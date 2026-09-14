# Drug Repurposing Agent

This repository is packaged as a Cloudera AI AMP. The prototype combines a
seeded biomedical knowledge graph, graph traversal, deterministic opportunity
scoring, and configurable LLM discovery narration in a Flask API with a React UI.

## Deploy in Cloudera AI

1. Import the repository as an AMP. The import manifest is
   [`.project-metadata.yaml`](.project-metadata.yaml); `project.yaml` is the
   companion deployment contract.
2. Run **Install Dependencies**. It installs `requirements.txt`, installs the
   frontend packages, and builds `frontend/dist`.
3. Run **Verify Prepared Demo**. This checks the graph, graph tools, Python
   syntax, and production frontend without making an external API call.
4. Configure the LLM environment variables. For an OpenAI-compatible API, set
   `LLM_PROVIDER=openai-compatible`, `LLM_API_KEY` (or `OPENAI_API_KEY`),
   `LLM_MODEL`, and optionally `LLM_BASE_URL` (or `OPENAI_API_BASE`). For Anthropic compatibility,
   set `LLM_PROVIDER=anthropic` and `ANTHROPIC_API_KEY`.
5. Start **Drug Repurposing Agent**. The application uses 2 vCPU and 4 GB RAM,
   serves the React bundle, and launches the Flask API through `cml_app.py`.

The application requires a configured LLM token for publication extraction and
discovery requests. The seeded graph and deterministic scoring checks remain
available for offline preparation and validation.

## Local development

```bash
pip install -r requirements.txt
cd frontend && npm install && npm run build
cd .. && python cai_integration/validate_amp.py
python cai_integration/smoke_test.py
LLM_PROVIDER=openai-compatible LLM_API_KEY=<your_key> LLM_MODEL=gpt-4o-mini python cml_app.py
```

The app binds to `CDSW_APP_PORT` when provided by Cloudera AI, and otherwise
defaults to port 8080.
