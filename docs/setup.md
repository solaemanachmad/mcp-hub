# Setup Guide

Follow these four steps in order. Never expose your Mac mini or Windows 11 PC ports to the public internet; keep internal traffic inside **Tailscale**.

---

## Step 1 — Oracle Cloud (Ubuntu VM + Tailscale + Docker)

### 1.1 Install Docker & Tailscale

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# Install Tailscale (private mesh network)
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
tailscale ip -4
```

### 1.2 Open Firewall Ports (Oracle Cloud Console + UFW)

In Oracle Cloud VCN **Security List** (and Ubuntu firewall if active), allow inbound TCP:
- `80` (HTTP, for Let's Encrypt certificate verification)
- `443` (HTTPS, public MCP & Kaggle API endpoint)
- Do **not** open `5432` (PostgreSQL) or `8000` publicly.

```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow in on tailscale0
sudo ufw enable
```

### 1.3 Configure `.env` and Start Services

```bash
git clone <your-repo-url> mcp-hub
cd mcp-hub
cp .env.example .env
```

Edit `.env`:
- `DOMAIN=mcp.yourdomain.com` *(or a free DuckDNS domain like `myhub.duckdns.org` pointed to Oracle's public IP; Caddy obtains HTTPS certificates automatically)*.
- Generate strong tokens with `openssl rand -hex 32` for `HUB_TOKEN`, `WORKER_TOKEN`, and `POSTGRES_PASSWORD`.
- Set `MAC_URL=http://<mac-tailscale-ip>:8100` (using Mac mini's `100.x.y.z` Tailscale IP works directly from Docker with zero DNS tweaks).

Launch the stack (works on both **ARM64 Ampere A1** and **AMD64 x86**):

```bash
docker compose up -d --build
curl http://127.0.0.1:8000/health
```

### Optional: Switch to Oracle Object Storage (S3)

Start with `STORAGE_MODE=local` on day 1. When ready to store thousands of PDFs in Oracle Cloud Always Free Object Storage (20 GB Standard), create a bucket + Customer Secret Key in Oracle Cloud Console and update `.env`:

```env
STORAGE_MODE=s3
S3_ENDPOINT=https://<namespace>.compat.objectstorage.<region>.oraclecloud.com
S3_REGION=ap-singapore-1
S3_BUCKET=mcp-hub-files
S3_ACCESS_KEY=<customer-secret-access-key>
S3_SECRET_KEY=<customer-secret-key>
```

---

## Step 2 — Mac mini M4 (16GB Unified Memory)

### 2.1 Install Tailscale & Ollama

1. Install **Tailscale** from the Mac App Store or `brew install --cask tailscale`, then sign in to the same Tailscale account.
2. Note your Mac mini's Tailscale IP:
   ```bash
   tailscale ip -4
   ```
3. Install **Ollama** (`brew install ollama`) and start it (`brew services start ollama`).
4. Pull models sized cleanly for **16GB Unified Memory**:
   ```bash
   ollama pull qwen2.5:7b
   ollama pull nomic-embed-text
   ```
   *(Alternative models for 16GB M4: `qwen3:8b`, `qwen2.5-coder:7b`. Keep total active model RAM under ~10GB so macOS and PDF processing stay snappy.)*

### 2.2 Run the Mac Local AI Service

```bash
cd mcp-hub
python3 -m venv .venv
source .venv/bin/activate
pip install -r mac/requirements.txt
cp .env.example .env
# Edit .env: set WORKER_TOKEN to match Oracle Cloud
uvicorn mac.main:app --host 0.0.0.0 --port 8100
```

Verify from Oracle Cloud over Tailscale:

```bash
curl http://<mac-tailscale-ip>:8100/health
```

---

## Step 3 — Office PC (Windows 11)

The Windows 11 worker uses **outbound polling only** — no inbound firewall ports are needed.

1. Install **Tailscale for Windows** and sign in to the same Tailscale account.
2. Open PowerShell in `mcp-hub`:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r pc\requirements.txt
   Copy-Item .env.example .env
   ```
3. Edit `.env` on Windows 11:
   ```env
   HUB_URL=https://mcp.yourdomain.com
   WORKER_TOKEN=<same-worker-token-as-oracle>
   NODE_NAME=pc
   WORK_DIR=.\runs
   ```
   *(If you prefer private Tailscale traffic instead of HTTPS, set `HUB_URL=http://<oracle-tailscale-ip>:8000` and expose port 8000 on the Tailscale interface.)*
4. Place your local experiment scripts inside `.\runs\` (for example `.\runs\train.py`) and start the worker:
   ```powershell
   python -m pc.worker
   ```

### Sample PC Experiment Script (`runs/demo.py`)

```python
import json, os

with open(os.environ["EXP_CONFIG"], "r", encoding="utf-8") as f:
    cfg = json.load(f)

metrics = {"accuracy": 0.91, "f1": 0.89, "lr": cfg.get("lr", 0.001)}
with open(os.environ["EXP_METRICS"], "w", encoding="utf-8") as f:
    json.dump(metrics, f)
print("Done:", metrics)
```

---

## Step 4 — Kaggle GPU Compute

1. Upload `kaggle/template.ipynb` to Kaggle Notebooks.
2. Enable **GPU (T4 x2 / P100)** and **Internet** in notebook settings.
3. Open **Add-ons → Secrets** and add:
   - `HUB_URL` = `https://mcp.yourdomain.com`
   - `WORKER_TOKEN` = `<your-worker-token>`
4. Ask any AI client: *"Submit a Kaggle experiment for project `general` with `epochs=20` and `lr=0.001`."*
5. Run the Kaggle notebook — it automatically claims the job, trains on GPU, and pushes metrics back to Oracle Cloud.
6. *(Optional)* Add `KAGGLE_USERNAME` and `KAGGLE_KEY` to Oracle Cloud `.env` to enable `kaggle_datasets`, `kaggle_status`, and `kaggle_output` MCP tools.
