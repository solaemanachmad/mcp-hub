# mcp-hub

A unified **MCP (Model Context Protocol) Hub** running 24/7 on **Oracle Cloud**, connecting your **Office PC (Windows 11)** and **Kaggle GPU** into one shared AI research and ML infrastructure — with zero local LLM maintenance.

Every AI client — **Claude Desktop, Antigravity, ChatGPT, CodeBuddy, WorkBuddy, Qwen** (whether on your Office PC or on your Mac mini when traveling) — connects to the same remote MCP endpoint, shares the same project memory, and processes PDFs, embeddings, and experiments centrally.

## Architecture

```text
  [Claude Desktop] [Antigravity] [ChatGPT] [CodeBuddy] [WorkBuddy] [Qwen]
  (Installed on your Office PC Win 11 & Mac mini M4 for mobile/remote work)
         \               |           |           |           |        /
          +--------------+-----------+-----------+-----------+-------+
                                     |  MCP Streamable HTTP (HTTPS + Bearer Token)
                                     v
          +----------------------------------------------------------+
          |            1. Oracle Cloud (hub/ + infra/)               |
          |  - Caddy HTTPS Reverse Proxy                             |
          |  - Unified MCP Server (/mcp) + Web Dashboard (/dashboard)|
          |  - Built-in PDF Extractor & Chunker (pypdf)              |
          |  - Cloud AI & Embedding API (OpenAI / Gemini / Qwen API) |
          |  - Experiment Orchestrator API (/api)                    |
          |  - PostgreSQL + pgvector + Hybrid Storage (Local / S3)   |
          +----------------------------------------------------------+
                         /                              \
       HTTPS / Tailscale/                                \ HTTPS + Kaggle API
                       v                                  v
            +--------------------+              +--------------------+
            | 2. Office PC Win11 |              |   3. Kaggle GPU    |
            | (pc/)              |              | (kaggle/)          |
            | - Always-on worker |              | - Kaggle Datasets  |
            | - Local Python/ML  |              | - template.ipynb   |
            | - Local Datasets   |              | - Heavy GPU Train  |
            +--------------------+              +--------------------+
```

## Project Layout

```text
mcp-hub/
├── README.md
├── .env.example
├── docker-compose.yml
├── pyproject.toml
├── infra/          # Dockerfile, Caddyfile, init.sql (PostgreSQL + pgvector)
├── hub/            # Oracle Cloud unified MCP server + Orchestrator API + Dashboard
│   ├── services/   # ai, exp, kaggle, memory, notify, papers, pdf, rag, writer
│   └── tools/      # ai, dataset, exp, kaggle, memory, notify, prompts, research, writer
├── pc/             # Windows 11 experiment worker daemon
├── kaggle/         # Kaggle GPU pull-based runner & template notebook
├── docs/           # setup.md, clients.md, api.md
└── tests/          # Unit tests
```

## Quick Start

1. Copy `.env.example` to `.env` on Oracle Cloud and set `HUB_TOKEN`, `WORKER_TOKEN`, `POSTGRES_PASSWORD`, and `AI_API_KEY`.
2. Follow [docs/setup.md](docs/setup.md) to deploy on Oracle Cloud, Office PC (Windows 11), and Kaggle.
3. Connect all your AI clients on Windows 11 and Mac mini using [docs/clients.md](docs/clients.md).
4. Explore every MCP tool and REST endpoint in [docs/api.md](docs/api.md).
