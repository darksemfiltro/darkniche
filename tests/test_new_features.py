"""Testes offline das funções da versão 1.0: veredito, ritmo e concentração, idiomas, pesquisa web, aprovação e sinais."""
import json
import random
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "analise-mercado-yt"
sys.path.insert(0, str(SKILL / "scripts"))
import common  # noqa: E402
import metrics  # noqa: E402
import plan_tools  # noqa: E402
import research  # noqa: E402
import scan  # noqa: E402
import score  # noqa: E402
import selection  # noqa: E402
import signals  # noqa: E402
import yt_api  # noqa: E402


def make_rows(n=60, channels=20, lang="pt", title="Como sair das dívidas passo {i}", base_views=2000, age0=15):
    rng, now, out = random.Random(1), datetime.now(timezone.utc), []
    for i in range(n):
        c = i % channels
        out.append({"id": f"v{i:010d}", "title": title.format(i=i), "lang": lang, "views": int(base_views * (i + 1) ** 1.4 * rng.uniform(0.8, 1.2)),
                    "published": (now - timedelta(days=age0 + i * 5)).strftime("%Y-%m-%dT00:00:00Z"), "dur": 600 + (i * 37) % 900,
                    "channel_id": f"UC{c:022d}", "channel": f"Canal {c}", "subs": 500 * (c + 1) ** 3,
                    "ch_created": (now - timedelta(days=60 + c * 120)).strftime("%Y-%m-%dT00:00:00Z")})
    return out


def opportunity(D, L, F, G, R=2, measured=(1, 1, 0, 0), cells=("t__pt",)):
    mk = lambda v, m: {"v": v, "measured": bool(m), "why": "x"}
    return {"id": "t", "cells": list(cells), "scores": {"D": mk(D, measured[0]), "L": mk(L, measured[1]), "F": mk(F, measured[2]), "G": mk(G, measured[3]),
                                                       "A": 4, "K": 4, "S": 4, "M": 3, "V": 3, "R": R}}


class VerdictTests(unittest.TestCase):
    cells = {"t__pt": {"m": {"n_long": 20}}}

    def verdict(self, *a, **k):
        return score.compute(opportunity(*a, **k), None, self.cells)

    def test_go_testar_evitar(self):
        self.assertEqual(self.verdict(5, 5, 5, 5, measured=(1, 1, 1, 1))["verdict"], "GO")
        self.assertEqual(self.verdict(5, 4, 5, 5, measured=(1, 0, 0, 0))["verdict"], "TESTAR")
        self.assertEqual(self.verdict(2, 5, 4, 4)["verdict"], "EVITAR")
        self.assertEqual(self.verdict(5, 5, 5, 5, R=5, measured=(1, 1, 1, 1))["verdict"], "EVITAR")

    def test_mar_vermelho_so_evita_sem_formato_diferente(self):
        self.assertEqual(self.verdict(5, 1, 4, 3)["verdict"], "EVITAR")
        self.assertEqual(self.verdict(5, 2, 4, 5, measured=(1, 1, 0, 1))["verdict"], "TESTAR")

    def test_faixa_cobre_so_os_eixos_julgados(self):
        c = self.verdict(4, 4, 4, 4, measured=(1, 1, 1, 1))
        self.assertEqual(c["range"], [c["total"], c["total"]])
        c = self.verdict(4, 4, 4, 4, measured=(0, 0, 0, 0))
        self.assertLess(c["range"][0], c["total"])
        self.assertGreater(c["range"][1], c["total"])

    def test_confianca_cai_com_amostra_pequena(self):
        for n_long, expected in ((3, "baixa"), (7, "média"), (20, "alta")):
            cells = {"t__pt": {"m": {"n_long": n_long}}}
            c = score.compute(opportunity(5, 5, 5, 5, measured=(1, 1, 1, 1)), None, cells)
            self.assertEqual(c["confidence"], expected, n_long)


