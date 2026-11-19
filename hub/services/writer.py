"""Academic Writer tools: BibTeX export, Literature Review Matrix, and LaTeX/Markdown tables."""

from __future__ import annotations

import re
from typing import Any

from hub.db import Database, db as default_db


def _cite_key(authors: str, year: int | None, title: str, fallback_id: int) -> str:
    first_author = re.sub(r"[^a-zA-Z]", "", (authors.split(",")[0] if authors else "paper")).lower()
    first_word = re.sub(r"[^a-zA-Z]", "", (title.split()[0] if title else "work")).lower()
    yr = str(year) if year else "nd"
    return f"{first_author or 'author'}{yr}{first_word or fallback_id}"


def _escape_latex(text: Any) -> str:
    s = str(text if text is not None else "-")
    for ch, repl in (("&", r"\&"), ("%", r"\%"), ("_", r"\_"), ("#", r"\#")):
        s = s.replace(ch, repl)
    return s


async def export_bibtex(project: str, database: Database | None = None) -> dict[str, Any]:
    """Generate standard BibTeX entries for all papers in a project."""
    repo = database or default_db
    papers = await repo.list_papers(project, limit=200)
    entries: list[str] = []
    for p in papers:
        key = _cite_key(p.get("authors", ""), p.get("year"), p.get("title", ""), p["id"])
        lines = [f"@article{{{key},"]
        lines.append(f"  title = {{{p.get('title', '')}}},")
        if p.get("authors"):
            bib_authors = " and ".join(a.strip() for a in p["authors"].split(",") if a.strip())
            lines.append(f"  author = {{{bib_authors}}},")
        if p.get("year"):
            lines.append(f"  year = {{{p['year']}}},")
        if p.get("doi"):
            lines.append(f"  doi = {{{p['doi']}}},")
        if p.get("url"):
            lines.append(f"  url = {{{p['url']}}},")
        lines.append("}")
        entries.append("\n".join(lines))

    return {
        "project": project,
        "count": len(entries),
        "bibtex": "\n\n".join(entries),
    }


async def build_paper_matrix(
    project: str,
    fmt: str = "markdown",
    database: Database | None = None,
) -> dict[str, Any]:
    """Build a structured Literature Review Matrix comparing methods, datasets, metrics, and gaps."""
    repo = database or default_db
    papers = await repo.list_papers(project, limit=100)

    if fmt.lower() == "latex":
        rows = [
            r"\begin{table*}[htbp]",
            r"\centering",
            r"\caption{Literature Review Comparison Matrix}",
            r"\begin{tabular}{p{3.5cm}p{3cm}p{2.5cm}p{3cm}p{4cm}}",
            r"\toprule",
            r"Paper & Method & Dataset & Key Metrics & Limitations / Research Gap \\",
            r"\midrule",
        ]
        for p in papers:
            ref = f"{p.get('title', '')[:45]} ({p.get('year') or 'n.d.'})"
            rows.append(
                f"{_escape_latex(ref)} & "
                f"{_escape_latex(p.get('method') or '-')} & "
                f"{_escape_latex(p.get('dataset_used') or '-')} & "
                f"{_escape_latex(p.get('key_metrics') or '-')} & "
                f"{_escape_latex(p.get('limitations') or (p.get('summary') or '-')[:120])} \\\\"
            )
        rows.extend([r"\bottomrule", r"\end{tabular}", r"\end{table*}"])
        table = "\n".join(rows)
    else:
        rows = [
            "| ID | Paper (Year) | Method | Dataset | Key Metrics | Limitations / Gap |",
            "|---|---|---|---|---|---|",
        ]
        for p in papers:
            ref = f"{p.get('title', '')[:55]} ({p.get('year') or 'n.d.'})"
            gap = p.get("limitations") or (p.get("summary") or "-")[:120]
            rows.append(
                f"| {p['id']} | {ref} | {p.get('method') or '-'} | "
                f"{p.get('dataset_used') or '-'} | {p.get('key_metrics') or '-'} | "
                f"{gap.replace(chr(10), ' ')} |"
            )
        table = "\n".join(rows)

    return {
        "project": project,
        "count": len(papers),
        "format": fmt,
        "table": table,
    }


async def build_exp_table(
    project: str,
    metrics: list[str] | None = None,
    fmt: str = "latex",
    caption: str = "Experimental Results Comparison",
    database: Database | None = None,
) -> dict[str, Any]:
    """Generate a publication-ready LaTeX or Markdown table from project experiments."""
    repo = database or default_db
    exps = await repo.list_experiments(project, limit=50)
    cols = metrics or ["accuracy", "f1", "precision", "recall", "loss"]

    if fmt.lower() == "latex":
        col_spec = "lll" + ("c" * len(cols))
        header_metrics = " & ".join(_escape_latex(m.upper()) for m in cols)
        lines = [
            r"\begin{table}[htbp]",
            r"\centering",
            f"\\caption{{{_escape_latex(caption)}}}",
            f"\\begin{{tabular}}{{{col_spec}}}",
            r"\toprule",
            f"Model / Experiment & Dataset & Node & {header_metrics} \\\\",
            r"\midrule",
        ]
        for e in exps:
            m_dict = e.get("metrics") or {}
            vals = []
            for c in cols:
                v = m_dict.get(c)
                vals.append(f"{float(v):.4f}" if isinstance(v, (int, float)) else _escape_latex(v or "-"))
            lines.append(
                f"{_escape_latex(e['name'])} & "
                f"{_escape_latex(e.get('dataset_slug') or '-')} & "
                f"{_escape_latex(e['target_node'])} & "
                f"{' & '.join(vals)} \\\\"
            )
        lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}"])
        table = "\n".join(lines)
    else:
        header = "| Experiment | Dataset | Node | Status | " + " | ".join(m.upper() for m in cols) + " |"
        sep = "|---|---|---|---|" + "|".join("---" for _ in cols) + "|"
        lines = [header, sep]
        for e in exps:
            m_dict = e.get("metrics") or {}
            vals = [
                f"{float(m_dict[c]):.4f}" if isinstance(m_dict.get(c), (int, float)) else str(m_dict.get(c, "-"))
                for c in cols
            ]
            lines.append(
                f"| {e['name']} (`{e['id']}`) | {e.get('dataset_slug') or '-'} | "
                f"{e['target_node']} | {e['status']} | {' | '.join(vals)} |"
            )
        table = "\n".join(lines)

    return {
        "project": project,
        "count": len(exps),
        "format": fmt,
        "metrics": cols,
        "table": table,
    }
