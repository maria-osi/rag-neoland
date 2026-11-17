from types import SimpleNamespace

import pytest

import consultar_rag as cr


class OllamaFalso:
    def __init__(self):
        self.ultima_entrada = None
        self.llamadas = 0

    def embed(self, model, input):
        self.llamadas += 1
        self.ultima_entrada = {"model": model, "input": input}
        return SimpleNamespace(embeddings=[[0.1, 0.2]])


class QdrantFalso:
    def __init__(self):
        self.ultima_consulta = None
        self.consultas = []

    def query_points(self, coleccion, query, limit, with_payload, **extra):
        self.ultima_consulta = {
            "coleccion": coleccion,
            "query": query,
            "limit": limit,
            "with_payload": with_payload,
            **extra,
        }
        self.consultas.append(self.ultima_consulta)
        puntos = [
            SimpleNamespace(
                id=i,
                score=1 - i / 10,
                payload={"fuente": f"f{i}.md", "texto": f"texto {i}"},
            )
            for i in range(5)
        ]
        return SimpleNamespace(points=puntos)


class RerankerFalso:
    def predict(self, pares):
        assert pares[0] == ("What is a context manager?", "texto 0")
        return [0.1, 0.9, 0.4, 0.8, 0.2]


def test_consulta_recupera_20_y_devuelve_los_4_reordenados():
    ollama = OllamaFalso()
    qdrant = QdrantFalso()
    consultor = cr.ConsultorRAG(qdrant, ollama, RerankerFalso())

    resultados = consultor.consultar("What is a context manager?")

    assert ollama.ultima_entrada["input"] == [
        "search_query: What is a context manager?"
    ]
    assert qdrant.ultima_consulta == {
        "coleccion": cr.COLECCION,
        "query": [0.1, 0.2],
        "limit": 20,
        "with_payload": True,
    }
    assert [resultado["id"] for resultado in resultados] == [1, 3, 2, 4]
    assert resultados[0]["score_reranking"] == 0.9


@pytest.mark.parametrize(
    "pregunta,candidatos,k",
    [("", 20, 4), ("pregunta", 0, 4), ("pregunta", 4, 5)],
)
def test_consulta_rechaza_parametros_invalidos(pregunta, candidatos, k):
    consultor = cr.ConsultorRAG(QdrantFalso(), OllamaFalso(), RerankerFalso())
    with pytest.raises(ValueError):
        consultor.consultar(pregunta, candidatos, k)


class RerankerPorLlamada:
    """Devuelve una lista de scores por cada llamada a predict, en orden."""

    def __init__(self, *listas):
        self.listas = list(listas)

    def predict(self, pares):
        return self.listas.pop(0)


def test_consulta_sin_filtros_igual_que_hoy():
    qdrant = QdrantFalso()
    consultor = cr.ConsultorRAG(qdrant, OllamaFalso(), RerankerFalso())

    resultados = consultor.consultar("What is a context manager?", filtros={})

    assert len(qdrant.consultas) == 1
    assert "query_filter" not in qdrant.consultas[0]
    assert qdrant.consultas[0]["limit"] == 20
    assert [r["id"] for r in resultados] == [1, 3, 2, 4]
    for r in resultados:
        assert r["filtrado"] is False
        for campo in cr.CAMPOS_METADATOS:
            assert campo in r
        assert r["modulo"] == ""
        assert r["simbolos"] == []
        assert r["tiene_codigo"] is False


def test_consulta_con_filtro_sin_repeticion():
    qdrant = QdrantFalso()
    ollama = OllamaFalso()
    consultor = cr.ConsultorRAG(qdrant, ollama, RerankerFalso())

    resultados = consultor.consultar(
        "What is a context manager?", filtros={"modulo": "logging"}
    )

    assert len(qdrant.consultas) == 1
    filtro = qdrant.consultas[0]["query_filter"]
    assert filtro.must[0].key == "modulo"
    assert filtro.must[0].match.any == ["logging"]
    assert all(r["filtrado"] is True for r in resultados)
    assert ollama.llamadas == 1


def test_consulta_con_filtro_repite_sin_filtro():
    qdrant = QdrantFalso()
    ollama = OllamaFalso()
    reranker = RerankerPorLlamada(
        [-0.5, -0.2, -0.9, -0.1, -0.3], [0.1, 0.9, 0.4, 0.8, 0.2]
    )
    consultor = cr.ConsultorRAG(qdrant, ollama, reranker)

    resultados = consultor.consultar("pregunta", filtros={"modulo": "logging"})

    assert len(qdrant.consultas) == 2
    assert "query_filter" in qdrant.consultas[0]
    assert "query_filter" not in qdrant.consultas[1]
    assert qdrant.consultas[0]["query"] == qdrant.consultas[1]["query"]
    assert ollama.llamadas == 1
    assert [r["id"] for r in resultados] == [1, 3, 2, 4]
    assert all(r["filtrado"] is False for r in resultados)


def test_umbral_none_no_repite():
    qdrant = QdrantFalso()
    reranker = RerankerPorLlamada([-0.5, -0.2, -0.9, -0.1, -0.3])
    consultor = cr.ConsultorRAG(qdrant, OllamaFalso(), reranker)

    resultados = consultor.consultar(
        "pregunta", filtros={"modulo": "logging"}, umbral=None
    )

    assert len(qdrant.consultas) == 1
    assert [r["id"] for r in resultados] == [3, 1, 4, 0]
    assert all(r["filtrado"] is True for r in resultados)


class QdrantVacioConFiltro(QdrantFalso):
    def query_points(self, coleccion, query, limit, with_payload, **extra):
        if "query_filter" in extra:
            self.consultas.append(extra)
            return SimpleNamespace(points=[])
        return super().query_points(coleccion, query, limit, with_payload, **extra)


def test_filtro_sin_candidatos_repite_sin_filtro():
    qdrant = QdrantVacioConFiltro()
    consultor = cr.ConsultorRAG(qdrant, OllamaFalso(), RerankerFalso())
    resultados = consultor.consultar("What is a context manager?", filtros={"tipo_pagina": ["library"]})
    assert len(qdrant.consultas) == 2
    assert len(resultados) == 4
    assert all(r["filtrado"] is False for r in resultados)


def test_filtro_sin_candidatos_y_umbral_none_devuelve_vacio():
    qdrant = QdrantVacioConFiltro()
    consultor = cr.ConsultorRAG(qdrant, OllamaFalso(), RerankerFalso())
    assert consultor.consultar("pregunta", filtros={"modulo": "x"}, umbral=None) == []
    assert len(qdrant.consultas) == 1


def test_filtros_combina_claves_y_listas():
    filtro = cr.construir_filtro({"modulo": ["a", "b"], "tipo_pagina": "library"})
    assert [(c.key, c.match.any) for c in filtro.must] == [
        ("modulo", ["a", "b"]),
        ("tipo_pagina", ["library"]),
    ]
    assert cr.construir_filtro(None) is None
    assert cr.construir_filtro({}) is None


@pytest.mark.parametrize(
    "filtros",
    [
        {"fuente": "x"},
        {"modulo": ""},
        {"modulo": []},
        {"modulo": ["a", 3]},
        {"modulo": 3},
    ],
)
def test_filtros_invalidos_fallan_antes_del_embedding(filtros):
    ollama = OllamaFalso()
    qdrant = QdrantFalso()
    consultor = cr.ConsultorRAG(qdrant, ollama, RerankerFalso())
    with pytest.raises(ValueError):
        consultor.consultar("pregunta", filtros=filtros)
    assert ollama.llamadas == 0
    assert qdrant.consultas == []
