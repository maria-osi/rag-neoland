"""Tests de scripts/comparar_embeddings.py (escenarios 1-8 de la issue #5)."""
import shutil
from pathlib import Path

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
