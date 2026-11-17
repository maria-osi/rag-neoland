"""Paso reutilizable «consultar el RAG» con la configuración decidida.

Uso desde terminal:

    uv run python scripts/consultar_rag.py "How does asyncio.TaskGroup work?"

La instancia carga el reranker una vez. Cada consulta calcula el embedding con
nomic, recupera 20 candidatos de Qdrant, los reordena y devuelve los 4 mejores.
"""

from __future__ import annotations

import argparse
import json

import ollama
from qdrant_client import QdrantClient
from sentence_transformers import CrossEncoder

from comparar_embeddings import MODELOS, preparar_query


COLECCION = "pydocs_nomic_est1500_m200_sinruta"
MODELO = "nomic"
RERANKER = "cross-encoder/ms-marco-MiniLM-L-6-v2"
CANDIDATOS = 20
K = 4


class ConsultorRAG:
    """Recupera y reordena chunks sin cargar modelos en cada consulta."""

    def __init__(self, qdrant, cliente_ollama, reranker) -> None:
        self.qdrant = qdrant
        self.cliente_ollama = cliente_ollama
        self.reranker = reranker

    @classmethod
    def local(cls) -> "ConsultorRAG":
        """Construye el consultor para los servicios locales del proyecto."""
        qdrant = QdrantClient("localhost", port=6333)
        try:
            qdrant.get_collection(COLECCION)
        except Exception as error:
            raise RuntimeError(
                f"Qdrant no responde o no tiene {COLECCION}. "
                "Arráncalo y ejecuta el notebook 07."
            ) from error
        cliente_ollama = ollama.Client()
        modelo = MODELOS[MODELO]["nombre"]
        try:
            cliente_ollama.show(modelo)
        except Exception as error:
            raise RuntimeError(
                f"Ollama no responde o no tiene {modelo}. Ejecuta `ollama pull {modelo}`."
            ) from error
        try:
            reranker = CrossEncoder(RERANKER)
        except Exception as error:
            raise RuntimeError(f"No se pudo cargar el reranker {RERANKER}.") from error
        return cls(qdrant, cliente_ollama, reranker)

    def consultar(
        self,
        pregunta: str,
        candidatos: int = CANDIDATOS,
        k: int = K,
    ) -> list[dict]:
        """Devuelve los `k` chunks mejor puntuados de `candidatos` recuperados."""
        if not pregunta.strip():
            raise ValueError("La pregunta no puede estar vacía")
        if candidatos < 1:
            raise ValueError("candidatos debe ser al menos 1")
        if k < 1 or k > candidatos:
            raise ValueError("k debe estar entre 1 y candidatos")

        modelo = MODELOS[MODELO]["nombre"]
        query_embedding = preparar_query(MODELO, pregunta)
        vector = self.cliente_ollama.embed(
            model=modelo, input=[query_embedding]
        ).embeddings[0]
        puntos = self.qdrant.query_points(
            COLECCION,
            query=vector,
            limit=candidatos,
            with_payload=True,
        ).points
        recuperados = [
            {
                "id": punto.id,
                "fuente": punto.payload["fuente"],
                "texto": punto.payload["texto"],
                "ruta_titulos": punto.payload.get("ruta_titulos", ""),
                "score_vectorial": float(punto.score),
            }
            for punto in puntos
        ]
        if not recuperados:
            return []

        scores = self.reranker.predict(
            [(pregunta, resultado["texto"]) for resultado in recuperados]
        )
        for resultado, score in zip(recuperados, scores):
            resultado["score_reranking"] = float(score)
        recuperados.sort(key=lambda resultado: resultado["score_reranking"], reverse=True)
        return recuperados[:k]


def main() -> None:
    parser = argparse.ArgumentParser(description="Consulta el RAG local del proyecto")
    parser.add_argument("pregunta", help="Pregunta en inglés para la documentación de Python")
    parser.add_argument("--k", type=int, default=K, help="Chunks finales (por defecto: 4)")
    parser.add_argument(
        "--candidatos", type=int, default=CANDIDATOS, help="Candidatos antes de reranking"
    )
    args = parser.parse_args()
    consultor = ConsultorRAG.local()
    resultados = consultor.consultar(args.pregunta, args.candidatos, args.k)
    print(json.dumps(resultados, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
