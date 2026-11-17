"""Tests de scripts/comparar_embeddings.py (escenarios 1-8 de la issue #5, 1-5 de la #7 y 1-9 de la #11)."""
import shutil
from pathlib import Path

import pytest

import comparar_embeddings as ce

RAIZ = Path(__file__).resolve().parent.parent
GOLDEN = RAIZ / "docs" / "GOLDEN_SET_PYTHON_DOCS.md"
EVIDENCIAS = RAIZ / "docs" / "golden_set_evidencias.json"
CORPUS = RAIZ / "data" / "python-docs-3.15" / "python-3.15-docs-md-clean"


def test_trocea_en_tramos_de_500(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "a.md").write_text("x" * 1200, encoding="utf-8")
    chunks = ce.trocear_corpus(tmp_path, 500)
    assert [len(c["texto"]) for c in chunks] == [500, 500, 200]
    assert {c["fuente"] for c in chunks} == {"sub/a.md"}
    assert len({c["id"] for c in chunks}) == 3


def test_descarta_tramos_en_blanco(tmp_path):
    (tmp_path / "a.md").write_text("x" * 500 + " \n" * 250, encoding="utf-8")
    chunks = ce.trocear_corpus(tmp_path, 500)
    assert len(chunks) == 1
    assert chunks[0]["texto"] == "x" * 500


def test_jsonl_ida_y_vuelta(tmp_path):
    chunks = [
        {"id": 0, "fuente": "a.md", "texto": "hola ñ\ncon salto"},
        {"id": 1, "fuente": "sub/b.md", "texto": "texto \"con comillas\""},
    ]
    ruta = tmp_path / "out" / "c.jsonl"
    ce.guardar_jsonl(chunks, ruta)
    assert ce.leer_jsonl(ruta) == chunks


def test_lee_golden_set_real():
    preguntas = ce.leer_golden_set(GOLDEN)
    assert len(preguntas) == 35
    por_cat = {}
    for p in preguntas:
        por_cat[p["categoria"]] = por_cat.get(p["categoria"], 0) + 1
    assert por_cat == {"A": 10, "B": 10, "C": 9, "D": 3, "E": 3}
    por_id = {p["id"]: p for p in preguntas}
    assert por_id["A01"]["fuentes"] == ["library/http.client.md"]
    assert set(por_id["D01"]["fuentes"]) == {"library/subprocess.md", "library/json.md"}
    assert all(p["fuentes"] == [] for p in preguntas if p["categoria"] == "E")
    assert all("`" not in p["query"] for p in preguntas)


def test_fila_nueva_se_incluye(tmp_path):
    copia = tmp_path / "golden.md"
    lineas = GOLDEN.read_text(encoding="utf-8").splitlines()
    salida = []
    for i, linea in enumerate(lineas):
        salida.append(linea)
        if linea.startswith("| A10 |"):
            salida.append("| A11 | A new `query` here? | resp | evid | `library/re.html` |")
    copia.write_text("\n".join(salida), encoding="utf-8")
    preguntas = ce.leer_golden_set(copia)
    assert len(preguntas) == 36
    a11 = next(p for p in preguntas if p["id"] == "A11")
    assert a11["query"] == "A new query here?"
    assert a11["fuentes"] == ["library/re.md"]


def test_rango_primer_acierto():
    assert ce.rango_primer_acierto(["x.md", "y.md", "a.md", "a.md"], ["a.md", "b.md"]) == 3
    assert ce.rango_primer_acierto(["x.md", "y.md", "z.md", "w.md"], ["a.md", "b.md"]) is None


def test_evidencias_coinciden_con_golden_set():
    """Cada pregunta con fuentes tiene evidencia para cada una de sus fuentes, y nada más."""
    evidencias = ce.leer_evidencias(EVIDENCIAS)
    esperado = {p["id"]: set(p["fuentes"]) for p in ce.leer_golden_set(GOLDEN) if p["fuentes"]}
    assert {id_: set(d) for id_, d in evidencias.items()} == esperado


def test_evidencias_caben_en_chunks_de_500():
    evidencias = ce.leer_evidencias(EVIDENCIAS)
    fuentes = {f for d in evidencias.values() for f in d}
    chunks = [c for c in ce.trocear_corpus(CORPUS, 500) if c["fuente"] in fuentes]
    assert ce.evidencias_fuera_de_chunks(evidencias, chunks) == []


def test_evidencia_partida_se_detecta():
    chunks = [{"fuente": "a.md", "texto": "hola mu"}, {"fuente": "a.md", "texto": "ndo"}]
    assert ce.evidencias_fuera_de_chunks({"X01": {"a.md": "mundo"}}, chunks) == [("X01", "a.md")]


