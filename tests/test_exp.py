"""Tests for Experiment Orchestrator auto-routing, Kaggle dataset routing, and ranking."""

import asyncio
import unittest

from hub.services.exp import compare_experiments, route_node


class FakeDB:
    async def list_experiments(self, project_slug: str, limit: int = 20):
        return [
            {"id": "exp-1", "name": "cnn", "target_node": "kaggle", "dataset_slug": "gazecom", "status": "completed", "metrics": {"f1": 0.88}},
            {"id": "exp-2", "name": "timesnet", "target_node": "kaggle", "dataset_slug": "gazecom", "status": "completed", "metrics": {"f1": 0.93}},
            {"id": "exp-3", "name": "baseline", "target_node": "pc", "dataset_slug": "", "status": "completed", "metrics": {}},
        ]


class TestExp(unittest.TestCase):
    def test_route_node_explicit(self):
        self.assertEqual(route_node("pc"), "pc")
        self.assertEqual(route_node("kaggle"), "kaggle")

    def test_route_node_auto_and_kaggle_dataset(self):
        self.assertEqual(route_node("auto", {}, dataset_location="kaggle"), "kaggle")
        self.assertEqual(route_node("auto", {"gpu": True}), "kaggle")
        self.assertEqual(route_node("auto", {"epochs": 30}), "kaggle")
        self.assertEqual(route_node("auto", {"epochs": 5}), "pc")

    def test_compare_experiments_ranks_descending(self):
        res = asyncio.run(compare_experiments("eye_movement", metric="f1", database=FakeDB()))
        self.assertEqual(res["count"], 3)
        self.assertEqual(res["experiments"][0]["id"], "exp-2")
        self.assertEqual(res["experiments"][1]["id"], "exp-1")
        self.assertEqual(res["experiments"][2]["id"], "exp-3")


if __name__ == "__main__":
    unittest.main()
