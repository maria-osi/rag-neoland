"""Funciones puras (sin red) del notebook 05_comparar_embeddings_bases.

Troceo del corpus, jsonl de chunks, lectura del golden set y de sus evidencias,
prefijos por modelo y métricas de recuperación.
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