def test_rango_primer_acierto_evidencia():
    evidencias = {"a.md": "clave", "b.md": "otra"}
    recuperados = [
        {"fuente": "x.md", "texto": "clave"},       # fuente equivocada
        {"fuente": "a.md", "texto": "sin dato"},    # fuente buena sin evidencia
        {"fuente": "b.md", "texto": "la otra cosa"},
    ]
    assert ce.rango_primer_acierto_evidencia(recuperados, evidencias) == 3
    assert ce.rango_primer_acierto_evidencia(recuperados[:2], evidencias) is None


def test_calcula_hit_y_mrr():
    m = ce.calcular_metricas([1, 2, None, 4], k=4)
    assert m["hit@1"] == 0.25
    assert m["hit@4"] == 0.75
    assert abs(m["mrr"] - 0.4375) < 1e-9


def test_prefijos_por_modelo():
    assert ce.preparar_query("minilm", "q") == "q"
    assert ce.preparar_documento("minilm", "c") == "c"
    assert ce.preparar_query("bge", "q") == "Represent this sentence for searching relevant passages: q"
    assert ce.preparar_documento("bge", "c") == "c"
    assert ce.preparar_query("nomic", "q") == "search_query: q"
    assert ce.preparar_documento("nomic", "c") == "search_document: c"


def test_fuentes_ausentes_avisa_con_id_y_ruta(tmp_path):
    """CB-03: una fuente que no existe en el corpus se señala con su ID y su ruta."""
    (tmp_path / "library").mkdir()
    (tmp_path / "library" / "re.md").write_text("x", encoding="utf-8")
    preguntas = [
        {"id": "A1", "fuentes": ["library/re.md"]},
        {"id": "A2", "fuentes": ["library/no_existe.md"]},
    ]
    assert ce.fuentes_ausentes(preguntas, tmp_path) == [("A2", "library/no_existe.md")]


def test_fila_invalida_no_cuenta_como_pregunta(tmp_path):
    """CB-04: una fila sin query o con un ID que no es letra más dígitos se descarta."""
    copia = tmp_path / "golden.md"
    lineas = GOLDEN.read_text(encoding="utf-8").splitlines()
    salida = []
    for linea in lineas:
        salida.append(linea)
        if linea.startswith("| A10 |"):
            salida.append("| A11 |  | resp | evid | `library/re.html` |")
            salida.append("| XX | A query? | resp | evid | `library/re.html` |")
    copia.write_text("\n".join(salida), encoding="utf-8")
    ids = [p["id"] for p in ce.leer_golden_set(copia)]
    assert "A11" not in ids and "XX" not in ids
    assert len(ids) == 35


def _texto_distinto(n: int) -> str:
    """Texto de n caracteres en el que cada posición se puede identificar."""
    return "".join(chr(0x4E00 + i) for i in range(n))


def test_trocea_con_solape(tmp_path):
    texto = _texto_distinto(1200)
    (tmp_path / "a.md").write_text(texto, encoding="utf-8")
    chunks = ce.trocear_corpus(tmp_path, 500, 100)
    assert [c["texto"] for c in chunks] == [texto[0:500], texto[400:900], texto[800:1200]]
    assert [len(c["texto"]) for c in chunks] == [500, 500, 400]
    for anterior, siguiente in zip(chunks, chunks[1:]):
        assert anterior["texto"][-100:] == siguiente["texto"][:100]


def test_solape_sin_tramo_final_redundante(tmp_path):
    texto = _texto_distinto(900)
    (tmp_path / "a.md").write_text(texto, encoding="utf-8")
    chunks = ce.trocear_corpus(tmp_path, 500, 100)
    assert [c["texto"] for c in chunks] == [texto[0:500], texto[400:900]]


def test_solape_ids_consecutivos_varios_ficheros(tmp_path):
    (tmp_path / "a.md").write_text(_texto_distinto(1200), encoding="utf-8")
    (tmp_path / "b.md").write_text(_texto_distinto(900), encoding="utf-8")
    chunks = ce.trocear_corpus(tmp_path, 500, 100)
    assert [c["id"] for c in chunks] == list(range(len(chunks)))
    assert [c["fuente"] for c in chunks] == ["a.md"] * 3 + ["b.md"] * 2


def test_solape_no_parte_mas_evidencias():
    evidencias = ce.leer_evidencias(EVIDENCIAS)
    fuentes = {f for d in evidencias.values() for f in d}
    sin_solape = [c for c in ce.trocear_corpus(CORPUS, 500) if c["fuente"] in fuentes]
    con_solape = [c for c in ce.trocear_corpus(CORPUS, 500, 100) if c["fuente"] in fuentes]
    assert len(ce.evidencias_fuera_de_chunks(evidencias, con_solape)) <= len(
        ce.evidencias_fuera_de_chunks(evidencias, sin_solape)
    )


