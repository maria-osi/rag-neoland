# Golden set: documentación oficial de Python 3.15

Conjunto de preguntas de evaluación para la Fase 0 de [TAREA_RAG_A_TEMPO.md](TAREA_RAG_A_TEMPO.md). Sirve para medir las decisiones de embeddings, chunk size, k, reranking e hybrid sobre el mismo corpus.

## Corpus

- Origen: <https://docs.python.org/3.15/download.html>, fichero `python-3.15-docs-html.zip` (descargado el 2026-11-16).
- Ubicación local: `data/python-docs-3.15/python-3.15-docs-html/` (596 ficheros HTML, 88 MB descomprimido).
- Las rutas de «Fuente» son relativas a esa carpeta. Al convertir a Markdown conservan la estructura de carpetas y cambian solo la extensión (`.html` → `.md`).

## Cómo se usa

Cada pregunta indica la fuente donde está la respuesta y los datos que la respuesta debe contener. Una recuperación **acierta** si entre los k resultados hay un chunk de la fuente indicada que contiene la evidencia. Métricas: hit rate@k, MRR y latencia.

Columnas de las tablas:

- **ID:** identificador estable. No se renumera al añadir preguntas.
- **Evidencia:** texto o dato concreto que debe aparecer en el chunk recuperado.
- **k mín.:** k que debería bastar. Sirve para la pregunta 4 de la tarea (1 o 2 resultados).

Todas las respuestas esperadas se han comprobado contra el texto de la documentación descargada.

## A. Consulta puntual (k mín. 1)

Una pregunta, una fuente, un dato. Es el caso «método HTTP GET» de la pregunta 4.

| ID | Pregunta | Respuesta esperada | Evidencia | Fuente |
|---|---|---|---|---|
| A01 | ¿Cómo hago una petición HTTP GET con la librería estándar? | Con `http.client.HTTPSConnection(host)`, `conn.request("GET", "/3/", headers={"Host": host})` y `conn.getresponse()`. | Ejemplo «to perform a GET request to https://docs.python.org/3/» con `print(response.status, response.reason)` → `200 OK` | `library/http.client.html` |
| A02 | ¿Cómo abro una URL y leo la respuesta con `urllib`? | Con `urllib.request.urlopen(url, data=None, [timeout, ]*, context=None)`. `url` puede ser una cadena o un objeto `Request`. | Firma de `urlopen` y su descripción | `library/urllib.request.html` |
| A03 | ¿Cómo leo un fichero de texto con `pathlib`? | `Path.read_text(encoding=None, errors=None, newline=None)` devuelve el contenido decodificado como cadena. | Firma de `Path.read_text` y el ejemplo con `write_text` | `library/pathlib.html` |
| A04 | ¿Cómo compruebo que una cadena entera cumple una expresión regular? | Con `re.fullmatch(pattern, string, flags=0)`: devuelve un `Match` si toda la cadena coincide y `None` si no. | Descripción de `re.fullmatch` | `library/re.html` |
| A05 | ¿Cómo itero dos listas en paralelo y fallo si tienen distinta longitud? | `zip(*iterables, strict=False)` con `strict=True`. | Texto «it's recommended to use the strict=True option» | `builtins/functions.html` |
| A06 | ¿Cómo ordeno las claves y sangro la salida al serializar JSON? | `json.dumps(obj, sort_keys=True, indent=4)`. | Ejemplo `json.dumps({'6': 7, '4': 5}, sort_keys=True, indent=4)` | `library/json.html` |
| A07 | ¿Cómo capturo la salida de un comando externo con `subprocess.run`? | Con `capture_output=True`: stdout y stderr se capturan con `PIPE`. No se puede combinar con los argumentos `stdout` ni `stderr`. | Párrafo «If capture_output is true, stdout and stderr will be captured» | `library/subprocess.html` |
| A08 | ¿Cómo inserto varias filas a la vez en SQLite? | `cur.executemany("INSERT INTO movie VALUES(?, ?, ?)", data)` seguido de `con.commit()`. Siempre con marcadores `?`, nunca formateando cadenas. | Ejemplo de `executemany` y nota sobre placeholders | `library/sqlite3.html` |
| A09 | ¿Cómo creo un entorno virtual y lo activo en macOS o Linux? | `python -m venv tutorial-env` y `source tutorial-env/bin/activate`. En Windows, `tutorial-env\Scripts\activate`. | Comandos de activación | `tutorial/venv.html` |
| A10 | ¿Cómo creo subcomandos en `argparse`? | Con `ArgumentParser.add_subparsers(...)`. | Entrada `ArgumentParser.add_subparsers` con sus parámetros (`title`, `dest`, `required`…) | `library/argparse.html` |

