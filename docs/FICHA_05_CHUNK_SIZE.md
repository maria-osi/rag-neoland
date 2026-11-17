# Ficha de investigación: tamaño de chunk

> Ficha de la pregunta 5 de [TAREA_RAG_A_TEMPO.md](TAREA_RAG_A_TEMPO.md), con la estructura de [PLANTILLA_FICHA_INVESTIGACION.md](PLANTILLA_FICHA_INVESTIGACION.md). Issues [#7](https://github.com/maria-osi/rag-neoland/issues/7) (tamaño fijo) y [#11](https://github.com/maria-osi/rag-neoland/issues/11) (troceo por estructura). Parte del modelo elegido en la [ficha 1](FICHA_01_EMBEDDINGS.md).

| Campo | Valor |
|---|---|
| Autores | Maria (persona A: indexación) |
| Fecha | 2026-11-17 |
| Versión | v2 |
| Estado | borrador |
| Pregunta nº | 5 |

## Resumen (máx. 150 palabras)

Qué troceo recupera mejor la documentación de Python 3.15, con nomic-embed-text, Qdrant, k=4 y las 32 preguntas A-D del golden set. Entre seis troceos de tamaño fijo, el acierto por evidencia sube desde 500 (ev_hit@4 0,375) hasta 1500 (0,563), y el solape no compensa. Después se comparó 1500 fijo con un troceo por encabezados Markdown (máximo 1500 o 1000, mínimo 200, con y sin ruta de títulos). Solo estructura 1500/200 sin ruta cumple el criterio fijado antes de medir: sube ev_hit@4 a 0,594 y ev_MRR de 0,422 a 0,477, en la categoría A pasa de 3 a 5 de 10, mantiene el hit@4 por fuente (0,906) y sus chunks son más cortos de media (1 203 frente a 1 441 caracteres). Se elige esa configuración, provisional: la ventaja global es de una pregunta y 71 chunks pasan de 6 000 caracteres; los más largos se embeben solo por su comienzo.

## 1. Introducción

### 1.1 Contexto y motivación

En la ficha 1, los tres modelos empataron en acierto por evidencia (0,375): el chunk con la respuesta exacta faltaba a menudo entre los 4 primeros aunque el fichero correcto sí apareciera. Eso apunta al troceo, no al modelo. El tamaño del chunk decide cuánto contexto lleva cada resultado y cuántos chunks hay que buscar. Con un corpus que crece de forma controlada, también condiciona el tiempo de indexación y la latencia.

### 1.2 Pregunta de investigación

¿Qué tamaño de chunk (y si conviene solape) maximiza el acierto por evidencia en los 4 primeros resultados sobre el golden set de Python 3.15?

### 1.3 Hipótesis

Los chunks más grandes que 500 caracteres suben el acierto por evidencia, porque la respuesta queda menos veces repartida entre chunks y cada chunk lleva más contexto para el embedding. A partir de cierto tamaño, el ruido de mezclar varios temas en un chunk bajaría el acierto por fuente. El solape debería ayudar a los chunks pequeños, porque evita cortar la evidencia por la mitad.

### 1.4 Alcance y exclusiones

- **Entra:** troceo por caracteres de 300, 500, 1000 y 1500, con y sin solape, y troceo por encabezados Markdown con máximo 1500 y 1000, mínimo 200, con y sin la ruta de títulos en el texto embebido (sección «Troceo por estructura Markdown»). Todo sobre nomic-embed-text, Qdrant y k=4.
- **No entra:** troceo por frases o por tokens; tamaños fijos mayores de 1500; otros modelos (ficha 1); otros k (ficha 4); reranking (ficha 3); hybrid (ficha 6). No se mide la respuesta final del LLM, solo la recuperación.

## 2. Estado de la cuestión

| Fuente | Qué aporta | Fiabilidad |
|---|---|---|
| Documentación de LangChain sobre text splitters (ref. 1) | El troceo por caracteres con solape es la línea base habitual. El solape existe para no perder contexto en los cortes. | oficial |
| Pinecone, «Chunking strategies» (ref. 2) | No hay un tamaño óptimo universal: depende del contenido, del modelo y de la longitud de las consultas. Recomienda medir sobre el propio corpus. | blog técnico |
| Nussbaum et al. (ref. 3) y ficha de nomic-embed-text en Ollama (ref. 4) | El modelo se entrenó con un contexto de 8192 tokens. La versión que sirve Ollama declara un `context_length` de 2048 tokens (`ollama show nomic-embed-text`). 1500 caracteres son unos 375 tokens con la estimación habitual de 4 caracteres por token; aunque el código diera 2 caracteres por token, serían 750 tokens, por debajo de 2048. | paper / oficial |
| Ficha 1 de este proyecto | Con 500 caracteres, el acierto por evidencia es 0,375 en los tres modelos probados. | propia |

Opinión del equipo: la documentación de Python mezcla prosa, firmas de funciones y ejemplos de código. Un párrafo explicativo y su ejemplo suelen sumar más de 500 caracteres, así que un troceo corto los separa.

## 3. Método

### 3.1 Opciones comparadas

| Opción | Tamaño (caracteres) | Solape (caracteres) | Colección en Qdrant |
|---|---|---|---|
| A | 300 | 0 | `pydocs_nomic_c300_s0` |
| B (base) | 500 | 0 | `pydocs_nomic_c500_s0` |
| C | 1000 | 0 | `pydocs_nomic_c1000_s0` |
| D | 1500 | 0 | `pydocs_nomic_c1500_s0` |
| E | 500 | 100 (20 %) | `pydocs_nomic_c500_s100` |
| F | 1000 | 200 (20 %) | `pydocs_nomic_c1000_s200` |

El troceo es `trocear_corpus(carpeta, tamano, solape)` de `scripts/comparar_embeddings.py`. Corta por caracteres, avanza `tamano - solape` en cada paso y descarta los tramos en blanco.

### 3.2 Datos y preguntas de prueba

- Documentos usados: corpus limpio de Python 3.15, `data/python-docs-3.15/python-3.15-docs-md-clean/` (508 ficheros `.md`, 9,6 MB).
- Conjunto de preguntas: las 35 del golden set ([GOLDEN_SET_PYTHON_DOCS.md](GOLDEN_SET_PYTHON_DOCS.md)), columna «Query (EN)». Las métricas de acierto usan las 32 de las categorías A-D. Las 3 de la categoría E no tienen respuesta en el corpus y se usan para ver el score del mejor resultado.
- Respuesta esperada: la fuente (fichero) de cada pregunta en el golden set y la subcadena literal que la contiene en [golden_set_evidencias.json](golden_set_evidencias.json). Las definió el equipo leyendo la documentación.

### 3.3 Variables

- Variable que se cambia: tamaño del chunk y solape.
- Variables fijas: modelo nomic-embed-text con prefijos `search_query: ` / `search_document: `, Qdrant con distancia coseno, k=4, corpus y golden set.
- Variables medidas: acierto por fuente y por evidencia, latencia por pregunta, tiempo de indexación, número de chunks, evidencias partidas por el troceo y score del mejor resultado en las preguntas E.

### 3.4 Métricas y criterio de éxito

| Métrica | Cómo se calcula | Umbral para aceptar la opción |
|---|---|---|
| hit@1 / hit@4 (fuente) | Proporción de preguntas con un chunk del fichero correcto en la posición 1 / en las 4 primeras | No bajar respecto a la base (500) |
| MRR@4 (fuente) | Media de 1/posición del primer acierto (0 si no hay) | Referencia |
| ev_hit@1 / ev_hit@4 | Igual, pero el chunk debe contener la evidencia literal | Criterio principal: el mayor |
| ev_MRR@4 | MRR con el criterio de evidencia | Desempate |
| Latencia (ms) | Media por pregunta: embedding de la query más búsqueda | Por debajo de 100 ms |
| Indexación (s) | Embeddings más inserción, por configuración | Referencia de coste |

No se fijó un umbral numérico de mejora antes de probar; el criterio fue elegir el mayor ev_hit@4 sin perder acierto por fuente respecto a la base.

### 3.5 Entorno y reproducción

- Python y librerías: las de `pyproject.toml` y `uv.lock` (`qdrant-client` 1.20.0, `ollama` 0.6.3, `nbconvert` 7.17.2). Qdrant 1.20 en Docker y Ollama con `nomic-embed-text:latest` en un MacBook M2 Pro de 16 GB.
- Notebook: [notebooks/06_comparar_tamano_chunk.ipynb](../notebooks/06_comparar_tamano_chunk.ipynb). Para ejecutarlo sin abrir Jupyter: `uv run jupyter nbconvert --to notebook --execute notebooks/06_comparar_tamano_chunk.ipynb --ExecutePreprocessor.timeout=-1`. La indexación de las seis configuraciones suma unos 36 minutos (CSV); si se fija un timeout por celda, tiene que ser mayor que eso.
- Repeticiones: una ejecución. El troceo y los embeddings son deterministas; la latencia y el tiempo de indexación varían entre ejecuciones.
- Troceo por estructura: [notebooks/07_comparar_troceo_estructura.ipynb](../notebooks/07_comparar_troceo_estructura.ipynb), con `uv run jupyter nbconvert --to notebook --execute notebooks/07_comparar_troceo_estructura.ipynb --ExecutePreprocessor.timeout=-1`. La indexación de las cuatro colecciones de estructura suma unos 16 minutos (CSV). La referencia `pydocs_nomic_c1500_s0` se reutiliza si existe y cuadra con el troceo y con `tamano_chunk.csv`; el notebook no la borra nunca.

## 4. Resultados

**Tabla 1. Métricas por configuración (32 preguntas A-D, k=4).** Entre paréntesis, preguntas acertadas.

| Tamaño | Solape | Chunks | hit@1 | hit@4 | MRR | ev_hit@1 | ev_hit@4 | ev_MRR |
|---|---|---|---|---|---|---|---|---|
| 300 | 0 | 32 156 | 0,625 | 0,844 (27) | 0,716 | 0,281 | 0,438 (14) | 0,341 |
| 500 | 0 | 19 393 | 0,656 | 0,906 (29) | 0,755 | 0,219 | 0,375 (12) | 0,271 |
| 1000 | 0 | 9 816 | 0,625 | 0,906 (29) | 0,753 | 0,313 | 0,500 (16) | 0,378 |
| **1500** | **0** | **6 639** | **0,719** | **0,906 (29)** | **0,794** | **0,344** | **0,563 (18)** | **0,422** |
| 500 | 100 | 24 049 | 0,625 | 0,844 (27) | 0,719 | 0,219 | 0,469 (15) | 0,326 |
| 1000 | 200 | 12 103 | 0,656 | 0,875 (28) | 0,758 | 0,219 | 0,500 (16) | 0,315 |

La fila de 500 sin solape reproduce el resultado de nomic en la ficha 1 (hit@4 0,906 por fuente y 0,375 por evidencia).

**Tabla 2. Coste por configuración.**

| Tamaño | Solape | Latencia media (ms) | Indexación (s) | Evidencias partidas | Score medio del mejor resultado en E |
|---|---|---|---|---|---|
| 300 | 0 | 58,5 | 405 | 1 (A08, `library/sqlite3.md`) | 0,652 |
| 500 | 0 | 42,5 | 298 | 0 | 0,661 |
| 1000 | 0 | 18,8 | 244 | 0 | 0,644 |
| 1500 | 0 | 19,8 | 228 | 0 | 0,637 |
| 500 | 100 | 40,6 | 687 | 0 | 0,663 |
| 1000 | 200 | 20,0 | 311 | 0 | 0,646 |

**Tabla 3. ev_hit@4 por categoría (acierto por evidencia).**

| Categoría (n) | 300 | 500 | 1000 | 1500 | 500/100 | 1000/200 |
|---|---|---|---|---|---|---|
| A, dato concreto (10) | 0,2 | 0,2 | 0,3 | 0,3 | 0,3 | 0,4 |
| B, explicación (10) | 0,8 | 0,7 | 0,7 | 0,9 | 0,6 | 0,8 |
| C, código (9) | 0,44 | 0,33 | 0,67 | 0,67 | 0,56 | 0,44 |
| D, varias fuentes (3) | 0 | 0 | 0 | 0 | 0,33 | 0 |

Fallos y resultados que no siguen la tendencia:

- **Categoría A (dato concreto)** es la más baja en todas las configuraciones: como mucho 4 de 10 por evidencia, aunque por fuente llega a 1,0 con 500. El fichero correcto aparece, pero el chunk con el dato exacto no.
- **Categoría D (varias fuentes)** casi no acierta por evidencia en ninguna configuración: solo 500/100 acierta una de las tres. Con k=4 no caben las fuentes que piden estas preguntas.
- **Por fuente, 300 y 500/100 bajan** a 0,844: pierden 2 preguntas respecto a 500 sin solape.
- **El tiempo de indexación de 500/100 (687 s)** es el mayor, por encima de 300 sin solape, que tiene más chunks. Con una sola ejecución no se puede saber si es un coste real o una variación puntual de Ollama; no se ha medido.
- **Preguntas E:** el score del mejor resultado está entre 0,61 y 0,67 en todas las configuraciones. No hay un corte que separe estas preguntas de las que sí tienen respuesta.

## 5. Discusión

- **Qué significan los resultados:** el acierto por fuente apenas depende del tamaño: el modelo encuentra el fichero correcto casi siempre. Lo que cambia es si el chunk devuelto contiene la respuesta. Con 1500 caracteres, 18 de 32 preguntas traen la evidencia entre los 4 primeros, frente a 12 con 500. Además el primer resultado acierta más (ev_hit@1 0,344 frente a 0,219), así que el chunk relevante sube de posición.
- **Frente a la hipótesis:** se confirma la primera parte: los chunks grandes suben el acierto por evidencia. No aparece la caída por ruido hasta 1500; el acierto por fuente se mantiene en 0,906. La parte del solape se confirma solo a medias: 500/100 mejora a 500 sin solape por evidencia (15 frente a 12) pero pierde 2 preguntas por fuente (hit@4 0,844 frente a 0,906). 1000/200 empata con 1000 sin solape por evidencia (16 preguntas), pierde 1 pregunta en hit@4 y baja el ev_MRR (0,315 frente a 0,378); solo sube un poco el hit@1 (0,656 frente a 0,625) y el MRR (0,758 frente a 0,753).
- **Explicaciones alternativas:** con chunks grandes hay menos chunks en total (6 639 frente a 19 393), así que acertar entre 4 es más fácil por pura probabilidad. Las evidencias son subcadenas cortas: un chunk más largo tiene más papeletas de contenerlas aunque el resto del texto no sea relevante. Parte de la mejora puede deberse a eso y no a un mejor embedding. La sección «Troceo por estructura Markdown» separa en parte ambos efectos.
- **Limitaciones y amenazas a la validez:**
  - Son 32 preguntas: la diferencia entre 1000 y 1500 es de 2 preguntas, dentro del ruido. Entre 500 y 1500 son 6 preguntas, una diferencia más sólida.
  - Hay una sola ejecución; la latencia y la indexación cambian entre ejecuciones (ver 500/100).
  - No se probaron tamaños mayores de 1500, así que no sabemos dónde empieza la caída.
  - El orden de los modelos de la ficha 1 se midió con 500; no está comprobado que nomic siga siendo el mejor con 1500.
  - No se mide si el LLM responde bien. Un chunk de 1500 caracteres mete más texto irrelevante en el prompt; con k=4 son unos 6 000 caracteres (unos 1 500 tokens) por pregunta. La prueba previa de [TAREA_RAG_A_TEMPO.md](TAREA_RAG_A_TEMPO.md) (pregunta 5) vio que, con chunks de 1000, una pregunta acabó en «No encuentro esa información». Fue una sola pregunta y otra configuración, pero avisa de que más recuperación no garantiza mejor respuesta.
  - La categoría D tiene solo 3 preguntas.
- **Qué cambiaría si el volumen de datos creciera:** chunks más grandes significan menos vectores. Con 1500 caracteres el índice tiene un tercio de los chunks de 500, la indexación es un 23 % más rápida y la búsqueda tarda la mitad (20 ms frente a 42 ms). Si el corpus crece, esta opción escala mejor en almacenamiento y en tiempo.

## Troceo por estructura Markdown

### Pregunta y criterio

¿Trocear por la estructura Markdown recupera mejor que 1500 caracteres sin solape? La categoría A acierta como mucho 4 de 10 por evidencia con tamaño fijo, y parte de la mejora de 1500 puede venir solo de que un chunk largo contiene más texto. Un troceo que sigue las secciones del documento separa ese efecto del tamaño.

Criterio de decisión, fijado en la issue #11 antes de medir: el troceo por estructura gana si sube ev_hit@4 y ev_MRR frente a 1500/0, sobre todo en la categoría A, sin bajar el hit@4 por fuente y con un tamaño medio de chunk parecido o menor. «Sobre todo en la categoría A» se aplica como: el ev_hit@4 de A también sube. Las cuatro configuraciones medidas lo cumplen, así que esta lectura no cambia el resultado.

### Método

El troceo es `trocear_por_estructura(carpeta, maximo, minimo)` de `scripts/comparar_embeddings.py`:

- Abre una sección en cada encabezado `#` a `####` que esté fuera de un bloque de código ```` ``` ````. Las líneas `#` dentro de un bloque son comentarios de Python.
- Une una sección de menos de `minimo` caracteres con la siguiente del mismo fichero (la última, con la anterior). Nunca une ficheros distintos.
- Subdivide una sección de más de `maximo` por líneas en blanco, sin cortar un bloque de código ni una entrada de lista de definiciones (`termino` seguido de `:   texto`). Un bloque que solo ya pasa de `maximo` queda entero, en un chunk propio.
- Sin solape. Los chunks de un fichero, concatenados, reproducen el fichero; el notebook lo comprueba.
- Cada chunk lleva `ruta_titulos`, los encabezados abiertos unidos con « > » (por ejemplo, «string — Common string operations > String constants»).

`texto_a_embeber(chunk, con_ruta)` decide qué se embebe: el texto del chunk, o la ruta de títulos, una línea en blanco y el texto. El payload de Qdrant guarda siempre el texto original, así que el acierto por evidencia se mide igual que en la tabla 1.

| Opción | Troceo | Máximo | Mínimo | Ruta en el texto embebido | Colección en Qdrant |
|---|---|---|---|---|---|
| G | estructura | 1500 | 200 | sí | `pydocs_nomic_est1500_m200_ruta` |
| H | estructura | 1500 | 200 | no | `pydocs_nomic_est1500_m200_sinruta` |
| I | estructura | 1000 | 200 | sí | `pydocs_nomic_est1000_m200_ruta` |
| J | estructura | 1000 | 200 | no | `pydocs_nomic_est1000_m200_sinruta` |
| D (referencia) | fijo | 1500 | — | no | `pydocs_nomic_c1500_s0` |

El resto es igual que en la sección 3: modelo, prefijos, Qdrant con coseno, k=4, corpus, golden set y evidencias. La referencia D se reutilizó de la primera prueba; su tiempo de indexación es el de `tamano_chunk.csv`.

### Resultados

**Tabla 4. Métricas por configuración (32 preguntas A-D, k=4).** Entre paréntesis, preguntas acertadas.

| Opción | Chunks | Tamaño medio (caracteres) | hit@1 | hit@4 | MRR | ev_hit@1 | ev_hit@4 | ev_MRR |
|---|---|---|---|---|---|---|---|---|
| G: estructura 1500, con ruta | 7 955 | 1 203 | 0,750 | 0,875 (28) | 0,807 | 0,375 | 0,594 (19) | 0,477 |
| **H: estructura 1500, sin ruta** | **7 955** | **1 203** | **0,719** | **0,906 (29)** | **0,786** | **0,406** | **0,594 (19)** | **0,477** |
| I: estructura 1000, con ruta | 10 554 | 907 | 0,781 | 0,844 (27) | 0,807 | 0,406 | 0,625 (20) | 0,495 |
| J: estructura 1000, sin ruta | 10 554 | 907 | 0,750 | 0,844 (27) | 0,792 | 0,438 | 0,563 (18) | 0,487 |
| D: fijo 1500 | 6 639 | 1 441 | 0,719 | 0,906 (29) | 0,794 | 0,344 | 0,563 (18) | 0,422 |

La fila D reproduce las métricas de recuperación de la fila 1500 de la tabla 1 (misma colección); la latencia se midió de nuevo (20,9 ms frente a 19,8 ms).

**Tabla 5. Coste por configuración.**

| Opción | Latencia media (ms) | Indexación (s) | Evidencias partidas | Chunks de más de 6 000 caracteres | Score medio del mejor resultado en E |
|---|---|---|---|---|---|
| G | 25,5 | 236 | 0 | 71 (máx. 203 072) | 0,639 |
| H | 18,8 | 228 | 0 | 71 (máx. 203 072) | 0,659 |
| I | 17,5 | 251 | 0 | 71 (máx. 203 072) | 0,638 |
| J | 18,5 | 240 | 0 | 71 (máx. 203 072) | 0,660 |
| D | 20,9 | 228 | 0 | 0 (máx. 1 500) | 0,637 |

**Tabla 6. Por categoría: ev_hit@4, ev_MRR en A y hit@4 por fuente.**

| Categoría (n) | G | H | I | J | D |
|---|---|---|---|---|---|
| A, ev_hit@4 (10) | 0,6 | 0,5 | 0,7 | 0,5 | 0,3 |
| A, ev_MRR | 0,450 | 0,358 | 0,517 | 0,433 | 0,183 |
| B, ev_hit@4 (10) | 0,7 | 0,7 | 0,6 | 0,6 | 0,9 |
| C, ev_hit@4 (9) | 0,67 | 0,78 | 0,78 | 0,78 | 0,67 |
| D, ev_hit@4 (3) | 0 | 0 | 0 | 0 | 0 |
| A, hit@4 por fuente | 0,8 | 0,9 | 0,8 | 0,8 | 0,8 |
| B, hit@4 por fuente | 0,8 | 0,9 | 0,7 | 0,8 | 1,0 |

**Tabla 7. Criterio de decisión aplicado frente a D.**

| Opción | Sube ev_hit@4 | Sube ev_MRR | Sube ev_hit@4 en A | No baja hit@4 por fuente | Tamaño medio parecido o menor | Gana |
|---|---|---|---|---|---|---|
| G | sí (19 frente a 18) | sí | sí (6 frente a 3) | no (28 frente a 29) | sí | no |
| **H** | **sí (19 frente a 18)** | **sí** | **sí (5 frente a 3)** | **sí (29)** | **sí** | **sí** |
| I | sí (20 frente a 18) | sí | sí (7 frente a 3) | no (27 frente a 29) | sí | no |
| J | no (18, empate) | sí | sí (5 frente a 3) | no (27 frente a 29) | sí | no |

Fallos y resultados que no siguen la tendencia:

- **La categoría B baja** con todos los troceos por estructura: de 9 de 10 por evidencia con D a 7 (G, H) o 6 (I, J). La mejora en A y C la compensa B en parte; en H, A suma 2 preguntas, C suma 1 y B resta 2.
- **La ruta de títulos** sube el acierto por evidencia en A (G 6 y I 7, frente a 5 sin ruta). En el total, con 1500 empata por evidencia (G 19, H 19) y baja el acierto por fuente (G 28 frente a 29 en H); con 1000 sube por evidencia (I 20 frente a 18 en J) y empata por fuente (I y J, 27). El efecto de la ruta en el hit@4 por fuente solo aparece con 1500. Con 1000, sin ruta el ev_hit@4 no sube respecto a D.
- **La categoría D (varias fuentes)** no acierta por evidencia en ninguna configuración.
- **Preguntas E:** el score del mejor resultado está entre 0,63 y 0,67 en todas. Sin ruta es algo mayor (0,659 y 0,660) que con ruta o con D (0,637-0,639). Sigue sin haber un corte que separe estas preguntas.
- **Latencia de G (25,5 ms)**: es la mayor, con el mismo número de chunks que H (18,8 ms). Con una sola ejecución no se sabe si es una variación puntual.

### Discusión

- **Qué significan los resultados:** H acierta por evidencia una pregunta más que D con chunks un 17 % más cortos de media, y sube el ev_MRR de 0,422 a 0,477: el chunk con la evidencia aparece antes. En la categoría A, la que motivó la prueba, pasa de 3 a 5 de 10. La mejora de la tabla 1 no se explica solo porque un chunk largo contenga más texto: cortar por secciones, con chunks más cortos, mantiene o sube el acierto por evidencia. J, con chunks de 907 caracteres de media, empata con D en ev_hit@4.
- **Frente al criterio:** H es la única opción que lo cumple entero. G empata con H por evidencia (19) y solo gana en la categoría A (6 frente a 5), pero baja el hit@4 por fuente (28 frente a 29). I es la única que supera a H por evidencia (20), pero baja el hit@4 por fuente a 27, como J.
- **Limitaciones y amenazas a la validez:**
  - Hay una sola ejecución con 32 preguntas: una pregunta vale 0,031. La diferencia entre H y D en ev_hit@4 es de una pregunta, dentro del ruido. La de ev_MRR y la de la categoría A (2 preguntas de 10) son mayores, pero A tiene solo 10 preguntas.
  - 71 chunks pasan de 6 000 caracteres; el mayor tiene 203 072. Son bloques que el troceo no corta (bloques de código o entradas de definición enteros, o párrafos sin líneas en blanco). Ollama sirve `nomic-embed-text` con un contexto de 2048 tokens y recorta sin error las entradas más largas (con `truncate=False`, la llamada falla). Se comprobó a mano con el chunk de 203 072 caracteres durante la preparación del notebook 07; esa prueba no queda en las salidas del notebook. Los más largos se embeben, por tanto, solo por su comienzo. Con tamaño fijo ningún chunk pasa de 1 500 caracteres.
  - Esos mismos chunks llegan enteros al prompt si se recuperan: un solo resultado puede ocupar más que los unos 5 900 caracteres de contexto que el prompt recibe de media con k=4 (medido en la ficha 4).
  - Solo se probó `minimo` 200 y dos valores de `maximo`.

## 6. Conclusión y decisión

| Campo | Contenido |
|---|---|
| Decisión | Troceo por estructura Markdown con máximo 1500 y mínimo 200, sin ruta de títulos en el texto embebido (colección `pydocs_nomic_est1500_m200_sinruta`), de forma provisional. Sustituye a 1500 caracteres sin solape. |
| Motivo principal | Es la única configuración que cumple el criterio fijado antes de medir: frente a 1500/0 sube ev_hit@4 (0,594 frente a 0,563) y ev_MRR (0,477 frente a 0,422), en la categoría A pasa de 3 a 5 de 10 por evidencia, mantiene el hit@4 por fuente (0,906) y tiene chunks más cortos de media (1 203 frente a 1 441 caracteres). |
| Alternativas descartadas | 1500 sin solape (`pydocs_nomic_c1500_s0`): queda como vuelta atrás, con el mismo acierto por fuente y una pregunta menos por evidencia. Estructura 1500 con ruta de títulos: empata por evidencia con la elegida (19) y baja el hit@4 por fuente (0,875 frente a 0,906). Estructura 1000 con ruta: sube el ev_hit@4 (0,625), pero baja el hit@4 por fuente a 0,844 frente a 0,906 de 1500/0. Estructura 1000 sin ruta: no sube el ev_hit@4 (0,563) y baja el hit@4 por fuente (0,844). 300 y 500: menos acierto por evidencia que 1500 (0,438 y 0,375 frente a 0,563). 1000 fijo: muy cerca de 1500 fijo. Con solape: 500/100 baja el acierto por fuente y 1000/200 no sube el de evidencia, y añaden un 24 % (500/100) y un 23 % (1000/200) más de chunks y más tiempo de indexación. |
| Coste o riesgo asumido | La ventaja global es de una pregunta (19 frente a 18), dentro del ruido, y la categoría B baja de 9 a 7 de 10 por evidencia. 71 chunks pasan de 6 000 caracteres (máximo 203 072): los más largos se embeben solo por su comienzo y, si se recuperan, meten mucho texto en el prompt. Hay un 20 % más de chunks que con 1500 fijo (7 955 frente a 6 639). |
| Cuándo se revisa | Al cerrar las fichas 3 (reranking) y 4 (k), que se miden sobre esta colección; si el LLM da respuestas peores con chunks largos; si se limita el tamaño de los bloques que el troceo no corta, para que ningún chunk pase del contexto de Ollama; o si se amplía el golden set, porque la ventaja frente a 1500 fijo es de una pregunta. Conviene repetir la ficha 1 con este troceo. |

## 7. Impacto en el workflow

- El paso «el agente consulta el RAG» busca en la colección `pydocs_nomic_est1500_m200_sinruta` de Qdrant, con el prefijo `search_query: ` de nomic.
- La indexación usa `trocear_por_estructura(carpeta, maximo=1500, minimo=200)` y embebe `preparar_documento("nomic", texto_a_embeber(chunk, con_ruta=False))`. El payload guarda `fuente`, `texto` y `ruta_titulos`.
- Las fichas 3, 4 y 6 parten de esta configuración en vez de 1500 sin solape.
- El prompt del agente recibe de media unos 5 900 caracteres de contexto con k=4 (5 926, medido en la [ficha 4](FICHA_04_NUMERO_K.md)), pero un solo resultado puede pasar de 6 000 (hasta 203 072). El prompt tiene que admitirlo o limitar el texto de cada resultado.

## 8. Referencias

1. LangChain. (s. f.). _Text splitters_. LangChain Docs. https://python.langchain.com/docs/concepts/text_splitters/ (consultado el _AAAA-MM-DD_).
2. Pinecone. (s. f.). _Chunking strategies for LLM applications_. Pinecone Learn. https://www.pinecone.io/learn/chunking-strategies/ (consultado el _AAAA-MM-DD_).
3. Nussbaum, Z., Morris, J. X., Duderstadt, B. y Mulyar, A. (2024). _Nomic Embed: Training a reproducible long context text embedder_. arXiv. https://arxiv.org/abs/2402.01613 (consultado el _AAAA-MM-DD_).
4. Ollama. (s. f.). _nomic-embed-text_. Ollama Library. https://ollama.com/library/nomic-embed-text (consultado el _AAAA-MM-DD_).

## Anexos

- Notebooks: [notebooks/06_comparar_tamano_chunk.ipynb](../notebooks/06_comparar_tamano_chunk.ipynb) (tamaño fijo) y [notebooks/07_comparar_troceo_estructura.ipynb](../notebooks/07_comparar_troceo_estructura.ipynb) (estructura)
- Datos brutos: `data/resultados/tamano_chunk.csv` y `data/resultados/troceo_estructura.csv`
- Troceo: `trocear_corpus`, `trocear_por_estructura` y `texto_a_embeber` en [scripts/comparar_embeddings.py](../scripts/comparar_embeddings.py)

---

## Lista de comprobación antes de exponer

- [x] La pregunta está formulada en una frase y se puede responder con datos.
- [ ] La hipótesis y el umbral de éxito se escribieron antes de probar. _En la prueba de tamaño fijo, la hipótesis sí; no hubo umbral numérico, solo «el mayor ev_hit@4 sin perder acierto por fuente». En la del troceo por estructura, el criterio se fijó antes de medir._
- [x] Solo cambia una variable a la vez; el resto está fijo.
- [x] Otra persona puede repetir la prueba con la sección 3.
- [x] Los resultados incluyen lo que no salió como se esperaba.
- [x] La conclusión no afirma más de lo que muestran los datos.
- [x] Las limitaciones están dichas con claridad.
- [ ] Toda afirmación externa tiene su referencia. _Faltan las fechas de consulta._
- [x] El resumen se entiende sin leer el resto.
