# Comparativa consolidada y decisiones del RAG

> Documento final de la investigación definida en [TAREA_RAG_A_TEMPO.md](TAREA_RAG_A_TEMPO.md). Reúne las seis fichas, la validación con la configuración completa y las decisiones que debe aplicar el workflow.

| Campo | Valor |
|---|---|
| Autora | Maria |
| Fecha de cierre | 2026-11-17 |
| Corpus | Documentación limpia de Python 3.15 |
| Golden set | 35 preguntas: 32 evaluables A-D y 3 sin respuesta E |
| Estado | Cerrado |

## 1. Decisión ejecutiva

El RAG final usa **Qdrant**, embeddings **nomic-embed-text**, troceo de Markdown por estructura con máximo 1500 y mínimo 200, recuperación de **20 candidatos**, reranking local con **MiniLM-L6** y entrega de los **4 mejores chunks**. No se incorpora búsqueda híbrida BM25 porque, una vez aplicado el reranker, solo mejora una pregunta por evidencia y el umbral exigía dos.

En la validación final, esta configuración recupera una fuente correcta entre los cuatro primeros en **30 de 32 preguntas (hit@4 0,938)** y un chunk con alguna de las evidencias literales de la pregunta en **26 de 32 (ev_hit@4 0,813)**. La latencia total media fue **918,3 ms**, en Windows con el reranker en CPU; la validación anterior, con el reranker en MPS, dio 153,7 ms (ver la sección 7).

## 2. Configuración final

| Componente | Decisión |
|---|---|
| Idioma de recuperación | Corpus y query en inglés; el agente traduce la pregunta antes y la respuesta después si la conversación está en español. |
| Modelo de embeddings | `nomic-embed-text` en Ollama |
| Prefijo del documento | `search_document: ` |
| Prefijo de la query | `search_query: ` |
| Base vectorial | Qdrant 1.20.2 como servidor Docker |
| Colección | `pydocs_nomic_est1500_m200_sinruta` |
| Troceo | Markdown por estructura; máximo 1500, mínimo 200; sin ruta de títulos en el texto embebido |
| Distancia | Coseno |
| Primera recuperación | 20 candidatos |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| Resultado final | 4 chunks |
| Búsqueda híbrida | No; solo búsqueda densa |
| Paso reutilizable | `scripts/consultar_rag.py` |

## 3. Comparativa total de decisiones

### 3.1 Embeddings

Se compararon MiniLM, BGE y nomic sobre Qdrant y Chroma con chunks fijos de 500 caracteres.

| Modelo | hit@1 | hit@4 | MRR | Lectura |
|---|---:|---:|---:|---|
| all-MiniLM-L6-v2 | 0,656 | 0,844 | 0,734 | Rápido y pequeño, pero pierde más fuentes. |
| BAAI/bge-base-en-v1.5 | 0,562 | 0,875 | 0,706 | Mejora hit@4 frente a MiniLM, peor primera posición. |
| **nomic-embed-text** | **0,656** | **0,906** | **0,755** | Mejor recuperación global; local, privado y sin coste por token. |

**Decisión:** nomic. La ventaja inicial era pequeña y la métrica por evidencia estaba limitada por el chunking; por eso se confirmó después con la configuración estructurada.

Ficha: [FICHA_01_EMBEDDINGS.md](FICHA_01_EMBEDDINGS.md).

### 3.2 Base vectorial

Qdrant y Chroma recibieron exactamente los mismos 7 955 vectores. Se midieron como servidores HTTP, con clientes asíncronos independientes, 640 búsquedas por ronda y tres rondas.

| Clientes | Qdrant, consultas/s | Chroma, consultas/s | Qdrant p95 | Chroma p95 |
|---:|---:|---:|---:|---:|
| 1 | 354,8 | **408,8** | 4,02 ms | **3,12 ms** |
| 4 | **587,0** | 539,6 | **8,61 ms** | 9,75 ms |
| 8 | **728,8** | 607,6 | 15,52 ms | **14,80 ms** |

