"""Funciones puras (sin red) del notebook 05_comparar_embeddings_bases.

Troceo del corpus (por tamaño fijo y por estructura Markdown), jsonl de chunks, lectura del golden set y de sus evidencias,
prefijos por modelo, métricas de recuperación y reordenado por reranker con su criterio de decisión.
"""
import json
import re
from pathlib import Path

# Única fuente de los prefijos de cada modelo.
MODELOS: dict[str, dict] = {
    "minilm": {
        "proveedor": "sentence-transformers",
        "nombre": "all-MiniLM-L6-v2",
        "prefijo_query": "",
        "prefijo_documento": "",
    },
    "bge": {
        "proveedor": "sentence-transformers",
        "nombre": "BAAI/bge-base-en-v1.5",
        "prefijo_query": "Represent this sentence for searching relevant passages: ",
        "prefijo_documento": "",
    },
    "nomic": {
        "proveedor": "ollama",
        "nombre": "nomic-embed-text",
        "prefijo_query": "search_query: ",
        "prefijo_documento": "search_document: ",
    },
}

_ID_PREGUNTA = re.compile(r"^[A-Za-z]\d+$")
_RUTA = re.compile(r"`([^`]+)`")
_ENCABEZADO = re.compile(r"^(#{1,4}) (.*)$")
_CATEGORIA_K_MIN = re.compile(r"^##\s+([A-Za-z])\.\s.*\(k mín\.\s*([^)]+?)\s*\)\s*$")


def trocear_corpus(carpeta: Path, tamano: int = 500, solape: int = 0) -> list[dict]:
    """Trocea cada .md en tramos de `tamano` caracteres, con `solape` caracteres compartidos.

    Cada tramo empieza `tamano - solape` caracteres después del anterior. El último
    tramo de un fichero es el primero que llega a su final. Descarta los tramos que
    solo tienen espacios. Devuelve {"id": int, "fuente": str, "texto": str}, con la
    fuente relativa a `carpeta`.

    Lanza ValueError si `tamano` es menor o igual que 0, o si `solape` es negativo
    o mayor o igual que `tamano`.
    """
    if tamano <= 0:
        raise ValueError(f"tamano debe ser mayor que 0, y es {tamano}")
    if solape < 0 or solape >= tamano:
        raise ValueError(f"solape debe estar entre 0 y tamano - 1 ({tamano - 1}), y es {solape}")
    paso = tamano - solape
    carpeta = Path(carpeta)
    chunks: list[dict] = []
    for ruta in sorted(carpeta.rglob("*.md"), key=lambda p: p.relative_to(carpeta).as_posix()):
        fuente = ruta.relative_to(carpeta).as_posix()
        contenido = ruta.read_text(encoding="utf-8")
        for inicio in range(0, len(contenido), paso):
            texto = contenido[inicio:inicio + tamano]
            if texto.strip():
                chunks.append({"id": len(chunks), "fuente": fuente, "texto": texto})
            if inicio + tamano >= len(contenido):
                break
    return chunks


def _es_valla(linea: str) -> bool:
    return linea.lstrip().startswith("```")


def _secciones(contenido: str) -> list[list[str]]:
    """Parte un fichero en [texto, ruta_titulos] por encabezados # a #### fuera de código."""
    secciones: list[list[str]] = []
    titulos = ["", "", "", ""]
    en_codigo = False
    actual: list[str] = []
    ruta_actual = ""
    for linea in contenido.splitlines(keepends=True):
        if en_codigo:
            actual.append(linea)
            if _es_valla(linea):
                en_codigo = False
            continue
        if _es_valla(linea):
            en_codigo = True
            actual.append(linea)
            continue
        m = _ENCABEZADO.match(linea.rstrip("\r\n"))
        if m:
            if actual:
                secciones.append(["".join(actual), ruta_actual])
            nivel = len(m.group(1))
            titulos[nivel - 1] = m.group(2).replace("`", "").strip()
            for i in range(nivel, 4):
                titulos[i] = ""
            ruta_actual = " > ".join(t for t in titulos if t)
            actual = [linea]
        else:
            actual.append(linea)
    if actual:
        secciones.append(["".join(actual), ruta_actual])
    return secciones


