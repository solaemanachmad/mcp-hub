"""FastAPI Local AI & PDF processing service for Mac mini M4 (16GB)."""

from __future__ import annotations

import hmac
from typing import Any

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from pydantic import BaseModel, Field

from mac import ollama, pdf
from mac.config import get_settings

app = FastAPI(title="Mac Local AI Service", version="0.1.0")


def verify_token(authorization: str = Header(default="")) -> None:
    cfg = get_settings()
    token = authorization[7:].strip() if authorization.lower().startswith("bearer ") else ""
    if not token or not hmac.compare_digest(token, cfg.worker_token):
        raise HTTPException(status_code=401, detail="Unauthorized")


class ChatRequest(BaseModel):
    prompt: str
    system: str = ""
    model: str = ""


class SummarizeRequest(BaseModel):
    text: str
    focus: str = "key findings and methodology"
    max_words: int = 200


class EmbedRequest(BaseModel):
    texts: list[str] = Field(default_factory=list)
    model: str = ""


@app.get("/health")
async def health() -> dict[str, Any]:
    cfg = get_settings()
    models: list[str] = []
    ollama_ok = True
    try:
        models = await ollama.list_models()
    except Exception:
        ollama_ok = False
    return {
        "status": "ok" if ollama_ok else "degraded",
        "node": "mac",
        "default_llm": cfg.ollama_model,
        "embed_model": cfg.embed_model,
        "ollama_online": ollama_ok,
        "models": models,
    }


@app.post("/chat", dependencies=[Depends(verify_token)])
async def run_chat(req: ChatRequest) -> dict[str, Any]:
    return await ollama.chat(prompt=req.prompt, system=req.system, model=req.model)


@app.post("/summarize", dependencies=[Depends(verify_token)])
async def run_summarize(req: SummarizeRequest) -> dict[str, Any]:
    system = (
        f"You are a concise research assistant. Summarize the text focusing on {req.focus}. "
        f"Keep the summary under {req.max_words} words using bullet points."
    )
    # Trim very long inputs to stay fast and light on 16GB unified memory
    snippet = req.text[:24000]
    res = await ollama.chat(prompt=snippet, system=system)
    return {"model": res["model"], "summary": res["reply"]}


@app.post("/embed", dependencies=[Depends(verify_token)])
async def run_embed(req: EmbedRequest) -> dict[str, Any]:
    vectors = await ollama.embed(texts=req.texts, model=req.model)
    return {"count": len(vectors), "embeddings": vectors}


@app.post("/pdf/extract", dependencies=[Depends(verify_token)])
async def extract_pdf(
    file: UploadFile = File(...),
    summarize: bool = Form(True),
) -> dict[str, Any]:
    raw = await file.read()
    text, page_count = pdf.extract_text(raw)
    chunks = pdf.chunk_text(text)

    summary = ""
    if summarize and text:
        try:
            res = await ollama.chat(
                prompt=text[:18000],
                system=(
                    "Summarize this academic paper in under 200 words: "
                    "problem, method, dataset, and key quantitative findings."
                ),
            )
            summary = res["reply"]
        except Exception:
            summary = ""

    return {
        "filename": file.filename,
        "pages": page_count,
        "chunk_count": len(chunks),
        "chunks": chunks,
        "summary": summary,
    }