No hubo errores. El top 1 coincidió en todas las queries y el solape top 20 fue 99,2 %. Con ocho clientes, Qdrant ofrece un 19,9 % más throughput; la diferencia de p95 es inferior al 10 % y se considera equivalente.

**Decisión:** Qdrant, porque el requisito es la consulta concurrente de varios agentes y escala mejor en esa carga. Chroma es válido para prototipos y fue más rápido con un cliente.

Ficha: [FICHA_02_BASE_VECTORIAL.md](FICHA_02_BASE_VECTORIAL.md).

### 3.3 Troceo

Primero se compararon tamaños fijos y solapes; después, troceo por estructura Markdown.

| Configuración finalista | hit@4 | ev_hit@4 | ev_MRR | Lectura |
|---|---:|---:|---:|---|
| Fijo 1500, sin solape | 0,906 | 0,563 | 0,422 | Mejor tamaño fijo, pero corta secciones por posición. |
| **Estructura 1500/200, sin ruta** | **0,906** | **0,594** | **0,477** | Mantiene fuentes y mejora evidencia y orden. |

**Decisión:** estructura 1500/200 sin ruta. Los encabezados delimitan unidades semánticas mejor que un número fijo de caracteres. Incluir la ruta de títulos en el embedding no compensó.

Ficha: [FICHA_05_CHUNK_SIZE.md](FICHA_05_CHUNK_SIZE.md).

### 3.4 Número de resultados

| k | Aciertos por evidencia | Diferencia frente a k=4 |
|---:|---:|---:|
| 1 | 13/32 | −6 |
| 2 | 15/32 | −4 |
| **4** | **19/32** | referencia |
| 8 | 22/32 | +3, pero duplica contexto |

**Decisión:** k=4 como contexto final. k=1 y k=2 pierden demasiada evidencia; k=8 aumenta el contexto. Los 20 candidatos del paso anterior al reranking no llegan al LLM.

Ficha: [FICHA_04_NUMERO_K.md](FICHA_04_NUMERO_K.md).

### 3.5 Reranking

| Configuración | hit@4 | ev_hit@4 | Reranking medio | Decisión |
|---|---:|---:|---:|---|
| Sin reranking | 29/32 | 19/32 | 0 ms | Referencia |
| **MiniLM-L6** | **30/32** | **22/32** | **119,4 ms** | Cumple |
| bge-reranker-base | 29/32 | 23/32 | 502,2 ms | Supera el límite de 500 ms |

**Decisión:** MiniLM-L6. Recupera tres evidencias adicionales, mantiene o mejora la fuente y queda lejos del límite de latencia. BGE acierta una evidencia más, pero es 4,2 veces más lento, baja la categoría C y quedó fuera por el criterio fijado antes de medir.

Ficha: [FICHA_03_RERANKING.md](FICHA_03_RERANKING.md).

### 3.6 Búsqueda híbrida

| Configuración | hit@4 | ev_hit@4 | ev_hit@4 en B |
|---|---:|---:|---:|
| Vectorial | 29/32 | 19/32 | 7/10 |
| Híbrida | 29/32 | 21/32 | 8/10 |
| Vectorial + reranking | 30/32 | 22/32 | 8/10 |
| Híbrida + reranking | 30/32 | 23/32 | 8/10 |

**Decisión:** mantener la búsqueda vectorial. BM25 aporta dos evidencias sin reranking, pero el reranker ya captura casi toda la mejora. Con la configuración final solo suma +1 total y +0 en términos exactos; el umbral exigía +2 total o en B.

Ficha: [FICHA_06_HYBRID.md](FICHA_06_HYBRID.md).

## 4. Validación de la configuración completa

El script [validar_rag_final.py](../scripts/validar_rag_final.py) ejecutó las 35 preguntas a través del mismo módulo que usará el agente.

