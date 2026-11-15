# AGENTS.md

Proyecto de aprendizaje: bootcamp Neoland. Quien lo usa está aprendiendo Python e IA ahora mismo.

## Gestión del entorno: siempre `uv`

- Usa **siempre `uv`**. Nunca `pip`, `pip install`, `python -m venv`, `conda` ni `poetry`.
- Añadir una librería: `uv add <paquete>` (queda en `pyproject.toml` y `uv.lock`).
- Quitar una librería: `uv remove <paquete>`.
- Sincronizar el entorno: `uv sync`.
- Ejecutar scripts: `uv run python <script.py>`.
- El entorno vive en `.venv/` y lo gestiona `uv`. No lo borres ni lo recrees a mano.
- En notebooks, no uses `!pip install`. Las dependencias se declaran con `uv add`.
- Versión de Python: la de `.python-version` y `pyproject.toml`.

## Estilo de código: nivel junior

El código debe poder entenderlo alguien que está aprendiendo.

- Prefiere **bucles `for` normales** a list comprehensions, `map`, `filter`, `lambda` o generadores anidados.
- Código **simple y explícito**. Nada de trucos, one-liners densos ni abstracciones innecesarias.
- Nombres de variables **largos y descriptivos**, en español cuando tenga sentido (`frases`, `tema`, `corpus`).
- **Pocas funciones**, cortas, con una sola responsabilidad. Sin clases si no hacen falta.
- Divide los pasos en variables intermedias en lugar de encadenar llamadas.
- Añade **comentarios breves** que expliquen el *porqué* de cada paso. No expliques lo obvio.
- Evita sintaxis avanzada: decoradores, metaclases, `*args/**kwargs`, walrus `:=`, type hints complejos.
- Si usas algo nuevo (por ejemplo `np.argsort`, `@` de matrices), **explica en una línea qué hace** con un comentario.
- Antes de dar una versión compacta, da la versión larga y clara. Ofrece la compacta solo si se pide.

## Forma de trabajar

- Responde en **español**.
- Explica paso a paso y deja que la persona escriba el código cuando sea un ejercicio. Da pistas antes que soluciones completas.
- No añadas funcionalidades que no se hayan pedido.
- Mantén los notebooks ordenados: una celda por paso, con un título en markdown.
