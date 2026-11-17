from types import SimpleNamespace

import pytest

import consultar_rag as cr


class OllamaFalso:
    def __init__(self):
        self.ultima_entrada = None

    def embed(self, model, input):
        self.ultima_entrada = {"model": model, "input": input}
        return SimpleNamespace(embeddings=[[0.1, 0.2]])


class QdrantFalso:
    def __init__(self):
        self.ultima_consulta = None

    def query_points(self, coleccion, query, limit, with_payload):
        self.ultima_consulta = {
            "coleccion": coleccion,
            "query": query,
            "limit": limit,
            "with_payload": with_payload,
        }
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