| Métrica, preguntas A-D | Resultado |
|---|---:|
| hit@1 por fuente | 0,688 (22/32) |
| hit@4 por fuente | **0,938 (30/32)** |
| MRR por fuente | 0,797 |
| ev_hit@1 | 0,438 (14/32) |
| ev_hit@4 | **0,813 (26/32)** |
| ev_MRR | 0,604 |
| Latencia total media, Windows con reranker en CPU | 918,3 ms |
| Latencia total media de la validación anterior, reranker en MPS | 153,7 ms |

Las métricas por evidencia usan [golden_set_evidencias.json](golden_set_evidencias.json) con varias evidencias por fuente: A04, A06, A10 y C03 aceptan una segunda redacción de la respuesta. Por eso no son comparables con las de la sección 3 ni con las fichas, medidas con una sola evidencia por fuente. Las métricas por fuente reproducen la fila vectorial con reranking del notebook híbrido, lo que confirma que el módulo integrado no cambió la lógica investigada.

Datos: `data/resultados/validacion_final.csv`.

## 5. Paso «consultar el RAG»

El módulo [consultar_rag.py](../scripts/consultar_rag.py) carga una vez el cliente de Qdrant, Ollama y el reranker. Por consulta:

1. Recibe una pregunta en inglés.
2. Añade el prefijo `search_query: ` y obtiene el embedding con nomic.
3. Consulta Qdrant y recupera 20 candidatos.
4. Puntúa los pares `(pregunta, texto)` con MiniLM-L6.
5. Ordena por score de reranking.
6. Devuelve los 4 mejores chunks con fuente, texto y scores.

Uso directo:

```bash
uv run python scripts/consultar_rag.py "How does asyncio.TaskGroup work?"
```

En un workflow asíncrono con varios agentes debe usarse `AsyncQdrantClient` o ejecutar el adaptador síncrono fuera del event loop. El benchmark de la ficha 2 ya valida el cliente asíncrono con ocho conexiones.

## 6. Reflexiones

### 6.1 La fuente correcta no basta

El hit por fuente sobreestima la calidad. En la configuración final, 30 preguntas encuentran el fichero correcto, pero solo 26 encuentran un chunk que contiene alguna de sus evidencias. Siguen fallando por evidencia B01, B08, C01 y D03, y A01 y D02 no aciertan ni la fuente. La revisión manual de esos fallos está en la issue #22. Con una sola evidencia por fuente eran 22: A04, A06, A10 y C03 tenían la respuesta en el top 4 con otra redacción.

### 6.2 El chunking tuvo más impacto estructural que cambiar de modelo

Los embeddings variaron una o dos preguntas por fuente en la primera prueba. Cambiar de chunks fijos a secciones Markdown mejoró evidencia y MRR sin perder fuentes. En documentación técnica, respetar la estructura del documento resultó más valioso que perseguir un modelo algo mayor.

### 6.3 Más resultados no sustituyen al reranking

k=8 encuentra tres evidencias más que k=4, pero duplica texto enviado al LLM. Recuperar 20 y rerankear permite aprovechar un conjunto amplio sin aumentar el contexto final. La contrapartida es unos 120 ms y un modelo adicional cargado en memoria.

### 6.4 Las optimizaciones se solapan

La búsqueda híbrida parecía útil antes del reranking: +2 evidencias. Después del reranking aporta solo +1. Las decisiones no son aditivas; cada mejora debe medirse sobre la configuración realmente vigente, no sobre una referencia antigua.

### 6.5 Los umbrales previos evitaron elegir por intuición

BGE quedó 2,2 ms fuera del límite y BM25 añadió una pregunta cuando se exigían dos. Aplicar el criterio escrito antes del resultado evitó mover el objetivo para justificar la opción técnicamente más llamativa.

### 6.6 Qdrant no ganó todas las métricas

