"""Telegram Bot and Webhook notifications for experiment completion and research alerts."""

from __future__ import annotations

from typing import Any

import httpx

from hub.config import get_settings


async def send_alert(title: str, message: str) -> dict[str, Any]:
    """Send an alert to configured Telegram chat and/or Webhook URL."""
    settings = get_settings()
    text = f"*{title}*\n{message}" if title else message
    sent_to: list[str] = []
    errors: list[str] = []

    if settings.telegram_token and settings.telegram_chat:
        url = f"https://api.telegram.org/bot{settings.telegram_token}/sendMessage"
        payload = {
            "chat_id": settings.telegram_chat,
            "text": text,
            "parse_mode": "Markdown",
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
            sent_to.append("telegram")
        except Exception as exc:
            errors.append(f"telegram: {exc}")

    if settings.webhook_url:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    settings.webhook_url,
                    json={"title": title, "content": message, "text": text},
                )
                resp.raise_for_status()
            sent_to.append("webhook")
        except Exception as exc:
            errors.append(f"webhook: {exc}")

    return {
        "configured": bool(sent_to or errors),
        "sent_to": sent_to,
        "errors": errors,
    }


async def notify_experiment_done(exp: dict[str, Any]) -> None:
    """Best-effort alert when a PC or Kaggle GPU experiment completes or fails."""
    status = exp.get("status", "completed").upper()
    metrics = exp.get("metrics") or {}
    metric_str = ", ".join(f"{k}={v}" for k, v in list(metrics.items())[:6]) or "none"
    title = f"Experiment {status}: {exp.get('name', exp.get('id'))}"
    msg = (
        f"ID: `{exp.get('id')}`\n"
        f"Project: `{exp.get('project_slug')}`\n"
        f"Node: `{exp.get('target_node')}`\n"
        f"Dataset: `{exp.get('dataset_slug') or '-'}`\n"
        f"Metrics: {metric_str}"
    )
    try:
        await send_alert(title, msg)
    except Exception:
        pass