class MetricsTests(unittest.TestCase):
    def test_ritmo_ignora_video_novo_e_n_eff_mede_concentracao(self):
        rows = make_rows(40, channels=40)
        m = metrics.cell_metrics(rows, "pt", 480, 540, 3000, 365)
        self.assertEqual(m["n_mature"], len([r for r in rows if r["dur"] >= 480]))
        self.assertGreater(m["n_eff"], 20)
        one = [{**r, "channel_id": "UC" + "a" * 22} for r in rows]
        self.assertEqual(metrics.cell_metrics(one, "pt", 480, 540, 3000, 365)["n_eff"], 1.0)

    def test_video_com_menos_de_14_dias_nao_entra_no_ritmo(self):
        rows = [{**r, "published": (datetime.now(timezone.utc) - timedelta(days=3)).strftime("%Y-%m-%dT00:00:00Z")} for r in make_rows(10)]
        m = metrics.cell_metrics(rows, "pt", 480, 540, 3000, 365)
        self.assertEqual(m["n_mature"], 0)
        self.assertIsNone(m["vpd_p50"])

    def test_cabeca_saturada_e_oferta_no_teto(self):
        rows = [{**r, "views": 500_000 + i} for i, r in enumerate(make_rows(40))]
        m = metrics.cell_metrics(rows, "pt", 480, 540, 3000, 365, 1_000_000)
        self.assertIn("cabeca_saturada", m["flags"])
        self.assertIn("oferta_acima_do_teto", m["flags"])

    def test_idioma_desconhecido(self):
        unknown = [{**r, "title": "xyz", "lang": None} for r in make_rows(20)]
        pt = metrics.cell_metrics(unknown, "pt", 480, 540, 3000, 365)
        self.assertEqual((pt["n_native"], pt["n_long"], pt["n_unknown_lang"]), (0, 0, 20))
        self.assertIn("idioma_nao_verificado", pt["flags"])
        fa = metrics.cell_metrics(unknown, "fa", 480, 540, 3000, 365)
        self.assertGreaterEqual(fa["n_long"], 10)
        self.assertIn("idioma_nao_verificavel", fa["flags"])

    def test_keywords_em_grupos_exigem_um_termo_de_cada(self):
        cell = {"keywords": [["chatgpt", "claude"], ["financ", "gastos"]], "exclude": ["jogo"]}
        row = lambda t: {"title": t}
        self.assertTrue(metrics.relevant(row("Claude para controlar seus GASTOS"), cell, "pt"))
        self.assertFalse(metrics.relevant(row("Aprenda Claude em 20 minutos"), cell, "pt"))
        self.assertFalse(metrics.relevant(row("Finanças pessoais do zero"), cell, "pt"))
        self.assertFalse(metrics.relevant(row("ChatGPT e finanças: jogo de perguntas"), cell, "pt"))
        self.assertTrue(metrics.relevant(row("qualquer"), {"keywords": ["qual"]}, "pt"))  # lista simples continua sendo OU

    def test_lacuna_limitada_quando_o_idioma_nao_foi_verificado(self):
        cells = [{"id": "a", "lang": "pt", "m": metrics.cell_metrics(make_rows(10, channels=2) + [{**r, "title": "xyz", "lang": None} for r in make_rows(8, channels=2)], "pt", 480, 540, 3000, 365)}]
        auto = metrics.auto_scores(cells)[0]["auto"]
        self.assertLessEqual(auto["L"], 3)

    def test_tamanho_de_mercado_assumido_limita_a_demanda(self):
        cells = [{"id": "a", "lang": "xx", "m": metrics.cell_metrics(make_rows(40, lang="xx"), "xx", 480, 540, 3000, 365)}]
        auto = metrics.auto_scores(cells, {"languages": [{"lang": "xx"}]})[0]["auto"]
        self.assertLessEqual(auto["D"], 3)
        self.assertIn("tamanho_assumido", auto["flags"])


class ProfileTests(unittest.TestCase):
    def test_canal_dedicado_aceita_keywords_em_grupos_e_consulta(self):
        import profile_channels
        plan = {"cells": [{"id": "ia", "queries": {"pt": ["planilha financeira com IA"]},
                           "keywords": {"pt": [["chatgpt", "claude"], ["financ", "gastos"]]}},
                          {"id": "sem-kw", "queries": {"pt": ["como renegociar dívida do cartão"]}}]}
        matchers, basis = profile_channels.topic_matchers(plan, ["ia/pt"])
        self.assertEqual((len(matchers), len(matchers[0]), basis), (1, 2, "keywords"))
        matchers, basis = profile_channels.topic_matchers(plan, ["sem-kw/pt"])
        self.assertEqual(basis, "consulta")
        self.assertIn("renegociar", matchers[0][0])