## B. Términos exactos y siglas (para la pregunta 6: hybrid)

Preguntas donde un nombre, un código o una sigla concreta decide la respuesta. La búsqueda semántica pura puede confundirlos con términos parecidos.

| ID | Pregunta | Respuesta esperada | Evidencia | Fuente |
|---|---|---|---|---|
| B01 | ¿Qué significa el código HTTP 418 en `http.HTTPStatus`? | `IM_A_TEAPOT`, definido en HTCPCP/1.0, RFC 2324, sección 2.3.2. | Fila `418 / IM_A_TEAPOT / HTCPCP/1.0 RFC 2324` | `library/http.html` |
| B02 | ¿Qué hace `secrets.compare_digest`? | Compara dos cadenas o bytes en tiempo constante para reducir el riesgo de ataques de temporización. Ver `hmac.compare_digest()`. | Definición «constant-time compare» | `library/secrets.html` |
| B03 | ¿Dónde están las funciones hash `adler32` y `crc32`? | En el módulo `zlib`, no en `hashlib`. | Nota «adler32 or crc32 hash functions, they are available in the zlib module» | `library/hashlib.html` |
| B04 | ¿Qué PEP añade el tipo `frozendict` en Python 3.15? | PEP 814. | Línea «PEP 814: Add frozendict built-in type» | `whatsnew/3.15.html` |
| B05 | ¿Qué PEP define la codificación UTF-8 por defecto? | PEP 686. | Línea «PEP 686: Python now uses UTF-8 as the default encoding» | `whatsnew/3.15.html` |
| B06 | ¿Qué es Tachyon y qué PEP lo introduce? | Un profiler de muestreo estadístico de alta frecuencia, dentro del nuevo paquete `profiling` (PEP 799). | «Tachyon: High-frequency statistical sampling profiler» | `whatsnew/3.15.html` |
| B07 | ¿Qué diferencia hay entre `functools.cache` y `lru_cache`? | `cache` equivale a `lru_cache(maxsize=None)`: caché sin límite, más pequeña y rápida porque nunca expulsa valores. | Texto «Returns the same as lru_cache(maxsize=None)» | `library/functools.html` |
| B08 | ¿Qué nivel tiene por defecto el logger raíz de `logging`? | `WARNING`. Los loggers nuevos arrancan en `NOTSET`. | Frase «the root logger is created with level WARNING» | `library/logging.html` |
| B09 | ¿Qué pasa si `itertools.batched` recibe `strict=True` y el último lote es más corto? | Lanza `ValueError`. | Firma `batched(iterable, n, *, strict=False)` y su descripción | `library/itertools.html` |
| B10 | ¿En qué modo se debe abrir el fichero que se pasa a `tomllib.load`? | Debe ser un objeto de fichero legible en modo binario. | «readable and binary file object» | `library/tomllib.html` |

## C. Conceptos y comportamiento (k mín. 1-2)

Preguntas de explicación, donde la respuesta ocupa un párrafo o depende de un matiz.

