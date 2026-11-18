---
name: consultar-docs-python
description: Consulta la documentación oficial de Python 3.15 con el RAG local del proyecto antes de usar una API de la biblioteca estándar o una construcción del lenguaje. Úsala al escribir o revisar código Python cuando dependas de la firma, el comportamiento, las excepciones o las restricciones de algo de la stdlib o de la sintaxis.
---

# Consultar la documentación de Python con el RAG

El RAG del proyecto busca en la documentación oficial de Python 3.15 (biblioteca estándar, referencia del lenguaje, tutorial y «What's New») y devuelve los 4 fragmentos más relevantes. Sirve para decidir con la documentación delante, no de memoria.

## Cuándo usarla

- Antes de usar una función, clase o módulo de la stdlib del que no tengas clara la firma, el valor de retorno o las excepciones.
- Antes de usar sintaxis con reglas propias (`except*`, `match`, `async with`, `nonlocal`, decoradores, comprensiones).
- Al elegir entre dos APIs parecidas (`gather` o `TaskGroup`, `wait_for` o `timeout`).

No sirve para librerías de terceros (numpy, requests, pandas…): el corpus solo tiene la documentación de Python.

## Requisitos

Desde la raíz del repo:

- Qdrant en Docker: `docker ps` debe listar `qdrant-rag`. Si no, `docker compose up -d`.
- Ollama en marcha con `nomic-embed-text` (`ollama list`).

## Cómo consultar

```bash
PYTHONIOENCODING=utf-8 uv run python scripts/consultar_rag.py "<pregunta en inglés>" --modulo <modulo>
```

- La pregunta va **en inglés**: el corpus está en inglés.
- `PYTHONIOENCODING=utf-8` hace que el JSON salga en UTF-8. Sin él, en Windows sale en cp1252 y leerlo como UTF-8 falla. En PowerShell: `$env:PYTHONIOENCODING = "utf-8"` antes de la orden.
- `--modulo` filtra por el módulo documentado (`asyncio`, `re`, `collections`, `tomllib`…). Es repetible. Con el filtro, el RAG acierta más (medido en la ficha 7). Si ningún candidato filtrado es bueno, repite la búsqueda sin filtro.
- Las funciones y los tipos integrados (`float`, `max`, `dict`, `str`, excepciones) no tienen módulo: usa `--tipo-pagina builtins`. Un `--modulo` que no existe, como `stdtypes`, no filtra nada y la búsqueda se repite sin filtro.
- `--tipo-pagina` filtra por carpeta del corpus: `builtins`, `library`, `reference`, `tutorial`, `howto`, `faq`, `whatsnew`, `c-api`, `using`, `extending`, `deprecations`.
- `--k` cambia el número de fragmentos (4 por defecto).
- Cada llamada tarda unos 10 s, porque carga los modelos. Planifica las preguntas y no lances consultas de relleno.
- Al terminar todas las consultas, descarga el modelo de la GPU con `ollama stop nomic-embed-text`.

La salida es una lista JSON. Por cada fragmento interesa:

| Campo | Para qué |
|---|---|
| `texto` | El fragmento de la documentación. Léelo entero: las reglas suelen ir al final. |
| `fuente` | Fichero de la documentación (`library/re.md`). Cítalo. |
| `ruta_titulos` | Sección exacta del fichero. |
| `score_reranking` | Confianza del reranker. Orientación sacada de la prueba del analizador de logs, no medida con el golden set: por encima de 3 suele responder; entre 0 y 3, comprueba que responde a la pregunta; por debajo de 0, el fragmento no suele servir. Un score alto no basta: manda el paso 3 del procedimiento. |
| `filtrado` | `false` si se pidió `--modulo` y la búsqueda se repitió sin filtro: el módulo indicado no tenía nada bueno. |
| `deprecated`, `added_in` | Si la API está obsoleta o en qué versión apareció. |

## Procedimiento

1. **Una pregunta por decisión.** Pregunta por una sola API o regla cada vez: «How do I parse a TOML file?», no «How do I read config and run tasks concurrently?».
2. **Usa `--modulo` cuando sepas el módulo.** Para funciones y tipos integrados, usa `--tipo-pagina builtins`. Para sintaxis del lenguaje, usa `--tipo-pagina reference` o ningún filtro.
3. **Comprueba que el primer fragmento nombra la API que necesitas**, aunque su score sea alto. En la prueba de `resumen_gastos`, «What exception does float() raise…» devolvió `re.PatternError` con 4,2. Si no la contiene, repite la pregunta con el nombre exacto: `"Match.groupdict"`, `"asyncio.timeout context manager"`. Las preguntas genéricas a veces devuelven la API vecina, por ejemplo `wait_for` en lugar de `timeout`. Con el nombre exacto, la API sale primera.
4. **Pregunta por las restricciones de forma explícita.** Para sintaxis y protocolos, haz una segunda consulta del tipo «What is not allowed in an except* clause?» o «restrictions of X». Si el fragmento empieza una sección (`### …`) y se corta, la continuación puede estar en otro fragmento: pide la sección por su título.
5. **Revisa lo que envuelve a tu código.** Si usas una API dentro de otra (`to_thread` dentro de `asyncio.run`, un hilo dentro de un executor), consulta también qué hace la de fuera al terminar o al cancelar. La documentación no siempre lo dice junto a la API interna.
6. **Comprueba la versión.** El corpus es de Python 3.15. Si el proyecto usa otra versión (mira `.python-version` o `pyproject.toml`), revisa `added_in` y las líneas «Added in version» y «Changed in version» del texto.
7. **Cita la fuente.** Cuando una decisión dependa de la documentación, menciona la `fuente` en tu respuesta o en un comentario breve.
8. **Ejecuta el código.** El RAG no sustituye a probar: ejecútalo o escribe un test antes de dar el trabajo por bueno.

## Errores conocidos

- **Regla al final de un fragmento con código.** Ejemplo: «`break`, `continue` and `return` cannot appear in an `except*` clause» está al final de un fragmento con un ejemplo largo, y no sale ni preguntando por ella. El paso 4 y el 8 lo cubren.
- **Avisos repartidos entre páginas.** Que un hilo de `asyncio.to_thread` no se cancela con un timeout no está escrito en un solo sitio. El paso 5 y el 8 lo cubren.
