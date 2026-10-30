"""Leitura descritiva dos dados existentes, sem IA, novas buscas ou promessa estratégica."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE if (_HERE / "common.py").exists() else _HERE.parents[1] / "scripts"))  # extras/colab -> ../../scripts
from common import read_json, write_json


def review(plan, rows):
    candidates = []
    for index, cell in enumerate(plan["cells"]):
        observed = [r for r in rows if r["id"] == cell["id"]]
        markets = []
        links = []
        for row in observed:
            m = row["m"]
            weak = m.get("n_long", 0) < 5 or m.get("lang_purity", 0) < .5
            why = (f"{m.get('n_long', 0)} vídeos long-form nativos; mediana {m.get('med', 0):,} views; "
                   f"pureza {m.get('lang_purity', 0):.0%}; {m.get('active', 0)} canais ativos na amostra. "
                   "Amostra insuficiente/contaminada." if weak else
                   f"{m.get('n_long', 0)} vídeos long-form nativos; mediana {m.get('med', 0):,} views; "
                   f"pureza {m.get('lang_purity', 0):.0%}; {m.get('active', 0)} canais ativos na amostra. Não mede o mercado inteiro.")
            markets.append({"lang": row["lang"], "verdict": "inconclusivo" if weak else "dados descritivos", "why": why})
            links.extend({"video": v["id"]} for v in m.get("top", [])[:2])
        candidates.append({"id": cell["id"], "priority": index + 1, "status": "inconclusivo",
                           "rationale": "Ordem original de exibição, sem ranking estratégico. " + " | ".join(f"{m['lang']}: {m['why']}" for m in markets),
                           "evidence": links, "markets": markets})
    return {"mode": "technical", "summary": "SEM IA: estatísticas do piloto existente. A ordem não é recomendação de nicho. Fit cultural, formato, produção e aderência das hipóteses à referência não foram avaliados.", "candidates": candidates}


def analysis(run):
    """Filtra a fotografia existente pelo subconjunto escolhido, sem fabricar oportunidades/notas."""
    run = Path(run)
    plan = read_json(run / "plan.json")
    ids = {c["id"] for c in plan["cells"]}
    langs = {l["lang"] for l in plan["languages"]}
    rows = read_json(run / "data/cells.json") or read_json(run / "triage/data/cells.json", [])
    rows = [r for r in rows if r["id"] in ids and r["lang"] in langs]
    if not rows:
        raise ValueError("Não há métricas existentes para a seleção; modo dados não faz novas buscas.")
    write_json(run / "data/cells.json", rows)
    if not (run / "data/channels.json").exists():
        write_json(run / "data/channels.json", read_json(run / "triage/data/channels.json", []))
    findings = [{"title": f"{r.get('label', r['id'])} · {r['lang']}",
                 "text": f"{r['m']['n_long']} long-form nativos; mediana {r['m']['med']:,} views; {r['m']['active']} canais ativos na amostra; pureza {r['m']['lang_purity']:.0%}."} for r in rows]
    value = {"analysis_mode": "technical", "meta": {"analysis_mode": "technical", "stamp": "DADOS · SEM IA"},
             "summary": {"lead": "Relatório técnico dos dados coletados. Não contém recomendação estratégica nem ranking de oportunidades.", "findings": findings},
             "method": {"scan": "Fotografia existente, filtrada pelos recortes e idiomas selecionados; sem novas buscas nesta etapa.",
                        "fit": "Não avaliado", "format": "Não inspecionado", "notes": ["Views e canais são da amostra de busca, não de um censo de mercado."]},
             "opportunities": [], "limitations": ["Sem modelo de IA: sem avaliação estratégica, fit cultural ou gramática visual.",
                  "As hipóteses existentes são preservadas; podem ser genéricas e não representar a referência.",
                  "Idioma, ruído e notas automáticas são aproximações; confirme os vídeos pelos links antes de decidir.",
                  "Não há validação de oceano azul, receita, custo ou viabilidade de produção."]}
    write_json(run / "analysis.json", value)
    return value
