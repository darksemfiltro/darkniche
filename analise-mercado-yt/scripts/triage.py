"""Prepara um piloto de mercado antes da seleção humana; até 24 buscas (padrão), uma variante por recorte/idioma.

  python triage.py --run <pasta> --duration longform --estimate
  python triage.py --run <pasta> --duration longform [--search-budget 24]
  python scan.py --run <pasta>/triage --triage
  python metrics.py --run <pasta>/triage

Não chama rede por si só. Não aprova o plano de aprofundamento. O teto padrão é 24 buscas; com mais recortes ou
idiomas, o usuário escolhe um teto maior (--search-budget, no máximo 60) depois de ver a estimativa.
O piloto usa o modo do plano (`defaults.mode`): api (filtra região, idioma e data) ou ytdlp (0 buscas; sem chave, sem
data nem inscritos, e as métricas de frescor e de tamanho de canal ficam sem medição). Plano sem modo: api se há chave.
"""
from __future__ import annotations

import argparse
import copy
from pathlib import Path

from common import load_env, read_json, set_run, write_json
from plan_tools import validate_plan
from selection import estimate_plan, scope_hash

MAX_PILOT = 60


def prepare(run, duration="longform", budget=24, estimate=False):
    if not 1 <= budget <= MAX_PILOT:
        raise ValueError(f"A triagem admite teto de 1–{MAX_PILOT} buscas (padrão 24); o aprofundamento passa pela seleção.")
    run = Path(run)
    source = read_json(run / "plan.json", {})
    validate_plan(source)
    if not source.get("cells"):
        raise ValueError("Escreva as hipóteses iniciais em plan.json para testar no mercado.")
    # O modo do plano manda (init_run.py grava api com chave e ytdlp sem). Só quando o plano não diz, decide a chave.
    declared = (source.get("defaults") or {}).get("mode")
    mode = declared if declared in ("api", "ytdlp") else "api" if load_env(run).get("YT_API_KEY") else "ytdlp"
    plan = copy.deepcopy(source)
    plan["title"] = "Triagem de mercado · " + plan.get("title", run.name)
    plan.setdefault("defaults", {}).update(mode=mode, probe_mode=mode, duration=duration, pages=1)
    plan["probes"] = []
    plan["competitors"] = []
    plan["collection_limits"] = {"max_channels": 6, "uploads_per_channel": 50}
    for cell in plan["cells"]:
        cell["mode"] = mode
        cell["filters"] = {**cell.get("filters", {}), "duration": duration, "pages": 1}
        cell["filters_lang"] = {l: {**f, "duration": duration, "pages": 1} for l, f in cell.get("filters_lang", {}).items()}
        cell["queries"] = {l: q[0] if isinstance(q, list) else q for l, q in cell["queries"].items()}
    validate_plan(plan)
    cost = estimate_plan(plan)
    max_units = max(100, 2 * budget + 52)
    if cost["searches"] > budget or cost["units"] > max_units:
        raise ValueError(f"Triagem teria {cost['searches']} buscas/{cost['units']} gerais. Reduza hipóteses/idiomas, use a faixa de duração da referência ou escolha um teto maior (--search-budget até {MAX_PILOT}) com o usuário. Não descarte idiomas silenciosamente.")
    if not estimate:
        pilot = run / "triage"
        write_json(pilot / "plan.json", plan)
        write_json(pilot / "source.json", {"scope_hash": scope_hash(source), "estimate": cost})
        write_json(pilot / "selection.json", {"status": "selected", "stage": "triage", "scope_hash": scope_hash(plan),
                                             "max_searches": budget, "max_units": max_units, "mode": mode,
                                             "note": "Piloto limitado autorizado pelo fluxo; não é a escolha humana de aprofundamento."})
    return cost


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True, type=Path)
    ap.add_argument("--duration", choices=["medium", "long", "longform"], default="longform")
    ap.add_argument("--search-budget", type=int, default=24)
    ap.add_argument("--estimate", action="store_true")
    args = ap.parse_args()
    set_run(args.run)
    try:
        cost = prepare(args.run, args.duration, args.search_budget, args.estimate)
        print(f"Estimativa sem cache (não é consumo realizado): {cost}")
        print("Nenhuma chamada de rede foi feita por triage.py. A coleta é scan.py --run <pasta>/triage --triage; métricas usam <pasta>/triage; selection.py usa a pasta principal.")
    except (ValueError, KeyError, TypeError) as e:
        ap.exit(2, f"{e}\n")


if __name__ == "__main__":
    main()