def _bloques(texto: str) -> list[str]:
    """Separa por líneas en blanco, sin cortar bloques de código ni entradas de definición.

    Cada bloque conserva las líneas en blanco que lo siguen.
    """
    lineas = texto.splitlines(keepends=True)
    bloques: list[str] = []
    actual: list[str] = []
    hay_texto = False
    en_codigo = False
    en_def = False
    tras_blanco = False
    for i, linea in enumerate(lineas):
        if en_codigo:
            actual.append(linea)
            if _es_valla(linea):
                en_codigo = False
            continue
        blanco = not linea.strip()
        if en_def:
            if blanco:
                siguiente = next((x for x in lineas[i + 1:] if x.strip()), None)
                if siguiente is not None and siguiente[0] in " \t":
                    actual.append(linea)
                    continue
                en_def = False
            elif linea[0] in " \t:":
                actual.append(linea)
                if _es_valla(linea):
                    en_codigo = True
                continue
            else:
                en_def = False
        if blanco:
            actual.append(linea)
            tras_blanco = True
            continue
        if tras_blanco and hay_texto:
            bloques.append("".join(actual))
            actual = []
        tras_blanco = False
        hay_texto = True
        actual.append(linea)
        if _es_valla(linea):
            en_codigo = True
        elif i + 1 < len(lineas) and lineas[i + 1].startswith(":"):
            en_def = True
    if actual:
        bloques.append("".join(actual))
    return bloques


def _subdividir(texto: str, maximo: int) -> list[str]:
    if len(texto) <= maximo:
        return [texto]
    trozos: list[str] = []
    actual = ""
    for bloque in _bloques(texto):
        if actual and len(actual) + len(bloque) > maximo:
            trozos.append(actual)
            actual = ""
        actual += bloque
    if actual:
        trozos.append(actual)
    return trozos


def trocear_por_estructura(carpeta: Path, maximo: int = 1500, minimo: int = 200) -> list[dict]:
    """Trocea cada .md por encabezados # a #### (fuera de bloques de código), sin solape.

    Une las secciones menores que `minimo` con la siguiente del mismo fichero (la última,
    con la anterior) y subdivide las mayores que `maximo` por líneas en blanco, sin cortar
    bloques de código ni entradas de definición. Devuelve {"id", "fuente", "texto",
    "ruta_titulos"}; el texto es el original y concatenado reproduce el fichero.

    Lanza ValueError si `maximo` es menor o igual que 0, si `minimo` es negativo o si
    `minimo` es mayor o igual que `maximo`.
    """
    if maximo <= 0:
        raise ValueError(f"maximo debe ser mayor que 0, y es {maximo}")
    if minimo < 0:
        raise ValueError(f"minimo no puede ser negativo, y es {minimo}")
    if minimo >= maximo:
        raise ValueError(f"minimo debe ser menor que maximo ({maximo}), y es {minimo}")
    carpeta = Path(carpeta)
    chunks: list[dict] = []
    for ruta in sorted(carpeta.rglob("*.md"), key=lambda p: p.relative_to(carpeta).as_posix()):
        fuente = ruta.relative_to(carpeta).as_posix()
        fusion: list[list[str]] = []
        pendiente: list[str] | None = None
        for texto, titulos in _secciones(ruta.read_text(encoding="utf-8")):
            if pendiente is None:
                pendiente = [texto, titulos]
            else:
                pendiente[0] += texto
            if len(pendiente[0]) >= minimo and pendiente[0].strip():
                fusion.append(pendiente)
                pendiente = None
        if pendiente is not None:
            if fusion:
                fusion[-1][0] += pendiente[0]
            elif pendiente[0].strip():
                fusion.append(pendiente)
        for texto, titulos in fusion:
            for trozo in _subdividir(texto, maximo):
                chunks.append(
                    {"id": len(chunks), "fuente": fuente, "texto": trozo, "ruta_titulos": titulos}
                )
    return chunks


