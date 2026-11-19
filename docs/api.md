# MCP Tools & REST API Reference

## MCP Tools (`/mcp`) — 27 Tools + 3 Prompts Across 9 Modules

### 1. Research & Cross-Project RAG (`hub/tools/research.py`)
| Tool | Purpose |
|---|---|
| `search_papers(query, limit=5, source="all")` | Search Semantic Scholar and arXiv with automatic fallback |
| `lookup_doi(doi)` | Retrieve verified CrossRef metadata for a DOI |
| `ingest_pdf(project, title, pdf_url_or_key, doi="", authors="", year=None, method="", dataset_used="", key_metrics="", limitations="")` | Extract PDF chunks directly on Oracle Cloud, generate API summary + embeddings, and store in `pgvector` |
| `search_kb(query, project="all", category="", top_k=5)` | Semantic RAG search within one project, across a project category, or across `'all'` projects |

### 2. Multi-Project Categorization & Shared Memory (`hub/tools/memory.py`)
| Tool | Purpose |
|---|---|
| `create_project(slug, name, category="research", status="active", description="", tags=None)` | Create/update project (`category`: `research`, `ml`, `software`, `teaching`; `status`: `active`, `paused`, `completed`, `archived`) |
| `list_projects(category="", status="")` | List projects with counts of papers, datasets, notes, and experiments |
| `save_note(project, title, content, author_ai="unknown", tags=None)` | Save decisions/findings shared across all AI clients |
| `get_context(project="general", limit=8)` | Compact project briefing (notes, paper count, latest experiments) |

### 3. Dataset Registry & Kaggle Dataset Linking (`hub/tools/dataset.py`)
| Tool | Purpose |
|---|---|
| `register_dataset(slug, project, name, location="kaggle", kaggle_ref="", mount_path="", fmt="csv", num_samples=0, num_classes=0, size_mb=0.0, description="")` | Register a dataset stored on Kaggle (`kaggle_ref="user/dataset"` auto-mounts at `/kaggle/input/...`), PC, or Oracle |
| `list_datasets(project="", location="")` | List registered datasets filtered by project and/or location (`kaggle`, `pc`) |
| `get_dataset(slug)` | Retrieve full dataset metadata, Kaggle ref, and mount path |

### 4. Academic Writer & Literature Review Matrix (`hub/tools/writer.py`)
| Tool | Purpose |
|---|---|
| `update_review(paper_id, method="", dataset_used="", key_metrics="", limitations="")` | Populate/update structured Literature Review Matrix fields for a paper |
| `paper_matrix(project, fmt="markdown")` | Generate a Literature Review Matrix comparing papers (`markdown` or `latex`) |
| `export_bibtex(project)` | Export standard `.bib` citations for all papers in a project |
| `exp_table(project, metrics=None, fmt="latex", caption="...")` | Generate a publication-ready LaTeX (`booktabs`) or Markdown table of experiment results |

### 5. Cloud AI Helper API (`hub/tools/ai.py`)
| Tool | Purpose |
|---|---|
| `ask_ai(prompt, system="", model="")` | Run a prompt on Oracle Cloud's configured low-cost AI API (Gemini Flash, Qwen, GPT-4o-mini, DeepSeek) |
| `summarize_text(text, focus="...", max_words=200)` | Compress long logs/papers on the server before feeding into your primary AI client |
| `ai_status()` | Check configured AI API provider, chat model, and embedding model |

### 6. Experiment Orchestrator (`hub/tools/exp.py`)
| Tool | Purpose |
|---|---|
| `list_nodes()` | List compute nodes (`pc`, `kaggle`) and live online/offline status |
| `submit_exp(project, name, target_node="auto", dataset_slug="", kaggle_datasets=None, script="", config={}, created_by="ai")` | Queue an experiment (`auto` routes Kaggle-stored datasets & GPU runs directly to `kaggle` and injects `dataset_path`) |
| `exp_status(exp_id)` | Check experiment status, linked dataset, and recent log tail |
| `exp_result(exp_id)` | Retrieve full config, metrics, logs, and artifact link |
| `compare_exps(project, metric="f1", limit=10)` | Rank project experiments by any metric |

### 7. Kaggle Integration (`hub/tools/kaggle.py`)
| Tool | Purpose |
|---|---|
| `kaggle_datasets(query, limit=5)` | Search Datasets on Kaggle |
| `kaggle_manifest(exp_id, kernel_id="...", enable_gpu=True)` | Generate `kernel-metadata.json` with `dataset_sources` auto-filled from the experiment's linked Kaggle datasets |
| `kaggle_status(kernel_slug)` | Check execution status of a Kaggle kernel |
| `kaggle_output(kernel_slug)` | List output artifact files from a completed Kaggle kernel |

### 8. Telegram & Webhook Alerts (`hub/tools/notify.py`)
| Tool | Purpose |
|---|---|
| `send_alert(title, message)` | Send an instant notification to Telegram or Discord/Slack webhook (also triggers automatically when any experiment finishes) |

### 9. Reusable Prompts & Backup (`hub/tools/prompts.py`)
| Item | Purpose |
|---|---|
| `backup_project(project)` | Export a complete portable JSON snapshot of a project |
| Prompt `lit_review` | 1-click workflow template for literature review |
| Prompt `plan_exp` | 1-click workflow template for designing a Kaggle/PC experiment |
| Prompt `ai_handoff` | 1-click workflow template for saving session state before switching AI clients |
