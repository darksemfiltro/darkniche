"""Autoteste offline da skill: sem rede, sem chave e sem gastar cota. Roda em uma pasta temporária.

  python scripts/selftest.py

Confere a sintaxe dos scripts, as regras de idioma e de segredos, as métricas e o veredito com dados sintéticos e a
cadeia inteira (plano → métricas → pesquisa → verificador → nota → relatório HTML). Sai com código 1 se algo falhar.
Rode depois de instalar ou de editar a skill.
"""
from __future__ import annotations

import ast
import json
import os
import random
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
FAIL, OKS = [], []


def check(name, cond, detail=""):
    (OKS if cond else FAIL).append(name if cond else f"{name} {detail}".strip())


def run(*args, env=None, check_code=True):
    p = subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, encoding="utf-8", env=env)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def rows_for(n=60):
    """Vídeos sintéticos em português: 20 canais de tamanhos diferentes, idades e views variadas."""
    rng, now, out = random.Random(1), datetime.now(timezone.utc), []
    for i in range(n):
        c = i % 20
        out.append({"id": f"v{i:010d}", "title": f"Como sair das dívidas passo {i}", "published": (now - timedelta(days=15 + i * 5)).strftime("%Y-%m-%dT00:00:00Z"),
                    "lang": "pt", "views": int(2000 * (i + 1) ** 1.4 * rng.uniform(0.8, 1.2)), "likes": 10, "comments": 3, "dur": 600 + (i * 37) % 900,
                    "channel_id": f"UC{c:022d}", "channel": f"Canal {c}", "subs": 500 * (c + 1) ** 3, "ch_created": (now - timedelta(days=60 + c * 120)).strftime("%Y-%m-%dT00:00:00Z"),
                    "ch_videos": 100, "ch_views": 10 ** 6, "tags": [], "desc_links": 0, "category": "27", "caption": False})
    return out


