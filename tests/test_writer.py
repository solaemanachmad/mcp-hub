"""Tests for LaTeX linter, BibTeX export, and manuscript generator."""

import asyncio
import unittest

from hub.services.writer import build_latex_manuscript, check_latex


class FakeWriterDB:
    async def ensure_project(self, slug: str, **_kwargs):
        return {"slug": slug, "name": "Eye Movement Study", "description": "Deep learning gaze classification."}

    async def list_papers(self, project_slug: str, limit: int = 100):
        return [
            {
                "id": 1,
                "title": "CNN Attention for Gaze",
                "authors": "Doe, Jane",
                "year": 2025,
                "doi": "10.1000/test",
                "url": "https://doi.org/10.1000/test",
                "method": "1D-CNN + MHA",
                "dataset_used": "GazeCom",
                "key_metrics": "F1=0.91",
                "limitations": "Small cohort",
            }
        ]

    async def list_experiments(self, project_slug: str, limit: int = 50):
        return [
            {
                "id": "exp-01",
                "name": "TimesNet",
                "dataset_slug": "gazecom",
                "target_node": "kaggle",
                "status": "completed",
                "metrics": {"accuracy": 0.93, "f1": 0.92},
            }
        ]


class TestWriter(unittest.TestCase):
    def test_check_latex_valid_and_invalid(self):
        ok = check_latex(r"\begin{table}\begin{tabular}{cc}a & b\end{tabular}\end{table}")
        self.assertTrue(ok["valid"])

        bad = check_latex(r"\begin{table}\begin{tabular}{cc}a & b\end{table}")
        self.assertFalse(bad["valid"])
        self.assertGreater(bad["issue_count"], 0)

    def test_build_latex_manuscript(self):
        res = asyncio.run(build_latex_manuscript("eye_movement", template="ieee", database=FakeWriterDB()))
        self.assertIn(r"\documentclass[conference]{IEEEtran}", res["tex"])
        self.assertIn("GazeCom", res["tex"])
        self.assertIn("@article{", res["bibtex"])
        self.assertTrue(res["lint"]["valid"])


if __name__ == "__main__":
    unittest.main()
