"""Async PostgreSQL + pgvector repository for MCP Hub."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

import asyncpg

from hub.config import get_settings


def _vec_literal(embedding: list[float] | None) -> str | None:
    if not embedding:
        return None
    return "[" + ",".join(f"{float(v):.6f}" for v in embedding) + "]"


def _decode_json(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


class Database:
    """Async PostgreSQL connection pool and domain queries."""

    def __init__(self) -> None:
        self.pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        if self.pool is not None:
            return
        settings = get_settings()
        self.pool = await asyncpg.create_pool(
            dsn=settings.database_url,
            min_size=1,
            max_size=10,
        )

    async def close(self) -> None:
        if self.pool is not None:
            await self.pool.close()
            self.pool = None

    def _require_pool(self) -> asyncpg.Pool:
        if self.pool is None:
            raise RuntimeError("Database pool is not connected.")
        return self.pool

    # ------------------------------------------------------------------
    # Projects (with category, status, and tags)
    # ------------------------------------------------------------------

    async def ensure_project(
        self,
        slug: str,
        name: str | None = None,
        description: str = "",
        category: str = "research",
        status: str = "active",
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        pool = self._require_pool()
        clean_slug = slug.strip().lower().replace(" ", "_") or "general"
        clean_cat = (category or "research").strip().lower()
        clean_status = (status or "active").strip().lower()
        row = await pool.fetchrow(
            """
            INSERT INTO projects (slug, name, category, status, description, tags)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (slug) DO UPDATE
            SET name = CASE WHEN EXCLUDED.name <> '' THEN EXCLUDED.name ELSE projects.name END,
                category = CASE WHEN EXCLUDED.category <> '' THEN EXCLUDED.category ELSE projects.category END,
                status = CASE WHEN EXCLUDED.status <> '' THEN EXCLUDED.status ELSE projects.status END,
                description = CASE WHEN EXCLUDED.description <> '' THEN EXCLUDED.description ELSE projects.description END,
                tags = CASE WHEN array_length(EXCLUDED.tags, 1) > 0 THEN EXCLUDED.tags ELSE projects.tags END
            RETURNING id, slug, name, category, status, description, tags, created_at
            """,
            clean_slug,
            name or clean_slug.replace("_", " ").title(),
            clean_cat,
            clean_status,
            description,
            tags or [],
        )
        return dict(row)

    async def list_projects(self, category: str = "", status: str = "") -> list[dict[str, Any]]:
        pool = self._require_pool()
        rows = await pool.fetch(
            """
            SELECT p.slug, p.name, p.category, p.status, p.description, p.tags, p.created_at,
                   (SELECT COUNT(*) FROM papers WHERE project_slug = p.slug) AS paper_count,
                   (SELECT COUNT(*) FROM datasets WHERE project_slug = p.slug) AS dataset_count,
                   (SELECT COUNT(*) FROM notes WHERE project_slug = p.slug) AS note_count,
                   (SELECT COUNT(*) FROM experiments WHERE project_slug = p.slug) AS exp_count
            FROM projects p
            WHERE ($1 = '' OR p.category = $1)
              AND ($2 = '' OR p.status = $2)
            ORDER BY p.created_at DESC
            """,
            category.strip().lower(),
            status.strip().lower(),
        )
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Shared Cross-AI Memory Notes
    # ------------------------------------------------------------------

    async def save_note(
        self,
        project_slug: str,
        title: str,
        content: str,
        author_ai: str = "unknown",
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        proj = await self.ensure_project(project_slug)
        pool = self._require_pool()
        row = await pool.fetchrow(
            """
            INSERT INTO notes (project_slug, title, content, author_ai, tags)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, project_slug, title, content, author_ai, tags, created_at
            """,
            proj["slug"],
            title,
            content,
            author_ai,
            tags or [],
        )
        return dict(row)

    async def list_notes(self, project_slug: str, limit: int = 10) -> list[dict[str, Any]]:
        pool = self._require_pool()
        rows = await pool.fetch(
            """
            SELECT id, title, content, author_ai, tags, created_at
            FROM notes
            WHERE project_slug = $1
            ORDER BY created_at DESC
            LIMIT $2
            """,
            project_slug,
            limit,
        )
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Papers, Literature Review Matrix & RAG Chunks
    # ------------------------------------------------------------------

    async def save_paper(
        self,
        project_slug: str,
        title: str,
        authors: str = "",
        year: int | None = None,
        doi: str = "",
        url: str = "",
        abstract: str = "",
        summary: str = "",
        method: str = "",
        dataset_used: str = "",
        key_metrics: str = "",
        limitations: str = "",
        storage_key: str = "",
    ) -> dict[str, Any]:
        proj = await self.ensure_project(project_slug)
        pool = self._require_pool()
        row = await pool.fetchrow(
            """
            INSERT INTO papers (
                project_slug, title, authors, year, doi, url, abstract, summary,
                method, dataset_used, key_metrics, limitations, storage_key
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            RETURNING id, project_slug, title, authors, year, doi, url, summary,
                      method, dataset_used, key_metrics, limitations, storage_key, created_at
            """,
            proj["slug"],
            title,
            authors,
            year,
            doi,
            url,
            abstract,
            summary,
            method,
            dataset_used,
            key_metrics,
            limitations,
            storage_key,
        )
        return dict(row)

    async def update_paper_review(
        self,
        paper_id: int,
        method: str = "",
        dataset_used: str = "",
        key_metrics: str = "",
        limitations: str = "",
    ) -> dict[str, Any] | None:
        pool = self._require_pool()
        row = await pool.fetchrow(
            """
            UPDATE papers
            SET method = CASE WHEN $2 <> '' THEN $2 ELSE method END,
                dataset_used = CASE WHEN $3 <> '' THEN $3 ELSE dataset_used END,
                key_metrics = CASE WHEN $4 <> '' THEN $4 ELSE key_metrics END,
                limitations = CASE WHEN $5 <> '' THEN $5 ELSE limitations END
            WHERE id = $1
            RETURNING id, project_slug, title, authors, year, doi, method, dataset_used, key_metrics, limitations
            """,
            paper_id,
            method,
            dataset_used,
            key_metrics,
            limitations,
        )
        return dict(row) if row else None

    async def list_papers(self, project_slug: str, limit: int = 50) -> list[dict[str, Any]]:
        pool = self._require_pool()
        rows = await pool.fetch(
            """
            SELECT id, project_slug, title, authors, year, doi, url, summary,
                   method, dataset_used, key_metrics, limitations, storage_key, created_at
            FROM papers
            WHERE ($1 = 'all' OR project_slug = $1)
            ORDER BY year DESC NULLS LAST, id DESC
            LIMIT $2
            """,
            project_slug,
            limit,
        )
        return [dict(r) for r in rows]

    async def get_paper(self, paper_id: int) -> dict[str, Any] | None:
        pool = self._require_pool()
        row = await pool.fetchrow(
            """
            SELECT id, project_slug, title, authors, year, doi, url, abstract, summary,
                   method, dataset_used, key_metrics, limitations, storage_key, created_at
            FROM papers
            WHERE id = $1
            """,
            paper_id,
        )
        return dict(row) if row else None

    async def delete_paper(self, paper_id: int) -> bool:
        pool = self._require_pool()
        res = await pool.execute("DELETE FROM papers WHERE id = $1", paper_id)
        return res.endswith("1")

    # ------------------------------------------------------------------
    # Dynamic Multi-LLM Providers
    # ------------------------------------------------------------------

    async def upsert_llm_provider(
        self,
        name: str,
        base_url: str,
        default_model: str,
        api_key_env: str,
        embed_model: str = "",
    ) -> dict[str, Any]:
        pool = self._require_pool()
        clean = name.strip().lower()
        row = await pool.fetchrow(
            """
            INSERT INTO llm_providers (name, base_url, default_model, embed_model, api_key_env, enabled)
            VALUES ($1, $2, $3, $4, $5, TRUE)
            ON CONFLICT (name) DO UPDATE
            SET base_url = EXCLUDED.base_url,
                default_model = EXCLUDED.default_model,
                embed_model = EXCLUDED.embed_model,
                api_key_env = EXCLUDED.api_key_env,
                enabled = TRUE
            RETURNING name, base_url, default_model, embed_model, api_key_env, enabled
            """,
            clean,
            base_url.rstrip("/"),
            default_model,
            embed_model,
            api_key_env.strip().upper(),
        )
        return dict(row)

    async def list_llm_providers(self) -> list[dict[str, Any]]:
        pool = self._require_pool()
        rows = await pool.fetch(
            "SELECT name, base_url, default_model, embed_model, api_key_env, enabled FROM llm_providers ORDER BY name"
        )
        return [dict(r) for r in rows]

    async def save_chunks(
        self,
        paper_id: int,
        project_slug: str,
        chunks: list[str],
        embeddings: list[list[float] | None],
    ) -> int:
        pool = self._require_pool()
        records = [
            (paper_id, project_slug, idx, text, _vec_literal(emb))
            for idx, (text, emb) in enumerate(zip(chunks, embeddings))
        ]
        async with pool.acquire() as conn:
            await conn.executemany(
                """
                INSERT INTO chunks (paper_id, project_slug, chunk_index, content, embedding)
                VALUES ($1, $2, $3, $4, $5::vector)
                """,
                records,
            )
        return len(records)

    async def search_chunks(
        self,
        project_slug: str,
        query_text: str,
        query_embedding: list[float] | None = None,
        category: str = "",
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Vector search with optional project ('all' for cross-project) and category filter."""
        pool = self._require_pool()
        clean_proj = (project_slug or "all").strip().lower()
        clean_cat = category.strip().lower()

        if query_embedding:
            vec = _vec_literal(query_embedding)
            rows = await pool.fetch(
                """
                SELECT c.id, c.paper_id, c.project_slug, p.title AS paper_title, p.doi, p.year,
                       c.chunk_index, c.content,
                       1 - (c.embedding <=> $2::vector) AS score
                FROM chunks c
                JOIN papers p ON p.id = c.paper_id
                JOIN projects pr ON pr.slug = c.project_slug
                WHERE ($1 = 'all' OR c.project_slug = $1)
                  AND ($3 = '' OR pr.category = $3)
                  AND c.embedding IS NOT NULL
                ORDER BY c.embedding <=> $2::vector ASC
                LIMIT $4
                """,
                clean_proj,
                vec,
                clean_cat,
                top_k,
            )
            if rows:
                return [dict(r) for r in rows]

        # Graceful keyword fallback if Mac mini embedding service is offline
        pattern = f"%{query_text}%"
        rows = await pool.fetch(
            """
            SELECT c.id, c.paper_id, c.project_slug, p.title AS paper_title, p.doi, p.year,
                   c.chunk_index, c.content, 0.5 AS score
            FROM chunks c
            JOIN papers p ON p.id = c.paper_id
            JOIN projects pr ON pr.slug = c.project_slug
            WHERE ($1 = 'all' OR c.project_slug = $1)
              AND ($3 = '' OR pr.category = $3)
              AND c.content ILIKE $2
            ORDER BY c.id DESC
            LIMIT $4
            """,
            clean_proj,
            pattern,
            clean_cat,
            top_k,
        )
        return [dict(r) for r in rows]

    async def count_papers(self, project_slug: str) -> int:
        pool = self._require_pool()
        val = await pool.fetchval("SELECT COUNT(*) FROM papers WHERE project_slug = $1", project_slug)
        return int(val or 0)

    # ------------------------------------------------------------------
    # Dataset Registry (Kaggle, PC, Mac, Oracle)
    # ------------------------------------------------------------------

    async def upsert_dataset(
        self,
        slug: str,
        project_slug: str,
        name: str,
        location: str = "kaggle",
        kaggle_ref: str = "",
        mount_path: str = "",
        fmt: str = "csv",
        num_samples: int = 0,
        num_classes: int = 0,
        size_mb: float = 0.0,
        description: str = "",
    ) -> dict[str, Any]:
        proj = await self.ensure_project(project_slug)
        pool = self._require_pool()
        clean_slug = slug.strip().lower().replace(" ", "_")
        clean_loc = (location or "kaggle").strip().lower()
        resolved_mount = mount_path
        if not resolved_mount and clean_loc == "kaggle":
            folder = kaggle_ref.partition("/")[2] if "/" in kaggle_ref else clean_slug
            resolved_mount = f"/kaggle/input/{folder}"

        row = await pool.fetchrow(
            """
            INSERT INTO datasets (
                slug, project_slug, name, location, kaggle_ref, mount_path,
                format, num_samples, num_classes, size_mb, description
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            ON CONFLICT (slug) DO UPDATE
            SET project_slug = EXCLUDED.project_slug,
                name = EXCLUDED.name,
                location = EXCLUDED.location,
                kaggle_ref = EXCLUDED.kaggle_ref,
                mount_path = EXCLUDED.mount_path,
                format = EXCLUDED.format,
                num_samples = EXCLUDED.num_samples,
                num_classes = EXCLUDED.num_classes,
                size_mb = EXCLUDED.size_mb,
                description = EXCLUDED.description
            RETURNING id, slug, project_slug, name, location, kaggle_ref, mount_path,
                      format, num_samples, num_classes, size_mb, description, created_at
            """,
            clean_slug,
            proj["slug"],
            name,
            clean_loc,
            kaggle_ref,
            resolved_mount,
            fmt,
            num_samples,
            num_classes,
            size_mb,
            description,
        )
        return dict(row)

    async def get_dataset(self, slug: str) -> dict[str, Any] | None:
        pool = self._require_pool()
        row = await pool.fetchrow(
            """
            SELECT id, slug, project_slug, name, location, kaggle_ref, mount_path,
                   format, num_samples, num_classes, size_mb, description, created_at
            FROM datasets
            WHERE slug = $1
            """,
            slug.strip().lower(),
        )
        return dict(row) if row else None

    async def list_datasets(self, project_slug: str = "", location: str = "") -> list[dict[str, Any]]:
        pool = self._require_pool()
        rows = await pool.fetch(
            """
            SELECT id, slug, project_slug, name, location, kaggle_ref, mount_path,
                   format, num_samples, num_classes, size_mb, description, created_at
            FROM datasets
            WHERE ($1 = '' OR $1 = 'all' OR project_slug = $1)
              AND ($2 = '' OR location = $2)
            ORDER BY created_at DESC
            """,
            project_slug.strip().lower(),
            location.strip().lower(),
        )
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Compute Nodes
    # ------------------------------------------------------------------

    async def upsert_node(
        self,
        name: str,
        kind: str,
        status: str = "online",
        capabilities: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        pool = self._require_pool()
        row = await pool.fetchrow(
            """
            INSERT INTO nodes (name, kind, status, capabilities, last_seen)
            VALUES ($1, $2, $3, $4::jsonb, NOW())
            ON CONFLICT (name) DO UPDATE
            SET kind = EXCLUDED.kind,
                status = EXCLUDED.status,
                capabilities = EXCLUDED.capabilities,
                last_seen = NOW()
            RETURNING name, kind, status, capabilities, last_seen
            """,
            name,
            kind,
            status,
            json.dumps(capabilities or {}),
        )
        item = dict(row)
        item["capabilities"] = _decode_json(item["capabilities"])
        return item

    async def list_nodes(self) -> list[dict[str, Any]]:
        pool = self._require_pool()
        rows = await pool.fetch("SELECT name, kind, status, capabilities, last_seen FROM nodes ORDER BY name")
        now = datetime.now(timezone.utc)
        result = []
        for r in rows:
            item = dict(r)
            item["capabilities"] = _decode_json(item["capabilities"])
            last_seen = item.get("last_seen")
            if isinstance(last_seen, datetime):
                age_sec = (now - last_seen).total_seconds()
                if age_sec > 180:
                    item["status"] = "offline"
            result.append(item)
        return result

    # ------------------------------------------------------------------
    # Experiments & Distributed Job Queue
    # ------------------------------------------------------------------

    async def create_experiment(
        self,
        project_slug: str,
        name: str,
        target_node: str,
        script: str = "",
        config: dict[str, Any] | None = None,
        dataset_slug: str = "",
        kaggle_datasets: list[str] | None = None,
        created_by: str = "ai",
    ) -> dict[str, Any]:
        proj = await self.ensure_project(project_slug)
        pool = self._require_pool()
        exp_id = f"exp-{uuid.uuid4().hex[:8]}"
        row = await pool.fetchrow(
            """
            INSERT INTO experiments (
                id, project_slug, name, target_node, status,
                dataset_slug, kaggle_datasets, script, config, created_by
            )
            VALUES ($1, $2, $3, $4, 'queued', $5, $6, $7, $8::jsonb, $9)
            RETURNING id, project_slug, name, target_node, status, dataset_slug,
                      kaggle_datasets, script, config, metrics, created_by, created_at
            """,
            exp_id,
            proj["slug"],
            name,
            target_node,
            dataset_slug,
            kaggle_datasets or [],
            script,
            json.dumps(config or {}),
            created_by,
        )
        item = dict(row)
        item["config"] = _decode_json(item["config"])
        item["metrics"] = _decode_json(item["metrics"])
        return item

    async def claim_experiment(self, node_name: str) -> dict[str, Any] | None:
        """Atomically claim the oldest queued job assigned to a compute node."""
        pool = self._require_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    """
                    SELECT id, project_slug, name, target_node, dataset_slug, kaggle_datasets, script, config
                    FROM experiments
                    WHERE target_node = $1 AND status = 'queued'
                    ORDER BY created_at ASC
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                    """,
                    node_name,
                )
                if not row:
                    return None
                updated = await conn.fetchrow(
                    """
                    UPDATE experiments
                    SET status = 'running', started_at = NOW()
                    WHERE id = $1
                    RETURNING id, project_slug, name, target_node, status,
                              dataset_slug, kaggle_datasets, script, config, started_at
                    """,
                    row["id"],
                )
                item = dict(updated)
                item["config"] = _decode_json(item["config"])
                return item

    async def get_experiment(self, exp_id: str) -> dict[str, Any] | None:
        pool = self._require_pool()
        row = await pool.fetchrow(
            """
            SELECT id, project_slug, name, target_node, status, dataset_slug, kaggle_datasets,
                   script, config, metrics, logs, artifact_url, created_by,
                   created_at, started_at, finished_at
            FROM experiments
            WHERE id = $1
            """,
            exp_id,
        )
        if not row:
            return None
        item = dict(row)
        item["config"] = _decode_json(item["config"])
        item["metrics"] = _decode_json(item["metrics"])
        return item

    async def complete_experiment(
        self,
        exp_id: str,
        status: str = "completed",
        metrics: dict[str, Any] | None = None,
        logs: str = "",
        artifact_url: str = "",
    ) -> dict[str, Any] | None:
        pool = self._require_pool()
        row = await pool.fetchrow(
            """
            UPDATE experiments
            SET status = $2,
                metrics = $3::jsonb,
                logs = $4,
                artifact_url = $5,
                finished_at = NOW()
            WHERE id = $1
            RETURNING id, project_slug, name, target_node, status, dataset_slug,
                      kaggle_datasets, metrics, artifact_url, finished_at
            """,
            exp_id,
            status,
            json.dumps(metrics or {}),
            logs[-20000:],
            artifact_url,
        )
        if not row:
            return None
        item = dict(row)
        item["metrics"] = _decode_json(item["metrics"])
        return item

    async def list_experiments(self, project_slug: str, limit: int = 20) -> list[dict[str, Any]]:
        pool = self._require_pool()
        rows = await pool.fetch(
            """
            SELECT id, project_slug, name, target_node, status, dataset_slug,
                   kaggle_datasets, config, metrics, artifact_url, created_by,
                   created_at, finished_at
            FROM experiments
            WHERE ($1 = 'all' OR project_slug = $1)
            ORDER BY created_at DESC
            LIMIT $2
            """,
            project_slug,
            limit,
        )
        items = []
        for r in rows:
            item = dict(r)
            item["config"] = _decode_json(item["config"])
            item["metrics"] = _decode_json(item["metrics"])
            items.append(item)
        return items


db = Database()