class LanguageTests(unittest.TestCase):
    def test_detectores_por_titulo(self):
        amostras = {"sv": "Hur du sparar pengar och varför det är viktigt", "fi": "Kuinka säästää rahaa ja miksi se on tärkeää",
                    "cs": "Jak ušetřit peníze a proč je to důležité", "hu": "Hogyan spórolj pénzt és miért fontos ez",
                    "vi": "Cách tiết kiệm tiền và tại sao điều đó quan trọng", "he": "איך לחסוך כסף בלי לוותר על החיים",
                    "pt": "Como sair das dívidas e por que você não consegue"}
        for lang, title in amostras.items():
            self.assertEqual(common.guess_lang(title), lang, title)

    def test_persa_e_urdu_valem_o_metadado(self):
        self.assertEqual(common.video_lang({"title": "چگونه پول پس انداز کنیم", "lang": "fa"}), "fa")
        self.assertFalse(common.can_verify_lang("fa"))
        self.assertTrue(common.can_verify_lang("pt"))

    def test_regiao_do_idioma(self):
        self.assertEqual(common.parse_lang_spec("es-AR"), ("es", "AR", "ES-AR"))
        self.assertEqual(common.parse_lang_spec("pt"), ("pt", "BR", "PT-BR"))
        self.assertIsNone(common.parse_lang_spec("fa")[1])

    def test_redact_mascara_chave_e_parametro(self):
        fake = "AIza" + "x" * 35
        out = common.redact(f"erro https://x/y?key={fake}&a=1 e token=abc123")
        self.assertNotIn(fake, out)
        self.assertNotIn("abc123", out)


class ResearchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.run = Path(self.tmp.name)
        self.today = datetime.now().strftime("%Y-%m-%d")

    def tearDown(self):
        self.tmp.cleanup()

    def add(self, **kw):
        base = dict(topic="monetizacao", claim="RPM de teste", url="https://example.org/x", accessed=self.today, type="dados", confidence="media")
        return research.add(self.run, **{**base, **kw})

    def test_registro_e_checagem(self):
        e, warn = self.add(value="US$ 2-4")
        self.assertEqual(e["id"], "r1")
        self.assertEqual(e["domain"], "example.org")
        _, errors, _ = research.check(self.run)
        self.assertTrue(any("politica" in m for m in errors))
        self.add(topic="politica", claim="Regra de teste", type="oficial", confidence="alta")
        _, errors, _ = research.check(self.run)
        self.assertEqual(errors, [])

    def test_recusa_url_data_futura_e_citacao_longa(self):
        for bad in ({"url": "ftp://x"}, {"accessed": "2999-01-01"}, {"quote": " ".join(["palavra"] * 30)}, {"topic": "outra"}):
            with self.assertRaises(ValueError):
                self.add(**bad)

    def test_numero_so_de_blog_vira_aviso(self):
        _, warn = self.add(value="US$ 5", type="blog", confidence="baixa")
        self.assertTrue(any("segunda fonte" in w for w in warn))


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.run = Path(self.tmp.name)
        self.plan = {"title": "t", "defaults": {"mode": "api", "after_days": 365, "duration": "longform", "pages": 1},
                     "languages": [{"lang": "pt", "region": "BR"}], "cells": [{"id": "a", "queries": {"pt": ["como sair das dívidas"]}}], "probes": []}
        common.write_json(self.run / "plan.json", self.plan)

    def tearDown(self):
        self.tmp.cleanup()

    def test_approve_registra_e_mudanca_de_consulta_invalida(self):
        state = selection.approve(self.run, 60, 500)
        self.assertEqual(state["scan_estimate"]["searches"], 2)
        selection.require_selection(self.run, self.plan)
        changed = json.loads(json.dumps(self.plan))
        changed["cells"][0]["queries"]["pt"] = ["outra consulta"]
        with self.assertRaises(ValueError):
            selection.require_selection(self.run, changed)

    def test_approve_recusa_teto_estourado(self):
        with self.assertRaises(ValueError):
            selection.approve(self.run, 1, 500)

    def test_plano_recusa_idioma_nao_declarado(self):
        bad = json.loads(json.dumps(self.plan))
        bad["cells"][0]["queries"] = {"pt-BR": ["x"]}
        with self.assertRaises(ValueError):
            plan_tools.validate_plan(bad)


