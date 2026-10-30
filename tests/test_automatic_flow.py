"""Automação sem APIs reais: modelo, rede e CLI controlados; métricas e HTML reais."""
import contextlib
import copy
import importlib
import io
import json
import os
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
import common
import notebook_flow as flow
import selection
from text_ai import TextAI, AIError


class AutomaticTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.run = Path(self.tmp.name) / "run"
        self.state = patch.multiple(common, HOME=Path(self.tmp.name)/"state", QUOTA_FILE=Path(self.tmp.name)/"state/quota.json", CACHE_DIR=Path(self.tmp.name)/"state/cache")
        self.state.start()

    def tearDown(self):
        common.set_run(None)
        self.state.stop()
        self.tmp.cleanup()

    def test_json_repairs_once_then_caches(self):
        ai = TextAI(self.run, backend="gemini")
        validate = lambda value: None if value.get("ok") else (_ for _ in ()).throw(ValueError("missing ok"))
        with patch.object(ai, "_generate", side_effect=['{"wrong":true}', '```json\n{"ok":true}\n```']) as generate:
            self.assertTrue(ai.json("test", "prompt", validate)["ok"])
            self.assertTrue(ai.json("test", "prompt", validate)["ok"])
            self.assertEqual(generate.call_count, 2)

    def test_quota_error_does_not_retry_or_switch_provider(self):
        ai = TextAI(self.run, backend="gemini")
        error = urllib.error.HTTPError("https://example.invalid", 429, "quota", {}, io.BytesIO(b'{}'))
        with patch("text_ai.load_env", return_value={"GEMINI_API_KEY": "fake"}), patch("urllib.request.urlopen", side_effect=error) as call:
            with self.assertRaisesRegex(AIError, "429"):
                ai.json("test", "prompt", lambda x: None)
            self.assertEqual(call.call_count, 1)

    def test_gemini_key_is_header_and_usage_recorded(self):
        ai = TextAI(self.run, backend="gemini", model="gemini-3.5-flash-lite")
        payload = {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": '{"ok":true}'}]}}], "usageMetadata": {"totalTokenCount": 20}}
        with patch("text_ai.load_env", return_value={"GEMINI_API_KEY": "fake-test-key"}), patch("urllib.request.urlopen", return_value=io.StringIO(json.dumps(payload))) as call:
            self.assertTrue(ai.json("test", "prompt", lambda x: None)["ok"])
            request = call.call_args.args[0]
            self.assertNotIn("fake-test-key", request.full_url)
            self.assertEqual(request.get_header("X-goog-api-key"), "fake-test-key")
            self.assertEqual(ai.usage[0]["totalTokenCount"], 20)

    def test_incomplete_response_is_not_used(self):
        ai = TextAI(self.run, backend="gemini")
        payload = {"candidates": [{"finishReason": "MAX_TOKENS", "content": {"parts": [{"text": '{"ok":true}'}]}}]}
        with patch("text_ai.load_env", return_value={"GEMINI_API_KEY": "fake"}), patch("urllib.request.urlopen", return_value=io.StringIO(json.dumps(payload))):
            with self.assertRaisesRegex(AIError, "incompleta"):
                ai.json("test", "prompt", lambda x: None)

    def test_no_ai_is_detected_before_search(self):
        class MissingAI:
            def preflight(self):
                raise AIError("missing")
        with patch.object(flow, "command") as command:
            with self.assertRaises(AIError):
                flow.initial_analysis(self.run, "pedido", MissingAI())
            command.assert_not_called()

    def test_end_to_end_automatic_flow_stops_for_selection_then_builds_html(self):
        base = {"title": "Teste automático", "reference": None,
                "defaults": {"mode": "api", "probe_mode": "api", "duration": "longform", "pages": 1},
                "languages": [{"lang": "pt", "region": "BR"}, {"lang": "en", "region": "US"}], "cells": [], "probes": [], "competitors": []}
        common.write_json(self.run / "plan.json", base)
        class FakeAI:
            stages = []
            def preflight(self):
                pass
            def json(self, stage, prompt, validate):
                self.stages.append(stage)
                if stage == "hypotheses":
                    value = {"cells": [{"id": c, "label": c, "queries": {l: [f"{c} primeira", f"{c} segunda"] for l in ("pt", "en")}} for c in ("a", "b", "c")]}
                elif stage == "market_review":
                    value = {"summary": "Piloto observado", "candidates": [{"id": c, "priority": i + 1, "rationale": "6 vídeos nativos; mediana 50 mil; hipótese precisa validar formato.", "status": "cautela", "evidence": [{"video": "video000000"}], "markets": []} for i, c in enumerate(("a", "b", "c"))]}
                else:
                    value = {"summary": {"lead": "Amostra limitada com demanda observada", "findings": []}, "method": {"scan": "Dados fictícios no teste"},
                             "opportunities": [{"id": "a-pt", "name": "Teste", "lang": "pt", "cells": ["a__pt"],
                                 "scores": {k: {"v": 3, "why": "6 vídeos coletados; hipótese a validar", **({"measured": k in "DL"} if k in "DLFG" else {})} for k in "DLFGAKSMVR"},
                                 "evidence": [{"video": "video000000"}], "titles": ["Pauta teste"], "production": {"automation": "hipótese"}, "risks": "validar"}],
                             "limitations": ["Sem visão/transcrição; fit e formato julgados."]}
                validate(value)
                return value
        ai = FakeAI()
        def fake_search(query, lang, *args):
            return [{"id": f"video{i:06}", "title": query, "lang": lang, "views": 50000+i, "dur": 1500,
                     "published": "2026-09-01T00:00:00Z", "channel": "Dedicado", "channel_id": "UC" + "a"*22, "subs": 5000} for i in range(6)]
        actual_command = flow.command
        def local_command(script, *args, capture=False):
            if script == "profile_channels.py":
                run = Path(args[args.index("--run") + 1])
                common.write_json(run / "data/channels.json", [])
                return ""
            module = importlib.import_module(script.removesuffix(".py"))
            output = io.StringIO()
            with patch.object(sys, "argv", [script, *map(str, args)]), contextlib.redirect_stdout(output):
                try:
                    module.main()
                except SystemExit as e:
                    if e.code:
                        raise ValueError(output.getvalue())
            return output.getvalue() if capture else None
        with patch.object(flow, "command", side_effect=local_command), patch("scan.yt_api.search", side_effect=fake_search), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(flow.initial_analysis(self.run, "pedido", ai), "pending")
            self.assertFalse((self.run / "relatorio.html").exists())
            data_ai = TextAI(self.run, backend="dados")
            with patch("scan.yt_api.search", side_effect=AssertionError("Modo dados não pode buscar")):
                self.assertEqual(flow.initial_analysis(self.run, "pedido", data_ai), "pending")
            with self.assertRaises(ValueError):
                flow.finish_analysis(self.run, "pedido", ai)
            selection.select(self.run, ["a"], ["pt"])
            report = flow.finish_analysis(self.run, "pedido", ai)
            self.assertTrue(report.exists())
            self.assertEqual(ai.stages, ["hypotheses", "market_review", "analysis"])
            self.assertEqual(flow.initial_analysis(self.run, "pedido", ai), "selected")
            with patch("scan.yt_api.search", side_effect=AssertionError("Modo dados não pode buscar")):
                flow.finish_analysis(self.run, "pedido", data_ai)
            technical = common.read_json(self.run / "analysis.json")
            self.assertEqual(technical["analysis_mode"], "technical")
            self.assertEqual(technical["opportunities"], [])
            self.assertEqual(data_ai.calls, 0)
            with self.assertRaisesRegex(ValueError, "pedido mudou"):
                flow.initial_analysis(self.run, "outro pedido", ai)

    def test_wrong_selection_folder_has_correct_command_hint(self):
        common.write_json(self.run / "plan.json", {"cells": []})
        common.write_json(self.run / "triage/source.json", {})
        with self.assertRaisesRegex(ValueError, "Pasta errada"):
            selection.require_triage(self.run / "triage", {})

    def test_data_mode_does_not_invent_hypotheses(self):
        common.write_json(self.run / "plan.json", {"cells": [], "languages": []})
        ai = TextAI(self.run, backend="dados")
        with patch.object(flow, "command") as command:
            with self.assertRaisesRegex(ValueError, "não inventa recortes"):
                flow.initial_analysis(self.run, "pedido", ai)
            command.assert_not_called()

    def test_legacy_state_migration_omits_secrets_and_does_not_reset_counter(self):
        from colab_support import migrate_legacy_state
        old, new = Path(self.tmp.name)/"legacy", Path(self.tmp.name)/"new"
        common.write_json(old / "quota.json", {"day": {"searches": 12}})
        common.write_json(old / "cache/video.json", {"items": []})
        (old / ".env").write_text("private", encoding="utf-8")
        self.assertEqual(set(migrate_legacy_state(old, new)), {"quota.json", "cache"})
        self.assertFalse((new / ".env").exists())
        common.write_json(new / "quota.json", {"day": {"searches": 20}})
        self.assertEqual(migrate_legacy_state(old, new), [])
        self.assertEqual(common.read_json(new / "quota.json")["day"]["searches"], 20)

    def test_generated_notebooks_have_no_intermediate_uploads_or_saved_outputs(self):
        for name in ("DarkNiche.ipynb", "DarkNiche-Retomar.ipynb"):
            nb = json.loads((SKILL/"extras/colab"/name).read_text(encoding="utf-8"))
            code = [c for c in nb["cells"] if c["cell_type"] == "code"]
            self.assertEqual(sum('files.upload()' in ''.join(c["source"]) for c in code), 1)
            for cell in code:
                compile(''.join(cell["source"]), cell["id"], 'exec')
                self.assertEqual(cell["outputs"], [])


if __name__ == "__main__":
    unittest.main()