| ID | Pregunta | Respuesta esperada | Evidencia | Fuente |
|---|---|---|---|---|
| C01 | ¿Para qué sirve `asyncio.TaskGroup` y cómo se usa? | Es una alternativa moderna a `create_task()`: se usa con `async with asyncio.TaskGroup() as tg` y `tg.create_task(...)`. El `await` es implícito al salir del contexto. | Ejemplo con `say_after` y comentario «The await is implicit when the context manager exits» | `library/asyncio-task.html` |
| C02 | ¿Por qué `threading` no aprovecha varios núcleos en CPython y qué alternativa hay? | Por el Global Interpreter Lock: solo un hilo ejecuta código Python a la vez. Para usar varios núcleos, `multiprocessing` o `concurrent.futures.ProcessPoolExecutor`. `threading` sigue siendo válido para tareas limitadas por E/S. | Nota «CPython implementation detail: … Global Interpreter Lock» | `library/threading.html` |
| C03 | ¿Cómo hago una clase de datos inmutable con `dataclasses`? | Con `@dataclass(frozen=True)`: asignar a un campo lanza una excepción. | Parámetro `frozen: If true (the default is False), assigning to fields will generate an exception` | `library/dataclasses.html` |
| C04 | ¿Qué estructura uso para implementar una cola con inserciones y extracciones rápidas? | `collections.deque`, diseñada para `append` y `pop` rápidos por ambos extremos. | Texto «To implement a queue, use collections.deque» | `tutorial/datastructures.html` |
| C05 | ¿Qué garantiza la cláusula `finally` en un `try`? | Se ejecuta como última tarea antes de que termine la sentencia `try`. | Párrafo «If a finally clause is present…» | `tutorial/errors.html` |
| C06 | ¿Qué riesgo tiene `shutil.rmtree` con un enlace simbólico a un directorio? | Si la ruta es un enlace seguido de barra final (`'link/'`), el sistema operativo resuelve el enlace: borra el contenido del directorio apuntado y luego falla al borrar el enlace. `pathlib.Path` quita las barras finales y `rmtree(Path('link/'))` rechaza el enlace. | Párrafo sobre `'link/'` en `shutil.rmtree` | `library/shutil.html` |
| C07 | ¿Cómo funciona `lazy import` en Python 3.15 y dónde se puede usar? | La palabra clave blanda `lazy` aplaza la carga del módulo hasta el primer uso del nombre. Solo vale a nivel de módulo: dentro de funciones, clases o `try/except/finally` da `SyntaxError`. Tampoco admite `import *` ni `__future__`. | Sección «PEP 810: Explicit lazy imports» | `whatsnew/3.15.html` |
| C08 | ¿Cómo activo los imports perezosos sin tocar el código fuente? | Con la opción `-X lazy_imports` o la variable `PYTHON_LAZY_IMPORTS`. Valores: `all` y `normal` (por defecto). | Párrafo sobre `-X lazy_imports` | `whatsnew/3.15.html` |
| C09 | ¿Qué cambia en Python 3.15 y cuándo se publicó? | Novedades principales: imports perezosos, `frozendict` y `sentinel`, UTF-8 por defecto, desempaquetado en comprensiones y ABI estable para builds free-threaded. Publicada el 9 de octubre de 2026. | Resumen «Release highlights» | `whatsnew/3.15.html` |

## D. Varias fuentes (k mín. 2)

La respuesta completa necesita información de dos páginas distintas. Con k=1 solo se obtiene la mitad.

| ID | Pregunta | Respuesta esperada | Evidencia | Fuentes |
|---|---|---|---|---|
| D01 | ¿Cómo ejecuto un comando externo y convierto su salida a un objeto Python desde JSON? | `subprocess.run(..., capture_output=True, text=True)` para capturar la salida y `json.loads(...)` para decodificarla. | `capture_output` en subprocess y las funciones de carga de `json` | `library/subprocess.html`, `library/json.html` |
| D02 | ¿Cómo hago una petición GET y guardo el resultado en un fichero con `pathlib`? | Petición con `http.client` (`request("GET", ...)`, `getresponse()`) y escritura con `Path.write_text` o `Path.write_bytes`. | Ejemplo de GET y métodos de escritura de `Path` | `library/http.client.html`, `library/pathlib.html` |
| D03 | ¿Qué tengo que usar en vez de `threading` para tareas de CPU y cómo se llama la clase concreta? | `multiprocessing` o `concurrent.futures.ProcessPoolExecutor`; la segunda se documenta en su propia página. | Recomendación en `threading` y definición de `ProcessPoolExecutor` | `library/threading.html`, `library/concurrent.futures.html` |

## E. Sin respuesta en el corpus (negativas)

El corpus no contiene la información. El sistema debe contestar «No encuentro esa información» y no inventar. Se ha comprobado que `FastAPI`, `PyTorch` y `Kubernetes` no aparecen en ningún HTML del corpus.

| ID | Pregunta | Respuesta esperada |
|---|---|---|
| E01 | ¿Cómo defino un endpoint con FastAPI? | «No encuentro esa información.» |
| E02 | ¿Cómo entreno una red neuronal con PyTorch? | «No encuentro esa información.» |
| E03 | ¿Cómo despliego una aplicación en Kubernetes? | «No encuentro esa información.» |

## Cobertura

| Categoría | Preguntas | Qué mide |
|---|---|---|
| A. Consulta puntual | 10 | Calidad base de embeddings y chunk size; k=1. |
| B. Términos exactos | 10 | Necesidad de hybrid search (pregunta 6). |
| C. Conceptos | 9 | Chunk size: respuestas que ocupan un párrafo. |
| D. Varias fuentes | 3 | Si k=1 pierde información que k=2 recupera (pregunta 4). |
| E. Negativas | 3 | Fiabilidad ante preguntas sin respuesta (ruido de chunks grandes). |

Total: 35 preguntas.

## Pendiente

- Las fuentes de D01-D03 están indicadas a nivel de página. Falta fijar el chunk exacto una vez elegido el tamaño de chunk.
- Ampliar con preguntas formuladas por el equipo para evitar sesgo de quien las redacta.
- Cambiar el corpus (por ejemplo, otra versión de Python) obliga a revisar B04-B06 y C07-C09, que son específicas de 3.15.
