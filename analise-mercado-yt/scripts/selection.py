"""Pré-seleção sem rede. propose mostra candidatos; select registra a escolha humana; approve aprova o plano como está.

  python selection.py propose --run <pasta>
  python selection.py select --run <pasta> --cells acidentes,historias --langs fr --probes titulo1
  python selection.py approve --run <pasta> [--search-budget 60 --unit-budget 500]

O agente só deve executar select ou approve após receber a resposta do usuário. Não é autenticação:
é um checkpoint persistente que impede scan acidental e invalida mudanças de coleta.
Use select depois de uma triagem em que o agente propôs os recortes; use approve quando o usuário já nomeou o escopo.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from common import read_json, set_run, write_json
from plan_tools import cell_filters, probe_filters, region_for, signature, validate_plan, raw_is_current


def scope_hash(plan):
    """Filtros locais e texto editorial podem mudar sem autorizar novas buscas."""
    entries = []
    defaults = plan.get("defaults", {})
    for group in ("cells", "probes"):
        for cell in plan.get(group, []):
            for lang, queries in cell.get("queries", {}).items():
                queries = queries if isinstance(queries, list) else [queries]
                mode = defaults.get("probe_mode", "ytdlp") if group == "probes" else cell.get("mode", defaults.get("mode", "api"))
                filters = probe_filters(defaults, cell) if group == "probes" else cell_filters(defaults, cell, lang)
                for query in queries:
                    entries.append((group, cell["id"], lang, signature(query, lang, region_for(plan, lang), filters, mode)))
    spec = {"queries": sorted(entries), "reference": plan.get("reference"),
            "competitors": plan.get("competitors", []), "limits": plan.get("collection_limits", {})}
    return hashlib.sha256(json.dumps(spec, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def estimate_plan(plan):
    """Matriz + sondagens, sem cache, sem rede. Não inclui referência/perfis/comentários."""
    from scan import cost_of
    total = {"searches": 0, "units": 0, "requests": 0}
    defaults = plan.get("defaults", {})
    for group in ("cells", "probes"):
        for cell in plan.get(group, []):
            for lang, queries in cell.get("queries", {}).items():
                queries = queries if isinstance(queries, list) else [queries]
                mode = defaults.get("probe_mode", "ytdlp") if group == "probes" else cell.get("mode", defaults.get("mode", "api"))
                modes = ["api", "ytdlp"] if mode == "both" else [mode]
                for query in queries:
                    for m in modes:
                        c, d = ({"filters": probe_filters(defaults, cell)}, {}) if group == "probes" else (cell, defaults)
                        cost = cost_of((c, lang, query, m, None), d)
                        for k in total:
                            total[k] += cost[k]
    return total


def require_selection(run, plan, mode=None, probes=False, triage=False):
    state = read_json(Path(run) / "selection.json", {})
    if (state.get("stage") == "triage") != triage:
        raise ValueError("Plano de triagem exige --triage; aprofundamento exige uma seleção humana distinta.")
    if state.get("status") != "selected" or state.get("scope_hash") != scope_hash(plan):
        raise ValueError("Aprovação pendente ou escopo alterado. Mostre o custo (scan.py --estimate) e aguarde o ok do usuário; depois rode selection.py approve (escopo que ele nomeou) ou select (recortes que ele escolheu). --estimate continua livre.")
    if mode is not None:
        defaults = plan.get("defaults", {})
        expected = [defaults.get("probe_mode", "ytdlp")] if probes else [c.get("mode", defaults.get("mode", "api")) for c in plan.get("cells", [])]
        if any(m != mode for m in expected):
            raise ValueError("--mode altera o modo selecionado. Ajuste o plano, mostre a nova estimativa e registre a seleção novamente.")
    return state


def require_triage(run, plan):
    run = Path(run)
    if run.name == "triage" and (run / "source.json").exists() and (run.parent / "plan.json").exists():
        raise ValueError(f"Pasta errada para selection.py: use --run '{run.parent}'. scan --triage e metrics usam '{run}'; propose/select usam a pasta principal.")
    pilot = read_json(run / "triage" / "source.json", {})
    measured = read_json(run / "triage" / "data" / "cells.json", [])
    if not pilot:
        raise ValueError("Não há triagem nesta pasta. Rode triage.py, scan.py --run <pasta>/triage --triage e metrics.py --run <pasta>/triage; "
                         "se o usuário já nomeou nichos e idiomas, mostre a estimativa e use selection.py approve.")
    if pilot.get("scope_hash") != scope_hash(plan):
        raise ValueError("O plano mudou depois da triagem (consultas, filtros, idiomas, modo ou limites). Rode triage.py de novo para refazer o piloto.")
    if not measured:
        raise ValueError("A triagem não tem métricas. Rode metrics.py --run <pasta>/triage antes de propor.")
    pilot_plan = read_json(run / "triage" / "plan.json", {})
    require_selection(run / "triage", pilot_plan, triage=True)
    from scan import jobs
    if jobs(pilot_plan, run / "triage", "api", None, None):
        raise ValueError("Triagem incompleta: retome o piloto antes de selecionar o aprofundamento.")
    return measured


def propose(run):
    run = Path(run)
    plan = read_json(run / "plan.json", {})
    validate_plan(plan)
    if not plan.get("cells"):
        raise ValueError("Preencha os candidatos em plan.json antes de apresentar a proposta.")
    measured = require_triage(run, plan)
    write_json(run / "proposal.json", plan)
    write_json(run / "selection.json", {"status": "pending", "scope_hash": scope_hash(plan)})
    print("PROPOSTA — triagem de mercado disponível. Ranking exige leitura crítica; amostra preliminar não comprova oceano azul.")
    for cell in sorted(plan["cells"], key=lambda c: c.get("priority", 999)):
        one = {**plan, "cells": [cell], "probes": []}
        cost = estimate_plan(one)
        qs = [f"{lang}: {q}" for lang, q in cell.get("queries", {}).items()]
        print(f"\n{cell.get('priority', '?')}. {cell['id']} — {cell.get('label', cell['id'])}")
        print(f"   Nicho/subnicho: {cell.get('niche', '?')} / {cell.get('subniche', '?')} · ângulo: {cell.get('lens', '?')}")
        print(f"   Hipótese: {cell.get('rationale', 'Ainda não justificada; o agente deve explicar antes da escolha.')}")
        print(f"   Idiomas: {', '.join(cell.get('queries', {}))}; buscas: {cost['searches']}; gerais: até {cost['units']}")
        print("   Consultas: " + " | ".join(qs))
        for row in measured:
            if row.get("id") == cell["id"]:
                m = row.get("m", {})
                au = row.get("auto", {})
                print(f"   Triagem {row.get('lang')}: long-form={m.get('n_long')}, views/dia (mediana)={m.get('vpd_p50')}, mediana de views={m.get('med')}, "
                      f"canais ativos={m.get('active')} (efetivos {m.get('n_eff')}), pureza={m.get('lang_purity')}, evidência={au.get('evidence', '?')}"
                      + (f", flags={','.join(au.get('flags', []))}" if au.get("flags") else ""))
    print("\nMercados: " + ", ".join(f"{l['lang']}/{l.get('region', '?')}" for l in plan.get("languages", [])))
    print("Sondagens opcionais: " + ", ".join(p["id"] for p in plan.get("probes", [])))
    print("Escolha IDs de recortes, idiomas/regiões e sondagens. Nenhuma coleta adicional foi iniciada por este comando.")


def select(run, cells, langs, probes=(), search_budget=60, unit_budget=500, dry_run=False):
    run = Path(run)
    source = read_json(run / "proposal.json") or read_json(run / "plan.json", {})
    validate_plan(source)
    require_triage(run, source)
    cells, langs, probes = set(cells), set(langs), set(probes)
    if not cells or not langs:
        raise ValueError("Selecione pelo menos um recorte e um idioma explicitamente.")
    if not cells <= {c["id"] for c in source.get("cells", [])}:
        raise ValueError("Recorte desconhecido na proposta.")
    if not langs <= {l["lang"] for l in source.get("languages", [])}:
        raise ValueError("Idioma desconhecido na proposta; ajuste também a região antes da seleção.")
    if not probes <= {p["id"] for p in source.get("probes", [])}:
        raise ValueError("Sondagem desconhecida na proposta.")
    if search_budget < 0 or unit_budget < 0:
        raise ValueError("Orçamentos não podem ser negativos.")
    plan = copy.deepcopy(source)
    plan["languages"] = [l for l in plan.get("languages", []) if l["lang"] in langs]
    for group, chosen in (("cells", cells), ("probes", probes)):
        plan[group] = [c for c in plan.get(group, []) if c["id"] in chosen]
        for c in plan[group]:
            c["queries"] = {l: q for l, q in c["queries"].items() if l in langs}
            if not c["queries"]:
                raise ValueError(f"{c['id']}: sem consulta para os idiomas escolhidos.")
    if any(not any(l in c["queries"] for c in plan["cells"]) for l in langs):
        raise ValueError("Um idioma escolhido não tem consultas de mercado.")
    validate_plan(plan)
    cost = estimate_plan(plan)
    if cost["searches"] > search_budget or cost["units"] > unit_budget:
        raise ValueError(f"Plano excede o teto escolhido: {cost}. Reduza recortes/idiomas/sondagens ou escolha outro teto.")
    state = {"status": "selected", "selected_at": datetime.now(timezone.utc).isoformat(),
             "cells": sorted(cells), "langs": sorted(langs), "probes": sorted(probes),
             "scope_hash": scope_hash(plan), "scan_estimate": cost,
             "scan_budget": {"searches": search_budget, "units": unit_budget},
             "note": "Escolha explícita registrada pelo operador/agente após resposta humana. Estimativa exclui referência, perfis, comentários e retries."}
    if not dry_run:
        if not (run / "proposal.json").exists():  # select sem propose sobrescrevia o plano e perdia os candidatos
            write_json(run / "proposal.json", source)
        write_json(run / "plan.json", plan)
        write_json(run / "selection.json", state)
        # Reusar resultados idênticos do piloto sem depender do timestamp móvel de publishedAfter.
        for f in (run / "triage" / "raw" / "search").glob("*.json"):
            data = read_json(f, {})
            if raw_is_current(data, plan):
                target = run / "raw" / "search" / f.name
                if not target.exists():
                    write_json(target, data)
    return state


def approve(run, search_budget=60, unit_budget=500, dry_run=False):
    """Registra o ok do usuário ao plano exatamente como está, sem triagem.

    Para quando o próprio usuário nomeou nicho(s) e idiomas ("analise finanças pessoais em PT e EN"): não há candidatos
    para escolher, só custo para aprovar. O checkpoint continua valendo: se o plano mudar depois, o scan recusa."""
    run = Path(run)
    plan = read_json(run / "plan.json", {})
    validate_plan(plan)
    if not plan.get("cells"):
        raise ValueError("Preencha as células em plan.json antes de aprovar.")
    if search_budget < 0 or unit_budget < 0:
        raise ValueError("Orçamentos não podem ser negativos.")
    cost = estimate_plan(plan)
    if cost["searches"] > search_budget or cost["units"] > unit_budget:
        raise ValueError(f"Plano excede o teto: {cost}. Reduza o escopo ou aprove um teto maior com o usuário (--search-budget / --unit-budget).")
    state = {"status": "selected", "stage": "approved", "selected_at": datetime.now(timezone.utc).isoformat(),
             "cells": sorted(c["id"] for c in plan["cells"]), "langs": sorted({l for c in plan["cells"] for l in c.get("queries", {})}),
             "probes": sorted(p["id"] for p in plan.get("probes", [])),
             "scope_hash": scope_hash(plan), "scan_estimate": cost,
             "scan_budget": {"searches": search_budget, "units": unit_budget},
             "note": "Aprovação do plano como está, sobre escopo nomeado pelo usuário. Estimativa exclui referência, perfis, comentários e retries."}
    if not dry_run:
        write_json(run / "selection.json", state)
    return state


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action", choices=["propose", "select", "approve"])
    ap.add_argument("--run", required=True, type=Path)
    ap.add_argument("--cells", default="")
    ap.add_argument("--langs", default="")
    ap.add_argument("--probes", default="")
    ap.add_argument("--search-budget", type=int, default=60)
    ap.add_argument("--unit-budget", type=int, default=500)
    args = ap.parse_args()
    set_run(args.run)
    split = lambda s: [x.strip() for x in s.split(",") if x.strip()]
    try:
        if args.action == "propose":
            propose(args.run)
        elif args.action == "approve":
            print(json.dumps(approve(args.run, args.search_budget, args.unit_budget), ensure_ascii=False, indent=2))
        else:
            print(json.dumps(select(args.run, split(args.cells), split(args.langs), split(args.probes), args.search_budget, args.unit_budget), ensure_ascii=False, indent=2))
    except (ValueError, TypeError, KeyError) as e:
        ap.exit(2, f"{e}\n")


if __name__ == "__main__":
    main()
