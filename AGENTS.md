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
- **Ramas:** el trabajo pasa por tres niveles:
  1. **Rama de trabajo** `número-tipo-descripcion`, creada desde `staging`.
  2. **`staging`** (rama base): las pull requests de las tareas se abren contra ella. Los scripts del paquete la detectan solos porque existe en `origin`.
  3. **`main`**: recibe `staging` con una pull request `staging` → `main` cuando lo integrado está probado.
- Antes de crear una rama de trabajo, `staging` tiene que estar al día con `main`.
- **Tipos de tarea:** los que define la skill `create-issue` (mira sus plantillas en `.claude/skills/create-issue/assets/`).
- **Títulos de issue y commits en inglés; el resto, en español.**
- **Nunca hagas merge** a `staging` ni a `main`: los dos los hace la persona.
- **Actualizar el paquete:** cambia la versión en `apm.yml`, `apm install` y commit. Después de cada `apm install`, ejecuta `/configure-models`.

### Modo por defecto: flujo completo

El flujo se usa **completo**: los agentes escriben el código y los tests (`code-developer` y `code-tester`), la spec, el plan y las tasks (`concept-developer`), y llevan la tarea hasta la pull request en draft y la petición de revisión.

Si la persona pide «solo git», el flujo para en la pull request en draft y el código lo escribe ella.
