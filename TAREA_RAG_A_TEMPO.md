# RAG a tempo: tarea de investigación y decisiones

## Contexto

Nuestro RAG funciona porque el crecimiento es controlado: la información a la que el agente tiene que acceder es limitada. Esa premisa condiciona las decisiones de abajo (no diseñamos para millones de documentos).

## Objetivo final

Incorporar al workflow el paso en el que el agente consulta el RAG.

## Preguntas a contestar y justificar

Cada pregunta se responde con una decisión, su justificación y la evidencia que la sostiene (ver plantilla de investigación al final).

### 1. Modelo de embeddings

¿Hugging Face (open source), OpenAI o Cohere? ver modelos locales de Ollama.

- Decisión: _pendiente_
- Criterios a comparar: calidad en español, coste, latencia, dependencia de un proveedor externo, dimensión del vector, privacidad de los datos.

### 2. Base de datos vectorial

¿Chroma DB o Qdrant?

- Requisito clave: varios agentes acceden a la BD de forma asíncrona y en paralelo.
- Hipótesis de partida: Qdrant, desplegado en Docker, porque funciona como servidor independiente con acceso concurrente. Hay que justificarlo con evidencia, no darlo por hecho.
- Decisión: _pendiente_

### 3. Reranking

¿Necesitamos reranking?

- Decisión: _pendiente_
- Cómo decidirlo: medir si mejora la relevancia de los resultados sobre nuestras preguntas frente a la búsqueda sin reranking, y a qué coste de latencia.

### 4. Número de respuestas

Por ejemplo para la pregunta sobre API - metodo HTTP GET - solo necesitamos 1-2 K
¿Cuántas respuestas necesitamos devolver?

- Hipótesis de partida: 1 o 2 resultados (k=1).
- Decisión: _pendiente_
- Cómo decidirlo: comprobar con preguntas reales si k=1 basta o si k=2 recupera información que k=1 pierde.

### 5. Tamaño de chunk

¿Qué chunk size usamos?

- Decisión: _pendiente_
- Cómo decidirlo: probar la eficacia con varios tamaños sobre el mismo conjunto de preguntas y comparar resultados. Ya hay una prueba previa en el notebook con 300, 500 y 1000 caracteres: con 1000 la misma pregunta devolvió «No encuentro esa información», así que los chunks grandes pueden meter ruido. Falta repetirla de forma sistemática.

### 6. Búsqueda híbrida

¿Necesitamos hybrid search (vectorial + palabras clave)?

- Decisión: _pendiente_
- Cómo decidirlo: comprobar si hay preguntas con términos exactos (nombres, códigos, siglas) que la búsqueda semántica falla.

## Documentación de la investigación

Hay que documentar lo investigado con la plantilla universitaria de investigación. Una ficha por pregunta, con estas secciones:

1. Pregunta de investigación
2. Hipótesis
3. Método (qué se probó y cómo, con qué datos y preguntas)
4. Resultados (datos, tablas)
5. Discusión
6. Conclusión y decisión
7. Referencias y fuentes

## Entregables

- Una ficha de investigación por cada una de las 6 preguntas.
- Tabla resumen con las 6 decisiones y su justificación.
- Paso «consultar el RAG» integrado en el workflow del agente.

## Reparto del trabajo entre 3 personas

Las 6 preguntas no son independientes: chunk size, k, reranking e hybrid se miden sobre el mismo índice, y ese índice depende del modelo de embeddings y de la BD. Por eso hay una fase común corta y después un reparto por afinidad.

### Fase 0: juntos (1 sesión corta)

Sin esta fase, cada persona mide con reglas distintas y los resultados no se pueden comparar.

- **Conjunto de preguntas de evaluación (golden set).** Unas 20-30 preguntas reales con la página o el chunk que debe aparecer. Incluye preguntas con términos exactos (siglas, códigos) para la pregunta 6 y casos tipo «método HTTP GET» para la 4.
- **Métricas comunes.** Hit rate@k, MRR y latencia.
- **Configuración base fija.** Por ejemplo, un embedding por defecto, chunk 500 y k=4. Todos parten de ella y cambian una sola variable.
- **Plantilla de ficha.** Se rellena una vez para la estructura común (`PLANTILLA_FICHA_INVESTIGACION.md`).

### Reparto

| Persona | Preguntas | Qué hace |
|---|---|---|
| **A: Indexación** | 1 Embeddings + 5 Chunk size | Define cómo se genera el índice. Compara modelos (HF, OpenAI, Cohere, Ollama local) en español, coste, latencia, dimensión y privacidad. Después barre los tamaños de chunk. |
| **B: Infraestructura** | 2 Vector DB + 6 Hybrid | Despliega Qdrant en Docker y prueba la concurrencia con varios agentes en paralelo, frente a Chroma. Hybrid va con B porque depende de lo que soporte la BD (Qdrant lo trae nativo). |
| **C: Calidad de recuperación** | 3 Reranking + 4 Nº de respuestas | Mide la relevancia con y sin reranker y el coste en latencia. Compara k=1, 2 y 4. Es dueña del golden set y de las métricas. |

Entregables comunes:

- **Tabla resumen de las 6 decisiones:** C, que reúne todos los resultados de calidad.
- **Paso «consultar el RAG» en el workflow:** B, porque conoce el servidor y su API.

### Dependencias

1. **A condiciona a B y C.** Si A cambia de embedding o de chunk, las medidas de B y C quedan obsoletas. Hasta que A cierre, todos trabajan con la configuración base.
2. **A y B deciden pronto.** Fijan la base del resto, así que sus decisiones deberían salir en la primera mitad del trabajo.
3. **Fase final, juntos.** Se repite el golden set con la configuración ganadora, se confirman las decisiones de B y C sobre ella y se cierran la tabla resumen y la integración.

### Encaje con el flujo de entrega

Una issue por ficha, con rama `número-tipo-descripcion` y PR en draft por cada una. Además, dos issues comunes: la Fase 0 y la integración en el workflow.
