"""Fluxo com dados fictícios: piloto → proposta → seleção → retomada, sem rede."""
import copy
import io
import json
import os
import sys
import tempfile
import unittest
import zipfile
import types
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "analise-mercado-yt"
sys.path.insert(0, str(SKILL / "scripts"))
sys.path.insert(0, str(SKILL / "extras/colab"))
sys.path.insert(0, str(ROOT))
import common
import metrics
import scan
import selection
import triage
import package_colab
import build_report
from colab_support import export_run
from plan_tools import cell_filters, region_for, signature


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.run = Path(self.temp.name) / "run"
        self.plan = {
            "title": "Teste", "reference": None, "defaults": {"mode": "api", "probe_mode": "api", "duration": "longform", "pages": 1},
            "languages": [{"lang": l, "region": r} for l, r in [("pt", "BR"), ("es", "MX"), ("en", "US")]],
            "cells": [{"id": c, "label": c, "queries": {l: [f"{c} primeira", f"{c} segunda"] for l in ("pt", "es", "en")}} for c in ("a", "b", "c")],
            "probes": [{"id": "pauta", "queries": {l: "título específico" for l in ("pt", "es", "en")}}], "competitors": []}
        common.write_json(self.run / "plan.json", self.plan)

    def tearDown(self):
        common.set_run(None)
        self.temp.cleanup()

    def pilot(self):
        triage.prepare(self.run)
        pilot = self.run / "triage"
        plan = common.read_json(pilot / "plan.json")
        for cell, lang, query, mode, path in scan.jobs(plan, pilot, "api", None, None):
            rows = [{"id": f"video{i:06}", "title": f"{query} história explicada", "views": 50000 + i, "dur": 800,
                     "lang": lang, "published": "2026-09-01T00:00:00Z", "channel_id": "UCteste", "channel": "Dedicado", "subs": 5000} for i in range(6)]
            sig = signature(query, lang, region_for(plan, lang), cell_filters(plan.get("defaults", {}), cell, lang), mode)
            common.write_json(path, {"cell": cell["id"], "lang": lang, "query": query, "mode": mode, "signature": sig, "rows": rows})
        with patch.object(sys, "argv", ["metrics.py", "--run", str(pilot)]), redirect_stdout(io.StringIO()):
            metrics.main()

    def test_pilot_cost_and_separate_gate(self):
        cost = triage.prepare(self.run)
        self.assertEqual(cost["searches"], 18)
        self.assertEqual(cost["units"], 36)
        plan = common.read_json(self.run / "triage/plan.json")
        selection.require_selection(self.run / "triage", plan, triage=True)
        with self.assertRaises(ValueError):
            selection.require_selection(self.run / "triage", plan)
        with self.assertRaises(ValueError):
            selection.require_selection(self.run, self.plan)

    def test_rank_requires_real_collection_artifacts(self):
        with self.assertRaises(ValueError):
            selection.propose(self.run)
        with self.assertRaises(ValueError):
            selection.select(self.run, ["a"], ["pt"])
        triage.prepare(self.run)
        common.write_json(self.run / "triage/data/cells.json", [{"id": "a"}])
        with self.assertRaisesRegex(ValueError, "incompleta"):
            selection.propose(self.run)

    def test_pilot_budget_and_estimate_do_not_mutate(self):
        with self.assertRaises(ValueError):
            triage.prepare(self.run, budget=10)
        with self.assertRaises(ValueError):
            triage.prepare(self.run, budget=100)
        self.assertFalse((self.run / "triage").exists())
        cost = triage.prepare(self.run, estimate=True)
        self.assertEqual(cost["searches"], 18)
        self.assertFalse((self.run / "triage").exists())

    def test_select_subset_reuses_pilot_and_omits_unselected_probes(self):
        self.pilot()
        with redirect_stdout(io.StringIO()):
            selection.propose(self.run)
        state = selection.select(self.run, ["a", "b"], ["pt", "es", "en"])
        plan = common.read_json(self.run / "plan.json")
        self.assertEqual(len(plan["cells"]), 2)
        self.assertEqual(plan["probes"], [])
        self.assertEqual(state["scan_estimate"]["searches"], 24)
        todo = scan.jobs(plan, self.run, "api", None, None)
        self.assertEqual(scan.estimate_cost(todo, plan["defaults"])["searches"], 12)
        self.assertEqual(len(common.read_json(self.run / "proposal.json")["cells"]), 3)
        selection.require_selection(self.run, plan)

    def test_dry_run_budget_and_invalid_selection_preserve_plan(self):
        self.pilot()
        before = (self.run / "plan.json").read_bytes()
        selection.select(self.run, ["a"], ["pt"], dry_run=True)
        self.assertEqual(before, (self.run / "plan.json").read_bytes())
        self.assertFalse((self.run / "selection.json").exists())
        for cells, langs in [([], ["pt"]), (["unknown"], ["pt"]), (["a"], ["fr"])]:
            with self.assertRaises(ValueError):
                selection.select(self.run, cells, langs)
        with self.assertRaises(ValueError):
            selection.select(self.run, ["a"], ["pt"], search_budget=1)
        self.assertEqual(before, (self.run / "plan.json").read_bytes())

    def test_scope_changes_invalidate_but_local_filters_do_not(self):
        self.pilot()
        selection.select(self.run, ["a"], ["pt"], ["pauta"])
        plan = common.read_json(self.run / "plan.json")
        plan["cells"][0]["keywords"] = {"pt": ["avião"]}
        selection.require_selection(self.run, plan)
        with self.assertRaises(ValueError):
            selection.require_selection(self.run, plan, mode="ytdlp")
        for mutate in (lambda p: p["defaults"].update(pages=2),
                       lambda p: p["languages"][0].update(region="PT"),
                       lambda p: p["cells"][0]["queries"]["pt"].append("nova consulta")):
            changed = copy.deepcopy(plan)
            mutate(changed)
            with self.assertRaises(ValueError):
                selection.require_selection(self.run, changed)

    def test_scan_without_selection_exits_before_network(self):
        with patch.object(sys, "argv", ["scan.py", "--run", str(self.run)]), patch.object(scan.yt_api, "search") as network, redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                scan.main()
            self.assertEqual(raised.exception.code, 4)
            network.assert_not_called()

    def test_export_excludes_credentials_and_keeps_pilot(self):
        common.write_json(self.run / "triage/data/cells.json", [])
        (self.run / ".env").write_text("private-value", encoding="utf-8")
        (self.run / "data").mkdir(exist_ok=True)
        (self.run / "data/.env").write_text("private-value", encoding="utf-8")
        common.write_json(self.run / "perfil.json", {"private": True})
        output = export_run(self.run, Path(self.temp.name) / "evidence.zip")
        with zipfile.ZipFile(output) as z:
            names = z.namelist()
            self.assertIn("triage/data/cells.json", names)
            self.assertNotIn("perfil.json", names)
            self.assertFalse(any(".env" in name for name in names))
        # Chave fictícia construída em tempo de execução, nunca uma credencial real.
        common.write_json(self.run / "analysis.json", {"oops": "AIza" + "x" * 35})
        with self.assertRaises(ValueError):
            export_run(self.run, output)

    def test_notebook_cells_compile_and_package_has_no_state(self):
        notebook = json.loads((SKILL / "extras/colab/DarkNiche.ipynb").read_text(encoding="utf-8"))
        for cell in notebook["cells"]:
            if cell["cell_type"] == "code":
                compile("".join(cell["source"]), cell["id"], "exec")
                self.assertEqual(cell["outputs"], [])
        output = package_colab.package(Path(self.temp.name) / "bundle.zip")
        with zipfile.ZipFile(output) as z:
            self.assertIn("analise-mercado-yt/extras/colab/DarkNiche.ipynb", z.namelist())
            self.assertEqual(z.read("analise-mercado-yt/SKILL.md"), (SKILL / "SKILL.md").read_bytes())
            self.assertFalse(any(".env" in name or "audit-output" in name or "__pycache__" in name for name in z.namelist()))

    def test_notebook_upload_extracts_bundle_and_rejects_traversal(self):
        notebook = json.loads((SKILL / "extras/colab/DarkNiche.ipynb").read_text(encoding="utf-8"))
        first = next(c for c in notebook["cells"] if c["cell_type"] == "code")
        bundle = package_colab.package(Path(self.temp.name) / "bundle.zip").read_bytes()
        google = types.ModuleType("google")
        colab = types.ModuleType("google.colab")
        colab.files = types.SimpleNamespace(upload=lambda: {"bundle.zip": bundle})
        google.colab = colab
        target = (Path(self.temp.name) / "extracted").as_posix()
        source = "".join(first["source"]).replace("/content/DarkNiche", target)
        with patch.dict(sys.modules, {"google": google, "google.colab": colab}), redirect_stdout(io.StringIO()):
            exec(compile(source, "upload-cell", "exec"), {})
            self.assertTrue((Path(target) / "analise-mercado-yt/SKILL.md").exists())
            bad = io.BytesIO()
            with zipfile.ZipFile(bad, "w") as archive:
                archive.writestr("../escape.txt", "bad")
            colab.files.upload = lambda: {"bad.zip": bad.getvalue()}
            with self.assertRaises(ValueError):
                exec(compile(source, "upload-cell", "exec"), {})
            self.assertFalse((Path(self.temp.name) / "escape.txt").exists())

    def test_report_counts_pilot_and_deepening_once(self):
        common.write_json(self.run / "analysis.json", {"quota": {"schema": 2, "units": 999, "searches": 999, "requests": 999}})
        common.write_json(self.run / "data/quota.json", {"schema": 2, "units": 8, "searches": 4, "requests": 12})
        common.write_json(self.run / "triage/data/quota.json", {"schema": 2, "units": 6, "searches": 3, "requests": 9})
        data = build_report.assemble(self.run)
        self.assertEqual(data["meta"]["quota"]["searches"], 7)
        self.assertEqual(data["meta"]["quota"]["units"], 14)
        self.assertEqual(data["meta"]["quota"]["requests"], 21)


if __name__ == "__main__":
    unittest.main()