class ScanTests(unittest.TestCase):
    def test_longform_soma_a_oferta_das_duas_faixas(self):
        def fake(q, lang, region, pages, after, duration, order, category):
            return yt_api.Rows([{"id": f"{duration[:3]}{q[:1]}{i:07d}"[:11].ljust(11, "0"), "title": q} for i in range(2)], {"total_results": 100})
        with patch("scan.yt_api.search", side_effect=fake):
            rows = scan.run_query("tema", "pt", "BR", {"duration": "longform", "after_days": 365}, "api")
        self.assertEqual(rows.meta["total_results"], 200)
        self.assertEqual(len(rows), 4)


class SignalTests(unittest.TestCase):
    def test_wikipedia_tendencia_relativa_a_propria_wikipedia(self):
        def series(first, last):
            return {"items": [{"views": first}] * 12 + [{"views": last}] * 12}
        def fake(url, ttl_h=72):
            if "action=query" in url and "pageprops" in url:
                return {"query": {"pages": {"1": {"pageprops": {"wikibase_item": "Q1"}, "title": "Teste"}}}}
            if "wikidata.org" in url:
                return {"entities": {"Q1": {"sitelinks": {"enwiki": {"title": "Test"}, "ptwiki": {"title": "Teste"}}}}}
            if "aggregate" in url:
                return {"items": [{"views": 10 ** 9}] * 24}
            return series(1000, 1500) if "/en.wikipedia/" in url else series(1000, 600)
        with patch.object(signals, "_get_json", side_effect=fake):
            res = signals.wiki("Test", "en", ["pt"])
        by = {r["lang"]: r for r in res["rows"]}
        self.assertEqual(by["en"]["trend"], "subindo")
        self.assertEqual(by["pt"]["trend"], "caindo")

    def test_noticias_ritmo_da_ultima_semana(self):
        now = datetime.now(timezone.utc)
        item = lambda d: f"<item><title>n</title><link>https://x/{d}</link><pubDate>{format_datetime(now - timedelta(days=d))}</pubDate><source>Fonte</source></item>"
        xml = "<rss><channel>" + "".join(item(d) for d in [1, 2, 3, 4, 5, 6] + [10, 12, 15, 20, 25, 28]) + "</channel></rss>"
        with patch.object(signals, "_fetch", return_value=xml):
            res = signals.news("tema", "pt", "BR", 30)
        self.assertEqual((res["n_total"], res["n_7d"]), (12, 6))
        self.assertEqual(res["trend"], "acelerando")

    def test_em_alta_le_o_rss_do_google_trends(self):
        xml = ('<rss xmlns:ht="https://trends.google.com/trending/rss"><channel><item><title>assunto</title>'
               '<ht:approx_traffic>200+</ht:approx_traffic></item></channel></rss>')
        with patch.object(signals, "_fetch", return_value=xml):
            res = signals.trending("BR", 5, False)
        self.assertEqual(res["google_trends"][0]["query"], "assunto")
        self.assertEqual(res["google_trends"][0]["traffic"], "200+")


