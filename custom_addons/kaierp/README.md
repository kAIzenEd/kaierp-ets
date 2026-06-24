kAI-ERP — Local AI integration

This addon includes helpers to integrate local Ollama models (via CrewAI) and
`odoorpc` for querying your Odoo database from an AI agent.

Setup

1. Create a Python virtual environment in the addon and install dependencies:

```bash
cd /path/to/odoo/addons/kaierp
./scripts/setup_venv.sh
```

2. Activate the virtualenv when using CLI tooling or running Odoo in that env:

```bash
source .venv/bin/activate
# start Odoo from this environment so it uses the same packages
./odoo-bin -c /etc/odoo/odoo.conf
```

Notes on usage from the addon

- If you run Odoo under a different Python interpreter than the addon venv,
  you can call scripts in `scripts/` with `subprocess` from Odoo code.
- Alternatively, run the Odoo server using the venv so the addon can
  `import kaierp.models.ai_agent` directly.

Example (server-side import in Odoo code)

```python
from .models.ai_agent import AIAgent

agent = AIAgent(db="mydb", user="odoo", password="secret")
answer = agent.answer_query('school.student', 'Summarize recent grades for class 10')
```

Adjust the CrewAI client calls in `models/ai_agent.py` to match the exact
API of the CrewAI package you install (some clients use `generate`,
`predict` or other method names).