def texto_a_embeber(chunk: dict, con_ruta: bool) -> str:
    """chunk["texto"], o ruta_titulos + "\\n\\n" + texto si `con_ruta`."""
    if con_ruta:
        return chunk["ruta_titulos"] + "\n\n" + chunk["texto"]
    return chunk["texto"]


def guardar_jsonl(chunks: list[dict], ruta: Path) -> None:
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")


def leer_jsonl(ruta: Path) -> list[dict]:
    with Path(ruta).open(encoding="utf-8") as f:
        return [json.loads(linea) for linea in f if linea.strip()]


def _celdas(linea: str) -> list[str]:
    return [c.strip() for c in linea.strip().strip("|").split("|")]


def leer_golden_set(ruta: Path) -> list[dict]:
    """Lee las preguntas de las tablas del golden set.

    Devuelve {"id", "categoria", "query", "fuentes"}. Las columnas se localizan por
    el nombre de la cabecera (`ID`, `Query (EN)`, `Fuente`/`Fuentes`). Una fila sin
    query o con un ID que no es letra más dígitos no cuenta como pregunta.
    """
    preguntas: list[dict] = []
    cabecera: list[str] | None = None
    for linea in Path(ruta).read_text(encoding="utf-8").splitlines():
        if not linea.lstrip().startswith("|"):
            cabecera = None
            continue
        celdas = _celdas(linea)
        if cabecera is None:
            cabecera = celdas
            continue
        if set("".join(celdas)) <= set("-: "):  # fila separadora
            continue
        if "ID" not in cabecera or "Query (EN)" not in cabecera:
            continue
        fila = dict(zip(cabecera, celdas))
        id_ = fila.get("ID", "")
        query = fila.get("Query (EN)", "").replace("`", "").strip()
        if not _ID_PREGUNTA.match(id_) or not query:
            continue
        celda_fuentes = fila.get("Fuentes", fila.get("Fuente", ""))
        fuentes = [
            r[:-5] + ".md" if r.endswith(".html") else r
            for r in _RUTA.findall(celda_fuentes)
        ]
        preguntas.append({
            "id": id_,
            "categoria": id_[0].upper(),
            "query": query,
            "fuentes": fuentes,
        })
    return preguntas


def fuentes_ausentes(preguntas: list[dict], carpeta: Path) -> list[tuple[str, str]]:
    """Pares (ID, ruta) cuya fuente no existe en el corpus."""
    carpeta = Path(carpeta)
    return [
        (p["id"], fuente)
        for p in preguntas
        for fuente in p["fuentes"]
        if not (carpeta / fuente).is_file()
    ]


def leer_k_minimo(ruta: Path) -> dict[str, str]:
    """Lee el «k mín.» de los títulos de categoría `## X. … (k mín. N)`: {letra: texto de N}.

    El valor se conserva como texto («1-2»). Las categorías sin «k mín.» no aparecen.
    """
    resultado: dict[str, str] = {}
    for linea in Path(ruta).read_text(encoding="utf-8").splitlines():
        m = _CATEGORIA_K_MIN.match(linea.rstrip())
        if m:
            resultado[m.group(1)] = m.group(2)
    return resultado


def leer_evidencias(ruta: Path) -> dict[str, dict[str, str]]:
    """Lee el json de evidencias: {ID: {fuente: subcadena}}. Ignora las claves que empiezan por `_`."""
    datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
    return {id_: valor for id_, valor in datos.items() if not id_.startswith("_")}