class RevisaoTests(unittest.TestCase):
    """Defeitos achados na revisão de código da versão 1.0."""

    def test_titulo_em_portugues_com_a_circunflexo_nao_vira_romeno(self):
        for t in ("A importância do câmbio para quem investe", "Atlântico: por que o dólar sobe e o que isso muda"):
            self.assertNotEqual(common.video_lang({"title": t}), "ro", t)
        self.assertEqual(common.video_lang({"title": "Cum să faci bani în 2026 și de ce nu merge"}), "ro")

    def test_empate_entre_idiomas_nao_decide_pela_ordem_do_dicionario(self):
        self.assertIsNone(common.lang_evidence("Como invertir para principiantes")["lang"])
        self.assertEqual(common.video_lang({"title": "Como invertir para principiantes", "lang": "es"}), "es")

    def test_cirilico_sem_marcador_fica_sem_idioma(self):
        self.assertIsNone(common.lang_evidence("Деньги и власть")["lang"])
        self.assertEqual(common.video_lang({"title": "Деньги и власть", "lang": "ru"}), "ru")
        self.assertEqual(common.lang_evidence("Почему это работает")["lang"], "ru")

    def test_kanji_sem_kana_vale_o_metadado_japones(self):
        self.assertEqual(common.video_lang({"title": "経済危機", "lang": "ja"}), "ja")
        self.assertEqual(common.video_lang({"title": "経済危機"}), "zh")

    def test_codigo_antigo_de_idioma_e_d_cortado(self):
        self.assertEqual(common.video_lang({"title": "Hvordan spare penger", "lang": "nb"}), "no")
        self.assertNotEqual(common.lang_evidence("Đurđevdan običaji i priča")["lang"], "vi")

    def test_palavra_inteira_nas_pontas_e_termo_vazio(self):
        cell = {"keywords": [" ia "]}
        for t in ("IA para finanças pessoais", "Usando IA, finanças ficam fáceis", "Como a ia", "Finanças com IA"):
            self.assertTrue(metrics.relevant({"title": t}, cell, "pt"), t)
        self.assertFalse(metrics.relevant({"title": "Iate de luxo"}, cell, "pt"))
        self.assertTrue(metrics.relevant({"title": "qualquer"}, {"exclude": [""]}, "pt"))
        self.assertTrue(metrics.relevant({"title": "Aprenda c++ do zero"}, {"keywords": ["c++"]}, "pt"))
        self.assertFalse(metrics.relevant({"title": "Aprenda c do zero"}, {"keywords": ["c++"]}, "pt"))

    def test_persa_sem_metadado_conta_como_provisorio(self):
        rows = [{**r, "title": "چگونه پول پس انداز کنیم", "lang": None} for r in make_rows(12)]
        m = metrics.cell_metrics(rows, "fa", 480, 540, 3000, 365)
        self.assertGreaterEqual(m["n_long"], 6)
        self.assertIn("idioma_nao_verificavel", m["flags"])

    def test_uma_linha_sem_duracao_nao_torna_a_sondagem_inconclusiva(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "raw" / "probes"
            d.mkdir(parents=True)
            rows = [{"id": f"p{i:010d}", "title": f"Receita de bolo número {i}", "lang": "pt", "views": 500000, "dur": 900} for i in range(19)]
            rows.append({"id": "p9999999999", "title": "Receita sem duração", "lang": "pt", "views": 10, "dur": None})
            (d / "a.json").write_text(json.dumps({"probe": "a", "lang": "pt", "query": "ajuste fiscal explicado para iniciantes", "rows": rows}), encoding="utf-8")
            self.assertEqual(metrics.probe_summary(tmp, 480)[0]["status"], "lacuna")

    def test_base64_do_relatorio_nao_tem_barra_m_barra(self):
        import base64
        import build_report
        seq = "/" + "m" + "/"  # montada aqui para o verificador de caminhos da DSF não acusar o próprio teste
        data = base64.b64decode(seq + "+" + seq.upper() + "+AAAA")
        out = build_report._b64(data)
        self.assertNotIn(seq, out.lower())
        self.assertEqual(base64.b64decode(out), data)  # a quebra de linha não muda o conteúdo

    def test_redact_mascara_nome_de_campo_com_prefixo(self):
        out = common.redact("YT_API_KEY=segredo123 access_token=xyz9 client_secret=abc7 passwd=qq88")
        for s in ("segredo123", "xyz9", "abc7", "qq88"):
            self.assertNotIn(s, out)

    def test_pesquisa_recusa_url_com_credencial_ou_chave(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = dict(topic="monetizacao", claim="fato", accessed=datetime.now().strftime("%Y-%m-%d"), type="dados", confidence="media")
            for bad in ("https://user:segredo@example.com/p", "https://example.com/p?api_key=abc", "https://example.com/p?k=AIza" + "x" * 30):
                with self.assertRaises(ValueError):
                    research.add(tmp, **base, url=bad)
            e, _ = research.add(tmp, **base, url="https://www.example.com/p?keyword=financas")
            self.assertEqual(e["domain"], "example.com")

    def test_sem_data_ou_inscritos_o_veredito_nao_chega_a_go(self):
        op = opportunity(5, 5, 5, 5, measured=(1, 1, 1, 1))
        parcial = score.compute(op, None, {"t__pt": {"m": {"n_long": 30, "flags": ["sem_datas", "sem_inscritos"]}}})
        self.assertEqual((parcial["verdict"], parcial["confidence"]), ("TESTAR", "baixa"))
        self.assertEqual(score.compute(op, None, {"t__pt": {"m": {"n_long": 30, "flags": []}}})["verdict"], "GO")

    def test_pasta_com_colchetes_nao_vira_curinga(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "analise [Clientes]" / "raw"
            d.mkdir(parents=True)
            (d / "a.json").write_text("{}", encoding="utf-8")
            self.assertEqual(len(common.glob_files(d)), 1)

    def test_titulo_sem_letra_latina_gera_pastas_diferentes(self):
        self.assertNotEqual(common.slug("日本の経済"), common.slug("株式投資"))

    def test_tamanho_de_mercado_aceita_virgula_e_plano_nulo(self):
        self.assertEqual(common.market_size("pt", {"languages": [{"lang": "pt", "size": "0,33"}]}), 0.33)
        self.assertEqual(common.market_size("pt", {"languages": None}), common.MARKET_SIZE["pt"])

    def test_plano_com_celula_sem_consultas_e_recusado(self):
        with self.assertRaises(ValueError):
            plan_tools.validate_plan({"languages": [{"lang": "pt"}], "cells": [{"id": "a"}]})

    def test_init_run_ignora_idioma_vazio(self):
        import os
        import subprocess
        with tempfile.TemporaryDirectory() as tmp:
            env = {**os.environ, "AMY_HOME": tmp, "AMY_DATA": tmp}
            subprocess.run([sys.executable, str(SKILL / "scripts" / "init_run.py"), "T", "--langs", "pt,en,", "--dir", tmp],
                           check=True, capture_output=True, env=env)
            plan = json.loads(next(Path(tmp).glob("*/plan.json")).read_text(encoding="utf-8"))
        self.assertEqual([l["lang"] for l in plan["languages"]], ["pt", "en"])

    def test_wikipedia_sem_wikidata_nao_entra_em_recursao(self):
        def fake(url, ttl_h=72):
            if "list=search" in url:
                return {"query": {"search": [{"title": "Outra"}]}}
            return {"query": {"pages": {"1": {"title": "x"}}}}
        with patch.object(signals, "_get_json", side_effect=fake):
            self.assertEqual(signals._qid("Teste", "en"), (None, None))

    def test_wikipedia_com_menos_de_24_meses_nao_calcula_variacao(self):
        def fake(url, ttl_h=72):
            if "pageprops" in url:
                return {"query": {"pages": {"1": {"pageprops": {"wikibase_item": "Q1"}, "title": "T"}}}}
            if "wikidata.org" in url:
                return {"entities": {"Q1": {"sitelinks": {"enwiki": {"title": "T"}}}}}
            if "aggregate" in url:
                return {"items": [{"views": 10 ** 9}] * 24}
            return {"items": [{"views": 1000}] * 18}
        with patch.object(signals, "_get_json", side_effect=fake):
            row = signals.wiki("T", "en", [])["rows"][0]
        self.assertIsNone(row["yoy"])
        self.assertIsNone(row["trend"])

    def test_noticias_com_toda_a_cobertura_na_ultima_semana(self):
        now = datetime.now(timezone.utc)
        item = lambda d: f"<item><title>n</title><link>https://x/{d}</link><pubDate>{format_datetime(now - timedelta(days=d))}</pubDate><source>Fonte</source></item>"
        xml = "<rss><channel>" + "".join(item(d) for d in [0, 1, 1, 2, 3, 4, 5, 6]) + "</channel></rss>"
        with patch.object(signals, "_fetch", return_value=xml):
            self.assertEqual(signals.news("tema", "pt", "BR", 30)["trend"], "acelerando")


if __name__ == "__main__":
    unittest.main()
