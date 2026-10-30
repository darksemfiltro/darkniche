"""Regressões sem rede, sem credenciais reais e sem gastar quota."""
import copy
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "analise-mercado-yt"
sys.path.insert(0, str(SKILL / "scripts"))
sys.path.insert(0, str(SKILL / "extras/colab"))
sys.path.insert(0, str(ROOT))
import common
import yt_api
import scan
import metrics
import build_report
import score
import ytdlp_tools
from plan_tools import signature, raw_is_current, validate_plan


class RegressionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.env = patch.dict(os.environ, {"USERPROFILE": str(self.base), "HOME": str(self.base),
                                           "SystemRoot": os.environ.get("SystemRoot", "C:/Windows")}, clear=True)
        self.env.start()
        self.home = patch.object(common, "HOME", self.base / "home")
        self.quota = patch.object(common, "QUOTA_FILE", self.base / "home" / "quota.json")
        self.cache = patch.object(common, "CACHE_DIR", self.base / "home" / "cache")
        self.cwd = patch.object(Path, "cwd", return_value=self.base)
        for p in (self.home, self.quota, self.cache, self.cwd):
            p.start()
        common.set_run(None)

    def tearDown(self):
        common.set_run(None)
        for p in (self.cwd, self.cache, self.quota, self.home):
            p.stop()
        self.env.stop()
        self.tmp.cleanup()

    def test_environment_alias_beats_dotenv_canonical(self):
        os.environ["YOUTUBE_API_KEY"] = "environment-fake"
        (self.base / ".env").write_text("YT_API_KEY=file-fake\n", encoding="utf-8")
        config, sources = common.env_config()
        self.assertEqual(config["YT_API_KEY"], "environment-fake")
        self.assertEqual(sources["YT_API_KEY"], "ambiente:YOUTUBE_API_KEY")

    def test_empty_environment_bom_quotes_comments_and_run_env(self):
        os.environ["YT_API_KEY"] = ""
        run = self.base / "run"
        run.mkdir()
        (run / ".env").write_text('export YOUTUBE_DATA_API_KEY="run-fake" # comment\nYT_DAILY_BUDGET=20 # budget\n', encoding="utf-8-sig")
        (self.base / ".env").write_text("YT_API_KEY=cwd-fake", encoding="utf-8")
        common.set_run(run)
        self.assertEqual(common.load_env()["YT_API_KEY"], "run-fake")
        self.assertEqual(yt_api.budgets()[0], 20)

    def test_quota_buckets_and_analysis_accounting(self):
        common.set_run(self.base / "run")
        with common.quota_lock():
            common.quota_add(1, search=True)
            common.quota_add(1)
        q = common.quota_used()
        self.assertEqual((q["units"], q["searches"], q["requests"]), (1, 1, 2))
        self.assertEqual(common.read_json(self.base / "run/data/quota.json"), q)
        self.assertIsNone(yt_api.quota_status()["remaining_google"])

    def test_legacy_quota_migration(self):
        q = common.normalize_quota({"units": 304, "searches": 3})
        self.assertEqual(q["units"], 4)
        self.assertTrue(q["migrated_estimate"])
        self.assertEqual(common.normalize_quota(q), q)

    def test_quota_lock_across_processes(self):
        # Usa o mesmo diretório para simular agentes paralelos; nenhum HTTP é enviado.
        task_env = {**os.environ, "AMY_HOME": str(self.base / "parallel"), "PYTHONPATH": str(SKILL / "scripts")}
        code = "import common;\nfor i in range(15):\n with common.quota_lock(): common.quota_add(1)"
        processes = [subprocess.Popen([sys.executable, "-c", code], env=task_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(4)]
        results = [(p.communicate(timeout=30), p.returncode) for p in processes]
        for ((_, err), code) in results:
            self.assertEqual(code, 0, err.decode())
        q = common.read_json(self.base / "parallel/quota.json")[common.pacific_day()]
        self.assertEqual(q["units"], 60)

    def test_cache_hit_free_and_key_not_in_request_url(self):
        os.environ["YOUTUBE_API_KEY"] = "fake-private-key"
        response = io.BytesIO(b'{"items": []}')
        with patch.object(yt_api.urllib.request, "urlopen", return_value=response) as call:
            yt_api.api("channels", part="id", id="UCtest")
            yt_api.api("channels", part="id", id="UCtest")
        self.assertEqual(call.call_count, 1)
        req = call.call_args.args[0]
        self.assertNotIn("fake-private-key", req.full_url)
        self.assertEqual(common.quota_used()["units"], 1)

    def test_retries_count_and_search_budget_stops_before_http(self):
        os.environ.update(YT_API_KEY="fake", YT_SEARCH_DAILY_BUDGET="1")
        failure = urllib.error.HTTPError("url", 503, "busy", {}, io.BytesIO(b"busy"))
        with patch.object(yt_api.urllib.request, "urlopen", side_effect=failure) as call, patch.object(yt_api.time, "sleep"):
            with self.assertRaises(yt_api.QuotaExceeded):
                yt_api.api("search", part="id", q="x")
        failure.close()
        self.assertEqual(call.call_count, 1)
        self.assertEqual(common.quota_used()["searches"], 1)

    def test_comments_does_not_swallow_quota_or_network_errors(self):
        for failure in (yt_api.QuotaExceeded("quota"), RuntimeError("network")):
            with patch.object(yt_api, "api", side_effect=failure):
                with self.assertRaises(type(failure)):
                    yt_api.comments("abcdefghijk")

    def plan(self):
        return {"defaults": {"pages": 1}, "languages": [{"lang": "pt", "region": "BR"}],
                "cells": [{"id": "aviacao", "mode": "api", "queries": {"pt": ["aviacao"]}}]}

    def test_resume_invalidates_query_filters_region_and_mode(self):
        plan = self.plan()
        job = scan.jobs(plan, self.base, "api", None, None)[0]
        cell, lang, q, mode, path = job
        saved = {"cell": cell["id"], "lang": lang, "query": q, "mode": mode,
                 "signature": signature(q, lang, "BR", {"pages": 1}, mode), "rows": []}
        common.write_json(path, saved)
        self.assertEqual(scan.jobs(plan, self.base, "api", None, None), [])
        for kind in ("query", "filter", "region"):
            changed = copy.deepcopy(plan)
            if kind == "query": changed["cells"][0]["queries"]["pt"] = ["outro"]
            if kind == "filter": changed["defaults"]["duration"] = "longform"
            if kind == "region": changed["languages"][0]["region"] = "PT"
            self.assertEqual(len(scan.jobs(changed, self.base, "api", None, None)), 1)
            self.assertFalse(raw_is_current(saved, changed))
        jobs = scan.jobs(plan, self.base, "ytdlp", None, None, force_mode=True)
        self.assertEqual(jobs[0][3], "ytdlp")

    def test_keywords_change_does_not_spend_again(self):
        plan = self.plan()
        saved = {"cell": "aviacao", "lang": "pt", "query": "aviacao", "mode": "api",
                 "signature": signature("aviacao", "pt", "BR", {"pages": 1}, "api")}
        plan["cells"][0]["keywords"] = ["acidente"]
        self.assertTrue(raw_is_current(saved, plan))

    def test_estimates_longform_pages_and_enrichment(self):
        job = ({"filters": {"duration": "longform", "pages": 2}}, "pt", "x", "api", None)
        self.assertEqual(scan.cost_of(job, {}), {"searches": 4, "units": 8, "requests": 12})
        job = ({"filters": {"ytdlp_n": 101}}, "pt", "x", "ytdlp", None)
        with patch.object(scan, "load_env", return_value={"YT_API_KEY": "fake"}):
            self.assertEqual(scan.cost_of(job, {})["units"], 6)
            job[0]["filters"]["enrich"] = False
            self.assertEqual(scan.cost_of(job, {})["units"], 0)

    def test_two_year_ytdlp_does_not_use_one_year_filter(self):
        with patch.object(scan.ytdlp_tools, "YTDLP", ["fake"]), patch.object(scan.ytdlp_tools, "search", return_value=[]) as call:
            scan.run_query("x", "pt", "BR", {"after_days": 730, "enrich": False}, "ytdlp")
        self.assertEqual(call.call_args.args[3], "any")

    def test_plan_rejects_path_traversal_before_collection(self):
        plan = self.plan()
        plan["cells"][0]["id"] = "../../outside"
        with self.assertRaises(ValueError): validate_plan(plan)

    def test_unknown_language_does_not_become_native(self):
        row = {"id": "abcdefghijk", "title": "12345", "dur": 600, "views": 100000}
        m = metrics.cell_metrics([row], "pt", 480, 540)
        self.assertEqual((m["n_native"], m["n_long"], m["n_unknown_lang"]), (0, 0, 1))

    def test_transcript_keeps_incremental_words(self):
        text = ytdlp_tools._vtt_to_text("WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nhello\n\n00:00:02.000 --> 00:00:03.000\nhello world\n")
        self.assertIn("world", text)

    def valid_op(self):
        return {"id": "test", "scores": {k: {"v": 5 if k != "R" else 1, "why": "evidence", "measured": True} for k in "DLFGAKSMVR"}}

    def test_score_rejects_strings_booleans_missing_axes_and_bad_weights(self):
        for v in ("5", True, float("nan"), 6):
            op = self.valid_op(); op["scores"]["D"]["v"] = v
            with self.assertRaises(ValueError): score.compute(op)
        op = self.valid_op(); del op["scores"]["K"]
        with self.assertRaises(ValueError): score.compute(op)
        with self.assertRaises(ValueError): score.compute(self.valid_op(), {"O": 1})

    def test_high_risk_or_missing_format_not_blue_ocean(self):
        op = self.valid_op(); op["scores"]["R"]["v"] = 5
        self.assertEqual(score.compute(op)["tier"], "C")
        self.assertFalse(score.compute(op)["blue_ocean"])
        op = self.valid_op(); op["scores"]["G"]["v"] = 1
        self.assertFalse(score.compute(op)["blue_ocean"])

    def test_embed_images_and_never_borrow_other_analysis_quota(self):
        from PIL import Image
        image = self.base / "image.png"; Image.new("RGB", (12, 12), "red").save(image)
        common.write_json(self.base / "plan.json", {"title": "test"})
        common.write_json(self.base / "analysis.json", {"format_gap": [{"cell": "x", "lang": "pt", "sheet_src": "image.png"}]})
        with common.quota_lock(): common.quota_add(20)
        data = build_report.assemble(self.base, embed=True)
        self.assertTrue(data["format_gap"][0]["sheet_src"].startswith("data:image/jpeg;base64,"))
        self.assertEqual(data["meta"]["quota"]["units"], 0)
        self.assertIsNone(build_report.img_src(self.base, "../outside.png", True, 100))

    def test_report_payload_cannot_close_script_tag(self):
        html = build_report.render({"meta": {"title": "test"}, "summary": {"lead": "</script><script>alert(1)</script>"}}, True)
        self.assertNotIn("</script><script>alert(1)", html)

    def test_reference_accepts_null_gallery(self):
        common.write_json(self.base / "data/reference.json", {"gallery": None})
        self.assertIsNone(build_report.assemble(self.base)["reference"]["gallery"])

    def test_report_text_can_contain_template_marker(self):
        html = build_report.render({"meta": {"title": "test"}, "summary": {"lead": "/*__APP__*/"}}, True)
        self.assertIn('"lead":"/*__APP__*/"', html)


if __name__ == "__main__":
    unittest.main()