@pytest.mark.parametrize("tamano, solape", [(500, -1), (500, 500), (500, 600), (0, 0), (-5, 0)])
def test_solape_o_tamano_invalidos(tmp_path, tamano, solape):
    (tmp_path / "a.md").write_text("x" * 1200, encoding="utf-8")
    with pytest.raises(ValueError) as error:
        ce.trocear_corpus(tmp_path, tamano, solape)
    assert str(solape if tamano > 0 else tamano) in str(error.value)


def test_solape_descarta_tramos_en_blanco(tmp_path):
    texto = "x" * 400 + " " * 400 + "y" * 400
    (tmp_path / "a.md").write_text(texto, encoding="utf-8")
    chunks = ce.trocear_corpus(tmp_path, 500, 100)
    assert [c["texto"] for c in chunks] == [texto[0:500], texto[400:900], texto[800:1200]]
    (tmp_path / "a.md").write_text("x" * 400 + " " * 1000 + "y" * 400, encoding="utf-8")
    chunks = ce.trocear_corpus(tmp_path, 500, 100)
    assert all(c["texto"].strip() for c in chunks)
    assert [c["id"] for c in chunks] == list(range(len(chunks)))
    assert len(chunks) == 3  # inicios 0, 400, 800, 1200, 1600: los de 400 y 800 son blancos


# --- Issue #11: troceo por estructura ---


def _md(tmp_path, nombre, texto):
    (tmp_path / nombre).write_text(texto, encoding="utf-8")


def test_estructura_ignora_encabezados_en_codigo(tmp_path):
    texto = "# Título\n\nUn párrafo.\n\n```\n# comentario\nx = 1\n```\n"
    _md(tmp_path, "a.md", texto)
    chunks = ce.trocear_por_estructura(tmp_path, 5000, 0)
    assert len(chunks) == 1
    assert chunks[0]["ruta_titulos"] == "Título"
    assert chunks[0]["texto"] == texto


def test_estructura_subdivide_seccion_grande(tmp_path):
    codigo = "```\n" + "\n".join(f"linea_{i} = {i}" for i in range(10)) + "\n```\n"
    definicion = "termino\n:   explicacion del termino\n\n    segundo parrafo con sangria\n"
    texto = (
        "# T\n\n" + "a" * 300 + "\n\n" + codigo + "\n" + "b" * 300 + "\n\n"
        + definicion + "\n" + "c" * 300 + "\n"
    )
    _md(tmp_path, "a.md", texto)
    chunks = ce.trocear_por_estructura(tmp_path, 400, 0)
    assert len(chunks) > 1
    assert all(len(c["texto"]) <= 400 for c in chunks)
    assert sum(codigo in c["texto"] for c in chunks) == 1
    assert sum(definicion.rstrip("\n") in c["texto"] for c in chunks) == 1


def test_estructura_bloque_indivisible_entero(tmp_path):
    codigo = "```\n" + "x = 1\n" * 100 + "```\n"
    texto = "# T\n\nintro\n\n" + codigo + "\ncierre\n"
    _md(tmp_path, "a.md", texto)
    chunks = ce.trocear_por_estructura(tmp_path, 200, 0)
    grandes = [c for c in chunks if len(c["texto"]) > 200]
    assert len(grandes) == 1
    assert codigo in grandes[0]["texto"]


def test_estructura_une_secciones_cortas(tmp_path):
    _md(tmp_path, "a.md", "# Uno\n\ncorta\n\n## Dos\n\n" + "d" * 300 + "\n")
    _md(tmp_path, "b.md", "# Tres\n\n" + "e" * 300 + "\n\n## Cuatro\n\ncorta final\n")
    chunks = ce.trocear_por_estructura(tmp_path, 1000, 100)
    assert len(chunks) == 2
    a, b = chunks
    assert a["fuente"] == "a.md" and b["fuente"] == "b.md"
    assert a["ruta_titulos"] == "Uno"
    assert "## Dos" in a["texto"] and "# Uno" in a["texto"]
    assert "corta final" in b["texto"] and "e" * 300 in b["texto"]
    assert b["ruta_titulos"] == "Tres"