def main():
    # 1) sintaxe e importação
    for f in sorted(HERE.glob("*.py")):
        try:
            ast.parse(f.read_text(encoding="utf-8"))
            check(f"sintaxe {f.name}", True)
        except SyntaxError as e:
            check(f"sintaxe {f.name}", False, str(e))
    import common
    import metrics
    import plan_tools
    import research
    import score

    # 2) idioma, região e segredos
    check("parse_lang_spec pt", common.parse_lang_spec("pt") == ("pt", "BR", "PT-BR"))
    check("parse_lang_spec es-AR", common.parse_lang_spec("es-AR") == ("es", "AR", "ES-AR"))
    check("idioma sem região", common.parse_lang_spec("fa")[1] is None)
    fake = "AIza" + "x" * 35
    check("redact chave", fake not in common.redact(f"erro https://x?key={fake} AIza{'y' * 30}"))
    check("video_lang título pt", common.video_lang({"title": "Como sair das dívidas e por que você não consegue"}) == "pt")
    try:
        plan_tools.validate_plan({"languages": [{"lang": "pt"}], "cells": [{"id": "a", "queries": {"pt-BR": ["x"]}}]})
        check("validate_plan recusa pt-BR", False)
    except ValueError:
        check("validate_plan recusa pt-BR", True)

    # 3) métricas e veredito com dados sintéticos
    m = metrics.cell_metrics(rows_for(), "pt", 480, 540, 3000, 365, 1200)
    check("métricas n_long", m["n_long"] >= 40, m["n_long"])
    check("métricas ritmo", m["vpd_p50"] and m["vpd_p50"] > 0)
    check("métricas canais efetivos", m["n_eff"] and 1 <= m["n_eff"] <= 20, m["n_eff"])
    check("métricas faixas de inscritos", m["size_mix"] and abs(sum(v["views"] for v in m["size_mix"].values()) - 1) < 0.1)
    unknown = [{**r, "title": "xyz", "lang": None} for r in rows_for(20)]
    mu = metrics.cell_metrics(unknown, "pt", 480, 540, 3000, 365)
    check("idioma desconhecido não vira nativo (pt)", mu["n_long"] == 0 and mu["n_unknown_lang"] == 20 and "idioma_nao_verificado" in mu["flags"], mu["flags"])
    mf = metrics.cell_metrics(unknown, "fa", 480, 540, 3000, 365)
    check("idioma sem detector: desconhecido entra como provisório e a flag avisa", mf["n_long"] >= 10 and "idioma_nao_verificavel" in mf["flags"], mf["flags"])
    amostras = {"sv": "Hur du sparar pengar och varför det är viktigt", "fi": "Kuinka säästää rahaa ja miksi se on tärkeää",
                "cs": "Jak ušetřit peníze a proč je to důležité", "hu": "Hogyan spórolj pénzt és miért fontos ez",
                "vi": "Cách tiết kiệm tiền và tại sao điều đó quan trọng", "he": "איך לחסוך כסף בלי לוותר על החיים"}
    check("detector de idioma por título (sv, fi, cs, hu, vi, he)", all(common.guess_lang(t) == l for l, t in amostras.items()),
          {l: common.guess_lang(t) for l, t in amostras.items()})
    check("persa com título em escrita árabe vale o metadado", common.video_lang({"title": "چگونه پول پس انداز کنیم", "lang": "fa"}) == "fa")

    def opp(D, L, F, G, R=2, measured=(1, 1, 0, 0)):
        mk = lambda v, ms: {"v": v, "measured": bool(ms), "why": "x"}
        return {"id": "t", "cells": ["t__pt"], "scores": {"D": mk(D, measured[0]), "L": mk(L, measured[1]), "F": mk(F, measured[2]), "G": mk(G, measured[3]),
                                                           "A": 4, "K": 4, "S": 4, "M": 3, "V": 3, "R": R}}
    cells = {"t__pt": {"m": {"n_long": 20}}}
    check("veredito GO", score.compute(opp(5, 5, 5, 5, measured=(1, 1, 1, 1)), None, cells)["verdict"] == "GO")
    check("veredito TESTAR", score.compute(opp(5, 4, 5, 5, measured=(1, 0, 0, 0)), None, cells)["verdict"] == "TESTAR")
    check("veredito EVITAR demanda vazia", score.compute(opp(2, 5, 4, 4), None, cells)["verdict"] == "EVITAR")
    check("veredito EVITAR risco 5", score.compute(opp(5, 5, 5, 5, R=5, measured=(1, 1, 1, 1)), None, cells)["verdict"] == "EVITAR")

    # 4) cadeia inteira numa pasta temporária (nada fora dela)
    with tempfile.TemporaryDirectory(prefix="amy-selftest-") as tmp:
        tmp = Path(tmp)
        env = {**os.environ, "AMY_HOME": str(tmp / "home"), "AMY_DATA": str(tmp / "home"), "PYTHONDONTWRITEBYTECODE": "1", "YT_API_KEY": "", "YOUTUBE_API_KEY": ""}
        code, out = run(HERE / "init_run.py", "Teste dividas", "--langs", "pt,en,fa", "--dir", tmp / "analises", env=env)
        runp = Path(out.strip().splitlines()[0]) if code == 0 else None  # 1ª linha = stdout (o caminho); os avisos vêm do stderr, depois
        check("init_run cria o plano", bool(runp) and (runp / "plan.json").exists(), out[-200:])
        if not runp:
            return
        plan = json.loads((runp / "plan.json").read_text(encoding="utf-8"))
        check("plano: região de fa fica vazia e tamanho assumido", [l for l in plan["languages"] if l["lang"] == "fa"][0]["region"] is None)
        plan["cells"] = [{"id": "t", "label": "Dívidas", "queries": {"pt": ["como sair das dívidas"]}}]
        plan["defaults"]["mode"] = "api"
        (runp / "plan.json").write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
        cell = plan["cells"][0]
        flt = plan_tools.cell_filters(plan["defaults"], cell, "pt")
        sig = plan_tools.signature("como sair das dívidas", "pt", plan_tools.region_for(plan, "pt"), flt, "api")
        raw = runp / "raw" / "search" / "t__pt.api.json"
        raw.parent.mkdir(parents=True, exist_ok=True)
        raw.write_text(json.dumps({"cell": "t", "lang": "pt", "query": "como sair das dívidas", "mode": "api", "filters": flt, "fetched_at": "2026-01-01T00:00Z",
                                   "meta": {"total_results": 1200}, "signature": sig, "rows": rows_for()}), encoding="utf-8")
        code, out = run(HERE / "metrics.py", "--run", runp, env=env)
        check("metrics.py roda", code == 0 and (runp / "data" / "cells.json").exists(), out[-300:])
        code, out = run(HERE / "scan.py", "--run", runp, env=env)
        check("scan recusa sem aprovação (código 4)", code == 4, f"{code} {out[-200:]}")
        code, out = run(HERE / "selection.py", "approve", "--run", runp, env=env)
        check("approve registra o plano", code == 0 and (runp / "selection.json").exists(), out[-300:])
        # pesquisa: sem política o verificador reprova; com ela passa
        code, out = run(HERE / "research.py", "add", "--run", runp, "--topic", "monetizacao", "--claim", "RPM de teste", "--value", "US$ 2-4", "--url",
                        "https://example.org/rpm", "--accessed", datetime.now().strftime("%Y-%m-%d"), "--type", "dados", "--confidence", "media", env=env)
        check("research add", code == 0, out[-200:])
        code, out = run(HERE / "research.py", "check", "--run", runp, env=env)
        check("research check reprova sem política", code == 1 and "politica" in out, out[-200:])
        run(HERE / "research.py", "add", "--run", runp, "--topic", "politica", "--claim", "Regra de teste", "--url", "https://example.org/regra",
            "--accessed", datetime.now().strftime("%Y-%m-%d"), "--type", "oficial", "--confidence", "alta", env=env)
        cells_json = json.loads((runp / "data" / "cells.json").read_text(encoding="utf-8"))
        top = cells_json[0]["m"]["top"]
        ax = lambda v, why, m=None: {"v": v, "why": why, **({"measured": m} if m is not None else {})}
        an = {"meta": {"title_html": "Teste <span class=\"acc\">offline</span>"},
              "summary": {"lead": "Dados sintéticos.", "verdict_text": "Teste de ponta a ponta.", "findings": [{"title": f"Achado {i}.", "text": "x"} for i in range(3)]},
              "opportunities": [{"id": "dividas-pt", "name": "Dívidas", "lang": "pt", "oneliner": "Teste.", "cells": ["t__pt"],
                                 "scores": {"D": ax(4, "ritmo medido", True), "L": ax(3, "canais medidos", True), "F": ax(4, "julgado", False), "G": ax(3, "julgado", False),
                                            "A": ax(4, "x"), "K": ax(4, "x"), "S": ax(4, "x"), "M": ax(3, "RPM (r1)"), "V": ax(3, "x"), "R": ax(2, "r2")},
                                 "evidence": [{"text": top[0]["title"], "video": top[0]["id"]}, {"research": "r1"}, {"research": "r2"}],
                                 "titles": ["Título 1"], "production": {"automation": "4/5"}, "risks": "baixo"}],
              "plan": [{"when": "Dias 1-7", "what": "Publicar 3 vídeos", "success": "x"}], "limitations": ["Dados sintéticos de teste."],
              "sources": [{"label": "teste", "url": "https://example.org"}]}
        (runp / "analysis.json").write_text(json.dumps(an, ensure_ascii=False), encoding="utf-8")
        code, out = run(HERE / "check_analysis.py", "--run", runp, env=env)
        check("check_analysis sem erros", code == 0, out[-400:])
        code, out = run(HERE / "score.py", "--run", runp, env=env)
        check("score imprime veredito", code == 0 and any(v in out for v in ("GO", "TESTAR", "EVITAR")), out[-200:])
        code, out = run(HERE / "build_report.py", "--run", runp, env=env)
        html = (runp / "relatorio.html").read_text(encoding="utf-8") if (runp / "relatorio.html").exists() else ""
        check("relatório gerado", code == 0 and "__DATA__" in html and "Resultado por oportunidade" in html, out[-300:])
        check("relatório sem marcadores soltos", "__TITLE__" not in html and "/*__APP__*/" not in html)
        check("relatório sem a chave", "AIza" not in html)

    print(f"{len(OKS)} verificações OK" + (f", {len(FAIL)} FALHA(S):" if FAIL else ""))
    for f in FAIL:
        print("  FALHOU:", f)
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