Chroma fue mejor con un solo cliente y tuvo una p95 ligeramente menor con ocho. Qdrant se eligió porque el requisito era concurrencia y su throughput escaló mejor, no porque sea universalmente superior. Para una aplicación local de un único proceso, Chroma seguiría siendo una elección razonable.

### 6.7 Las preguntas sin respuesta necesitan una decisión propia

El reranker separó las tres preguntas E de las A-D en este golden set, pero tres casos no bastan para fijar un umbral de confianza. El workflow todavía debe ser conservador: si la evidencia recuperada no sostiene una respuesta, el LLM debe decir que no la encuentra.

## 7. Limitaciones

- Un solo corpus, de Python 3.15 y en inglés.
- 32 preguntas evaluables; una pregunta cambia una proporción en 0,031.
- La mayoría de experimentos se ejecutó una vez; las latencias dependen de caché, orden y hardware.
- Las fichas midieron el reranker en MPS de Apple. La validación final, en Windows con el reranker en CPU, dio 918,3 ms de latencia total media frente a 153,7 ms de la validación anterior en MPS. No se midió el mismo equipo con los dos dispositivos, así que el peso del dispositivo en esa diferencia es una hipótesis. Un servidor dará otra cifra.
- La evidencia literal solo acepta las subcadenas listadas en el json: un chunk correcto con una redacción que no está en la lista cuenta como fallo.
- No se evaluó la respuesta generada por el LLM, solo la recuperación.
- La comparación de bases fue local, caliente y solo de lectura; no cubre escrituras, red, réplicas ni fallos.
- Algunos chunks excepcionales superan el máximo porque un bloque de código indivisible no se corta.
- La traducción español → inglés y la respuesta final en español se delegan al agente y no se midieron aquí.

## 8. Cuándo revisar las decisiones

Repetir la evaluación si ocurre cualquiera de estas condiciones:

- cambia el corpus, la versión de Python o el idioma;
- el golden set crece de forma material;
- el agente empieza a consultar desde CPU o desde otra máquina;
- aumenta la proporción de códigos, siglas o nombres exactos;
- el corpus supera claramente el tamaño controlado actual;
- se requiere escritura concurrente, alta disponibilidad o despliegue distribuido;
- se adopta otro reranker o se reduce el presupuesto de latencia;
- se quiere fijar un umbral de «no hay respuesta».

## 9. Artefactos finales

| Artefacto | Ruta |
|---|---|
| Plan maestro | [TAREA_RAG_A_TEMPO.md](TAREA_RAG_A_TEMPO.md) |
| Ficha 1 | [FICHA_01_EMBEDDINGS.md](FICHA_01_EMBEDDINGS.md) |
| Ficha 2 | [FICHA_02_BASE_VECTORIAL.md](FICHA_02_BASE_VECTORIAL.md) |
| Ficha 3 | [FICHA_03_RERANKING.md](FICHA_03_RERANKING.md) |
| Ficha 4 | [FICHA_04_NUMERO_K.md](FICHA_04_NUMERO_K.md) |
| Ficha 5 | [FICHA_05_CHUNK_SIZE.md](FICHA_05_CHUNK_SIZE.md) |
| Ficha 6 | [FICHA_06_HYBRID.md](FICHA_06_HYBRID.md) |
| Benchmark de bases | `scripts/comparar_bases_vectoriales.py` y `data/resultados/bases_vectoriales.csv` |
| Consulta integrada | `scripts/consultar_rag.py` |
| Validación final | `scripts/validar_rag_final.py` y `data/resultados/validacion_final.csv` |

## 10. Conclusión

El RAG deja de ser una colección de pruebas aisladas y queda convertido en una configuración trazable y ejecutable. La decisión final equilibra calidad, contexto y latencia: nomic + Qdrant + estructura 1500/200 + 20 candidatos + MiniLM-L6 + top 4. El siguiente trabajo ya no es elegir componentes, sino observar su comportamiento dentro del agente real y ampliar el golden set con fallos encontrados en uso.