def test_estructura_no_parte_definiciones(tmp_path):
    definicion = "termino\n:   texto de la definicion\n\n    otro parrafo con sangria\n"
    texto = "# T\n\n" + "a" * 200 + "\n\n" + definicion + "\n" + "b" * 200 + "\n"
    _md(tmp_path, "a.md", texto)
    chunks = ce.trocear_por_estructura(tmp_path, 260, 0)
    assert len(chunks) > 1
    con = [c for c in chunks if "termino\n" in c["texto"]]
    assert len(con) == 1
    assert definicion.rstrip("\n") in con[0]["texto"]


def test_estructura_ruta_titulos(tmp_path):
    texto = (
        "# `string` — Common string operations\n\nx\n\n## String constants\n\ny\n\n"
        "### Sub\n\nz\n\n## Otra\n\nw\n"
    )
    _md(tmp_path, "a.md", texto)
    chunks = ce.trocear_por_estructura(tmp_path, 1000, 0)
    assert [c["ruta_titulos"] for c in chunks] == [
        "string — Common string operations",
        "string — Common string operations > String constants",
        "string — Common string operations > String constants > Sub",
        "string — Common string operations > Otra",
    ]


@pytest.mark.parametrize("maximo,minimo", [(300, 0), (300, 100), (1000, 200), (50, 10)])
def test_estructura_reproduce_fichero(tmp_path, maximo, minimo):
    texto = (
        "previo sin titulo\n\n# A\n\n" + "a" * 200 + "\n\n```\n# c\n" + "k\n" * 80
        + "```\n\n## B\n\ncorto\n\ntermino\n:   def\n\n    mas\n\n### C\n\n" + "c" * 500
        + "\n\n\n\n"
    )
    _md(tmp_path, "a.md", texto)
    _md(tmp_path, "b.md", "# Solo\n\ncorta\n")
    chunks = ce.trocear_por_estructura(tmp_path, maximo, minimo)
    for fuente, esperado in (("a.md", texto), ("b.md", "# Solo\n\ncorta\n")):
        assert "".join(c["texto"] for c in chunks if c["fuente"] == fuente) == esperado
    assert [c["id"] for c in chunks] == list(range(len(chunks)))


def test_texto_a_embeber():
    chunk = {"ruta_titulos": "A > B", "texto": "hola"}
    assert ce.texto_a_embeber(chunk, True) == "A > B\n\nhola"
    assert ce.texto_a_embeber(chunk, False) == "hola"


@pytest.mark.parametrize(
    "maximo,minimo,nombre",
    [(0, 0, "maximo"), (-5, 0, "maximo"), (100, -1, "minimo"), (100, 100, "minimo"), (100, 150, "minimo")],
)
def test_estructura_parametros_invalidos(tmp_path, maximo, minimo, nombre):
    with pytest.raises(ValueError, match=nombre):
        ce.trocear_por_estructura(tmp_path, maximo, minimo)


def test_estructura_casos_de_borde(tmp_path):
    _md(tmp_path, "vacio.md", "  \n\n")
    _md(tmp_path, "abierto.md", "# T\n\n```\n# no es titulo\ncodigo\n")
    _md(tmp_path, "previo.md", "texto previo\n\n# T\n\n" + "z" * 300 + "\n")
    chunks = ce.trocear_por_estructura(tmp_path, 1000, 50)
    assert not [c for c in chunks if c["fuente"] == "vacio.md"]
    abierto = [c for c in chunks if c["fuente"] == "abierto.md"]
    assert len(abierto) == 1 and abierto[0]["ruta_titulos"] == "T"
    previo = [c for c in chunks if c["fuente"] == "previo.md"]
    assert previo[0]["ruta_titulos"] == ""


# --- Issue #9: número de k ---


def test_k_minimo_del_golden_set_real():
    assert ce.leer_k_minimo(GOLDEN) == {"A": "1", "C": "1-2", "D": "2"}


def test_k_minimo_sin_declarar(tmp_path):
    ruta = tmp_path / "golden.md"
    ruta.write_text(
        "## A. Consulta puntual\n\n## B. Términos exactos\n\n## E. Sin respuesta\n",
        encoding="utf-8",
    )
    assert ce.leer_k_minimo(ruta) == {}


@pytest.mark.parametrize(
    "k, hit1, hit_k, mrr",
    [
        (1, 1 / 4, 1 / 4, 1 / 4),
        (2, 1 / 4, 2 / 4, (1 + 1 / 2) / 4),
        (8, 1 / 4, 3 / 4, (1 + 1 / 2 + 1 / 5) / 4),
    ],
)
def test_metricas_con_k_distinto_de_4(k, hit1, hit_k, mrr):
    m = ce.calcular_metricas([1, 2, 5, None], k=k)
    assert m["hit@1"] == pytest.approx(hit1)
    assert m[f"hit@{k}"] == pytest.approx(hit_k)
    assert m["mrr"] == pytest.approx(mrr)
