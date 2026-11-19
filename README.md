# mcp-hub

A unified, multi-node **MCP (Model Context Protocol) Hub** connecting **Oracle Cloud**, **Mac mini M4 (16GB)**, **Office PC (Windows 11)**, and **Kaggle GPU** into one shared AI research and ML infrastructure.

Every AI client — **Claude Desktop, Antigravity, ChatGPT, CodeBuddy, WorkBuddy, Qwen** — connects to the same remote MCP endpoint, shares the same project memory, and delegates heavy text/embedding work to local Qwen on Mac mini M4 to maximize cloud token budgets.

## Architecture

```text
  [Claude Desktop] [Antigravity] [ChatGPT] [CodeBuddy] [WorkBuddy] [Qwen]
         \               |           |           |           |        /
          +--------------+-----------+-----------+-----------+-------+
                                     |  MCP Streamable HTTP (HTTPS + Bearer Token)
                                     v
          +----------------------------------------------------------+
          |               Oracle Cloud (hub/ + infra/)               |
          |  - Caddy HTTPS Reverse Proxy                             |
          |  - Unified MCP Server (/mcp)                             |
          |  - Experiment Orchestrator API (/api)                    |
          |  - PostgreSQL + pgvector + Hybrid Storage (Local / S3)   |
          +----------------------------------------------------------+
                 /                   |                      \
     Tailscale  /         Tailscale  |                       \ HTTPS + Kaggle API
               v                     v                        v
     +------------------+   +------------------+    +--------------------+
     | Mac mini M4 16GB |   | Office PC Win 11 |    |     Kaggle GPU     |
     | (mac/)           |   | (pc/)            |    | (kaggle/)          |
     | - Ollama Qwen    |   | - Job Worker     |    | - template.ipynb   |
     | - Embeddings     |   | - Local Python   |    | - Pull Config      |
     | - PDF Extraction |   | - Local Datasets |    | - Push Metrics     |
     +------------------+   +------------------+    +--------------------+
```

## Project Layout

```text
mcp-hub/
├── README.md
├── .env.example
├── docker-compose.yml
├── pyproject.toml
├── infra/          # Dockerfile, Caddyfile, init.sql (PostgreSQL + pgvector)
├── hub/            # Oracle Cloud unified MCP server + Orchestrator API
│   ├── services/   # papers, rag, memory, mac, exp, kaggle
│   └── tools/      # research, memory, local, exp, kaggle
├── mac/            # Mac mini M4 (16GB) Ollama + PDF & embedding service
├── pc/             # Windows 11 experiment worker daemon
├── kaggle/         # Kaggle GPU pull-based runner & template notebook
├── docs/           # setup.md, clients.md, api.md
└── tests/          # Unit tests
```

## Quick Start

1. Copy `.env.example` to `.env` and set strong random values for `HUB_TOKEN`, `WORKER_TOKEN`, and `POSTGRES_PASSWORD`.
2. Follow [docs/setup.md](docs/setup.md) to install **Tailscale** and deploy on Oracle Cloud, Mac mini M4, Windows 11 PC, and Kaggle.
3. Connect all your AI clients using [docs/clients.md](docs/clients.md).
4. Explore every MCP tool and REST endpoint in [docs/api.md](docs/api.md).
