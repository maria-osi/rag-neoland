# AGENTS.md

## Gestión del entorno: siempre `uv`

- Usa **siempre `uv`**. Nunca `pip`, `pip install`, `python -m venv`, `conda` ni `poetry`.
- Añadir una librería: `uv add <paquete>` (queda en `pyproject.toml` y `uv.lock`).
- Quitar una librería: `uv remove <paquete>`.
- Sincronizar el entorno: `uv sync`.
- Ejecutar scripts: `uv run python <script.py>`.
- El entorno vive en `.venv/` y lo gestiona `uv`. No lo borres ni lo recrees a mano.
- En notebooks, no uses `!pip install`. Las dependencias se declaran con `uv add`.
- Versión de Python: la de `.python-version` y `pyproject.toml`.

## Forma de trabajar

- Responde en **español**.
- No añadas funcionalidades que no se hayan pedido.
- Mantén los notebooks ordenados: una celda por paso, con un título en markdown.

## Flujo de entrega (paquete `delivery-workflow`)

Instalado con `apm` (versión fijada en `apm.yml`). Los agentes y skills viven en `.claude/agents/` y `.claude/skills/`; la lista real está ahí, no aquí. No los edites a mano: `apm install` los regenera.

- **Punto de entrada:** `/delivery-workflow` y pedir la tarea con palabras normales. Comprobar el entorno: `/check-status`.
- **Token:** `GITHUB_TOKEN` en `.env` (clásico, permiso `repo`). Nunca lo muestres ni lo subas.
- **Rama base:** `main` (no existe `staging`). Las ramas se llaman `número-tipo-descripcion`.
- **Tipos de tarea:** los que define la skill `create-issue` (mira sus plantillas en `.claude/skills/create-issue/assets/`).
- **Títulos de issue y commits en inglés; el resto, en español.**
- **Nunca hagas merge** a `main`: lo hace la persona.
- **Actualizar el paquete:** cambia la versión en `apm.yml`, `apm install` y commit. Después de cada `apm install`, ejecuta `/configure-models`.

### Modo por defecto: flujo completo

El flujo se usa **completo**: los agentes escriben el código y los tests (`code-developer` y `code-tester`), la spec, el plan y las tasks (`concept-developer`), y llevan la tarea hasta la pull request en draft y la petición de revisión.

Si la persona pide «solo git», el flujo para en la pull request en draft y el código lo escribe ella.
