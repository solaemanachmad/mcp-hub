# Connecting AI Clients

All AI clients connect to the **same remote MCP endpoint** on Oracle Cloud:

- **URL:** `https://mcp.yourdomain.com/mcp`
- **Transport:** Streamable HTTP (`stateless_http=True`)
- **Auth Header:** `Authorization: Bearer <HUB_TOKEN>`

Install AI clients directly on your **Windows 11 PC** and/or **Mac mini M4** (never on Oracle Cloud).

---

## 1. Test First with MCP Inspector

```bash
npx @modelcontextprotocol/inspector
```

Select **Streamable HTTP**, enter `https://mcp.yourdomain.com/mcp`, add header `Authorization: Bearer <HUB_TOKEN>`, and verify all tools appear.

---

## 2. Claude Desktop (Windows 11 / macOS)

If your Claude Desktop version supports remote MCP connectors directly in **Settings → Connectors**, add:
- **URL:** `https://mcp.yourdomain.com/mcp`
- **Header:** `Authorization: Bearer <HUB_TOKEN>`

Or via `mcp-remote` bridge in `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mcp-hub": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "https://mcp.yourdomain.com/mcp",
        "--header",
        "Authorization: Bearer YOUR_HUB_TOKEN"
      ]
    }
  }
}
```

---

## 3. Antigravity / VS Code / Cursor / CodeBuddy / WorkBuddy

Add the remote MCP server in your IDE MCP config (`mcp_config.json` or `.vscode/mcp.json`):

```json
{
  "mcpServers": {
    "mcp-hub": {
      "serverUrl": "https://mcp.yourdomain.com/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_HUB_TOKEN"
      }
    }
  }
}
```

*(Some IDE clients use the key `"url"` instead of `"serverUrl"` with `"type": "http"` — adjust the field name to match your client schema.)*

---

## 4. ChatGPT (Remote MCP Connector)

In ChatGPT **Settings → Connectors / Apps → Add Custom MCP Server**:
- **Server URL:** `https://mcp.yourdomain.com/mcp`
- **Authentication:** Bearer Token (`YOUR_HUB_TOKEN`)

---

## 5. Qwen / Local Clients (Mac mini M4 or Windows 11)

Any MCP-compatible local client (Qwen Code, Open WebUI with MCP bridge, Cline, Continue) can connect to the same `https://mcp.yourdomain.com/mcp` endpoint using the exact same Bearer token.

---

## Multi-AI Token-Saving Workflow

1. **Start any session** (Claude, Antigravity, ChatGPT, CodeBuddy, Qwen) with:
   > *"Call `get_context` for project `eye_movement`."*
2. **Offload heavy text work** to Mac mini M4:
   > *"Use `ingest_pdf` and `summarize_local` to process these papers before we compare methods."*
3. **Save handoff state** before switching AI or hitting token limits:
   > *"Call `save_note` with `author_ai='claude'` summarizing our decisions and next steps."*
4. **Resume on another AI** with zero manual copy-paste.
