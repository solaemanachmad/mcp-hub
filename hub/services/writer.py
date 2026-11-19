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


def check_latex(tex_source: str) -> dict[str, Any]:
    """Lint LaTeX source for unmatched environments, braces, and common table issues."""
    issues: list[str] = []
    begins = re.findall(r"\\begin\{([^}]+)\}", tex_source)
    ends = re.findall(r"\\end\{([^}]+)\}", tex_source)

    if len(begins) != len(ends):
        issues.append(f"Mismatched environment count: {len(begins)} \\begin vs {len(ends)} \\end.")

    stack: list[str] = []
    for match in re.finditer(r"\\(begin|end)\{([^}]+)\}", tex_source):
        kind, env = match.group(1), match.group(2)
        if kind == "begin":
            stack.append(env)
        else:
            if not stack or stack[-1] != env:
                issues.append(f"Unexpected \\end{{{env}}} (open stack: {stack}).")
            else:
                stack.pop()
    if stack:
        issues.append(f"Unclosed environments: {stack}.")

    open_braces = tex_source.count("{") - tex_source.count(r"\{")
    close_braces = tex_source.count("}") - tex_source.count(r"\}")
    if open_braces != close_braces:
        issues.append(f"Unbalanced curly braces: {open_braces} '{{' vs {close_braces} '}}'.")

    return {
        "valid": len(issues) == 0,
        "issue_count": len(issues),
        "issues": issues,
    }


async def build_latex_manuscript(
    project: str,
    template: str = "ieee",
    title: str = "",
    authors: str = "Author Name",
    database: Database | None = None,
) -> dict[str, Any]:
    """Generate a complete, ready-to-compile LaTeX paper skeleton (IEEE, Springer, Elsevier) with tables & BibTeX."""
    repo = database or default_db
    proj = await repo.ensure_project(project)
    matrix = await build_paper_matrix(proj["slug"], fmt="latex", database=repo)
    exp_tbl = await build_exp_table(proj["slug"], fmt="latex", database=repo)
    bib = await export_bibtex(proj["slug"], database=repo)

    tpl = template.strip().lower()
    if tpl == "springer":
        doc_class = r"\documentclass[runningheads]{llncs}"
    elif tpl == "elsevier":
        doc_class = r"\documentclass[preprint,12pt]{elsarticle}"
    else:
        doc_class = r"\documentclass[conference]{IEEEtran}"

    paper_title = _escape_latex(title or proj["name"])
    tex = "\n".join(
        [
            doc_class,
            r"\usepackage{booktabs}",
            r"\usepackage{graphicx}",
            r"\usepackage{amsmath,amssymb}",
            r"\usepackage{hyperref}",
            "",
            f"\\title{{{paper_title}}}",
            f"\\author{{{_escape_latex(authors)}}}",
            "",
            r"\begin{document}",
            r"\maketitle",
            "",
            r"\begin{abstract}",
            _escape_latex(proj.get("description") or "Abstract placeholder."),
            r"\end{abstract}",
            "",
            r"\section{Introduction}",
            "Introduction and research motivation.",
            "",
            r"\section{Related Work}",
            matrix["table"],
            "",
            r"\section{Proposed Methodology}",
            "Architecture and mathematical formulation.",
            "",
            r"\section{Experimental Setup and Results}",
            exp_tbl["table"],
            "",
            r"\section{Conclusion}",
            "Summary of findings and future work.",
            "",
            r"\bibliographystyle{IEEEtran}",
            r"\bibliography{references}",
            r"\end{document}",
        ]
    )

    return {
        "project": proj["slug"],
        "template": tpl,
        "tex": tex,
        "bibtex": bib["bibtex"],
        "lint": check_latex(tex),
    }
