# Setup Guide

Follow these three steps. Because PDF extraction runs directly inside Oracle Cloud and embeddings/summaries use an API (`AI_API_KEY`), you do **not** need to install Ollama or run any background server on your Mac mini.

---

## Step 1 — Oracle Cloud (Ubuntu VM + Docker)

### 1.1 Install Docker (& Optional Tailscale)

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# Optional: Install Tailscale if you want private networking to your Office PC
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

### 1.2 Open Firewall Ports (Oracle Cloud Console + UFW)

In Oracle Cloud VCN **Security List** (and Ubuntu firewall if active), allow inbound TCP:
- `80` (HTTP, for Let's Encrypt certificate verification)
- `443` (HTTPS, public MCP, Dashboard, Worker & Kaggle endpoint)
- Do **not** open `5432` (PostgreSQL) or `8000` publicly.

```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 1.3 Clone `mcp-hub` and Configure `.env`

```bash
git clone https://github.com/solaemanachmad/mcp-hub.git
cd mcp-hub
cp .env.example .env
sed -i "s/change-me-hub-token/$(openssl rand -hex 24)/" .env
sed -i "s/change-me-worker-token/$(openssl rand -hex 24)/" .env
sed -i "s/change-me-db-password/$(openssl rand -hex 16)/g" .env
```

Edit `.env` (`nano .env`) to set:
- `DOMAIN=mcp.yourdomain.com` *(or leave `:80` to test via IP first)*.
- **AI & Embedding API (`AI_BASE_URL`, `AI_API_KEY`, `AI_MODEL`, `EMBED_MODEL`)** — choose any provider:
  - **Google Gemini API (Free tier available):**
    ```env
    AI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
    AI_API_KEY=your-gemini-api-key
    AI_MODEL=gemini-2.5-flash
    EMBED_MODEL=text-embedding-004
    ```
  - **OpenAI API:**
    ```env
    AI_BASE_URL=https://api.openai.com/v1
    AI_API_KEY=sk-...
    AI_MODEL=gpt-4o-mini
    EMBED_MODEL=text-embedding-3-small
    ```
  - **Qwen (Alibaba DashScope API):**
    ```env
    AI_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
    AI_API_KEY=sk-...
    AI_MODEL=qwen-plus
    EMBED_MODEL=text-embedding-v3
    ```

Launch the stack:

```bash
docker compose up -d --build
curl http://127.0.0.1:8000/health
```

Open your status dashboard in any browser:
`https://mcp.yourdomain.com/dashboard?token=<YOUR_HUB_TOKEN>`

---

## Step 2 — Office PC (Windows 11 Worker)

The Windows 11 worker uses **outbound polling only** — no inbound firewall ports are needed.

1. Open PowerShell in `mcp-hub`:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r pc\requirements.txt
   Copy-Item .env.example .env
   ```
2. Edit `.env` on Windows 11:
   ```env
   HUB_URL=https://mcp.yourdomain.com
   WORKER_TOKEN=<same-worker-token-as-oracle>
   NODE_NAME=pc
   WORK_DIR=.\runs
   ```
3. Place local experiment scripts inside `.\runs\` and start the worker:
   ```powershell
   python -m pc.worker
   ```

---

## Step 3 — Kaggle GPU Compute

1. Upload `kaggle/template.ipynb` to Kaggle Notebooks.
2. Enable **GPU (T4 x2 / P100)** and **Internet** in notebook settings.
3. Open **Add-ons → Secrets** and add:
   - `HUB_URL` = `https://mcp.yourdomain.com`
   - `WORKER_TOKEN` = `<your-worker-token>`
4. Attach your Kaggle Dataset (e.g. GazeCom) to the notebook and run it — it claims the queued job, trains on GPU, pushes metrics to Oracle Cloud, and sends a Telegram/Webhook alert to your phone.