def evidencias_fuera_de_chunks(
    evidencias: dict[str, dict[str, str]], chunks: list[dict]
) -> list[tuple[str, str]]:
    """Pares (ID, fuente) cuya subcadena no cabe entera en ningún chunk de esa fuente."""
    textos: dict[str, list[str]] = {}
    for chunk in chunks:
        textos.setdefault(chunk["fuente"], []).append(chunk["texto"])
    return [
        (id_, fuente)
        for id_, por_fuente in evidencias.items()
        for fuente, subcadena in por_fuente.items()
        if not any(subcadena in texto for texto in textos.get(fuente, []))
    ]


def preparar_query(modelo: str, texto: str) -> str:
    return MODELOS[modelo]["prefijo_query"] + texto


def preparar_documento(modelo: str, texto: str) -> str:
    return MODELOS[modelo]["prefijo_documento"] + texto


def rango_primer_acierto(recuperadas: list[str], esperadas: list[str]) -> int | None:
    """Posición (desde 1) del primer resultado cuya fuente está entre las esperadas."""
    for posicion, fuente in enumerate(recuperadas, start=1):
        if fuente in esperadas:
            return posicion
    return None


def rango_primer_acierto_evidencia(
    recuperados: list[dict], evidencias: dict[str, str]
) -> int | None:
    """Posición (desde 1) del primer chunk de una fuente esperada que contiene su evidencia.

    `recuperados` son {"fuente", "texto"}; `evidencias` es {fuente: subcadena}.
    """
    for posicion, chunk in enumerate(recuperados, start=1):
        subcadena = evidencias.get(chunk["fuente"])
        if subcadena is not None and subcadena in chunk["texto"]:
            return posicion
    return None


def calcular_metricas(rangos: list[int | None], k: int = 4) -> dict:
    """hit@1, hit@k y MRR@k a partir de los rangos del primer acierto."""
    n = len(rangos)
    if n == 0:
        return {"hit@1": 0.0, f"hit@{k}": 0.0, "mrr": 0.0}
    en_k = [r for r in rangos if r is not None and r <= k]
    return {
        "hit@1": sum(1 for r in en_k if r == 1) / n,
        f"hit@{k}": len(en_k) / n,
        "mrr": sum(1 / r for r in en_k) / n,
    }


def reordenar_por_score(candidatos: list[dict], scores: list[float], k: int) -> list[dict]:
    """Los `k` candidatos de mayor score; en los empates conserva el orden de la búsqueda."""
    if k < 1:
        raise ValueError(f"k debe ser al menos 1, y es {k}")
    if len(scores) != len(candidatos):
        raise ValueError(
            f"hay {len(scores)} scores para {len(candidatos)} candidatos"
        )
    pares = sorted(zip(candidatos, scores), key=lambda par: par[1], reverse=True)
    return [candidato for candidato, _ in pares[:k]]


def elegir_reranker(
    referencia: dict,
    opciones: list[dict],
    mejora_minima: int,
    latencia_maxima_ms: float,
) -> tuple[list[dict], str | None]:
    """Aplica el criterio de decisión sobre aciertos contados.

    `referencia` es {"ev_aciertos", "aciertos"}; cada opción trae además "nombre" y "latencia_ms"
    (latencia de reranking media). Devuelve una fila por opción y el nombre del ganador, o None.
    """
    filas = []
    for opcion in opciones:
        mejora = opcion["ev_aciertos"] - referencia["ev_aciertos"]
        fuente_no_baja = opcion["aciertos"] >= referencia["aciertos"]
        latencia_ok = opcion["latencia_ms"] < latencia_maxima_ms
        filas.append(
            {
                "nombre": opcion["nombre"],
                "mejora_ev": mejora,
                "fuente_no_baja": fuente_no_baja,
                "latencia_ok": latencia_ok,
                "cumple": mejora >= mejora_minima and fuente_no_baja and latencia_ok,
            }
        )
    por_nombre = {opcion["nombre"]: opcion for opcion in opciones}
    cumplen = [por_nombre[fila["nombre"]] for fila in filas if fila["cumple"]]
    if not cumplen:
        return filas, None
    ganador = min(cumplen, key=lambda o: (-o["ev_aciertos"], o["latencia_ms"]))
    return filas, ganador["nombre"]
