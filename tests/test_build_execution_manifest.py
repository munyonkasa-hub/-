"""Production-route checks for approved visual handoffs."""

import csv
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / ".codex/agents/build_execution_manifest.py"
spec = importlib.util.spec_from_file_location("build_execution_manifest", SCRIPT)
manifest_builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manifest_builder)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class RouteHandoffTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "source.png").write_bytes(b"source image placeholder")

    def prepare(self, route="SOURCE_CROP_LAYOUT", photo="", schema=1):
        page = (
            "# P7｜真实细节四宫格\n"
            "## 执行方式\n"
            f"制作路线：{route}\n"
            "只裁切原图四处真实部位，禁止 AI 生成商品细节。\n"
            "### 摄影底图指令\n"
            f"{photo}\n"
            "### 日文全文\n"
            "真实细节\n"
            "### 版式执行指令\n"
            "原图四格，独立排版\n"
        )
        (self.root / "script.md").write_text(page, encoding="utf-8")
        with (self.root / "list.csv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=[
                "页码", "SKU", "方式", "摄影底图指令", "日文全文", "版式执行指令"
            ])
            writer.writeheader()
            writer.writerow({"页码": "P7", "SKU": "白色", "方式": route,
                             "摄影底图指令": photo, "日文全文": "真实细节",
                             "版式执行指令": "原图四格，独立排版"})
        approval = {"sha256": sha(self.root / "script.md"),
                    "approved_list_sha256": sha(self.root / "list.csv")}
        if schema is not None:
            approval["route_schema"] = schema
        (self.root / "approval.json").write_text(json.dumps(approval), encoding="utf-8")
        (self.root / "execution-pages.json").write_text(json.dumps({
            "P7": {"basis": "test", "owner": "producer", "assets": ["source.png"],
                   "adoption": "pending"}
        }), encoding="utf-8")

    def build(self):
        return manifest_builder.build(self.root, "script.md", "list.csv")

    def test_static_crop_route_keeps_photo_input_empty(self):
        self.prepare()
        page = json.loads(self.build().read_text())["pages"][0]
        self.assertEqual(page["execution_route"], "SOURCE_CROP_LAYOUT")
        self.assertTrue(page["route_verified"])
        self.assertIsNone(page["photo_input"])

    def test_generation_route_without_photo_is_rejected(self):
        self.prepare(route="PHOTO_GENERATION")
        with self.assertRaisesRegex(ValueError, "photo input conflicts"):
            self.build()

    def test_crop_route_with_generation_input_is_rejected(self):
        self.prepare(photo="Photograph a newly rendered product.")
        with self.assertRaisesRegex(ValueError, "photo input conflicts"):
            self.build()

    def test_route_must_match_approved_page(self):
        self.prepare()
        listing = self.root / "list.csv"
        content = listing.read_text(encoding="utf-8").replace(
            "SOURCE_CROP_LAYOUT", "STATIC_LAYOUT"
        )
        listing.write_text(content, encoding="utf-8")
        approval = self.root / "approval.json"
        decision = json.loads(approval.read_text(encoding="utf-8"))
        decision["approved_list_sha256"] = sha(listing)
        approval.write_text(json.dumps(decision), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "route differs"):
            self.build()

    def test_older_approval_stays_readable_but_unverified(self):
        self.prepare(route="PHOTO_GENERATION", schema=None)
        page = json.loads(self.build().read_text())["pages"][0]
        self.assertFalse(page["route_verified"])
        self.assertIsNone(page["execution_route"])


if __name__ == "__main__":
    unittest.main()
