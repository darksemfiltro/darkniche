"""Roda a matriz nicho × idioma e as sondagens de transposição de títulos definidas em plan.json.

  python scripts/scan.py --run <pasta-da-analise> [--mode api|ytdlp|both] [--estimate] [--only celula1,celula2] [--langs pt,es]
  python scripts/scan.py --run <pasta> --probes [--mode ytdlp|api]

- api   : search.list com filtros (idioma, região, data, duração, ordem) + enriquecimento. 1 busca/página + até 2 unidades gerais/página.
- ytdlp : busca do YouTube via yt-dlp (sem cota) com filtros de ordem/data/duração; enriquece com videos.list
          (1 unidade por 50 vídeos) quando há chave, para ter data, idioma e inscritos.
- both  : as duas; a API dá precisão regional, o yt-dlp dá amplitude.
Retoma de onde parou: pula combinações já salvas (e o --estimate só conta o que falta). Para no primeiro QUOTA
e mostra o que falta.

Filtros: plan.defaults < cell.filters < cell.filters_lang[<idioma>]. Chaves: after_days, duration
(any | short | medium | long | longform = medium + long em duas buscas, sem Shorts), order, pages, category.
Use filters_lang para corrigir um idioma sem criar outra célula (ex.: {"fr": {"duration": "longform"}}).
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from math import ceil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_env, log, quota_used, read_json, set_run, stamp, write_json
import yt_api
from plan_tools import cell_filters, region_for, signature, probe_filters, validate_plan

try:
    import ytdlp_tools
except Exception:  # yt-dlp ausente não impede o modo api
    ytdlp_tools = None

UPLOAD = {30: "month", 7: "week", 1: "today"}


def enrich_ytdlp(rows):
    """Completa linhas do yt-dlp com data, idioma, duração e dados do canal via API (barato)."""
    if not rows or not load_env().get("YT_API_KEY"):
        return rows
    vs = {v["id"]: v for v in yt_api.videos([r["id"] for r in rows])}
    chs = {c["id"]: c for c in yt_api.channels([v["snippet"]["channelId"] for v in vs.values()])}
    out = []
    for r in rows:
        v = vs.get(r["id"])
        if not v:
            continue
        row = yt_api.video_row(v, chs.get(v["snippet"]["channelId"]))
        row["source"] = "ytdlp"
        out.append(row)
    return out


def run_query(q, lang, region, d, mode):
    """Uma consulta. duration "longform" = médio (4–20 min) + longo (> 20 min) em duas buscas, para que os Shorts
    não ocupem metade dos 50 resultados numa análise de long-form."""
    if d.get("duration") == "longform":
        seen, out, total = set(), yt_api.Rows(), None
        for dur in ("medium", "long"):
            part = run_query(q, lang, region, {**d, "duration": dur}, mode)
            t = (getattr(part, "meta", None) or {}).get("total_results")
            if t is not None:  # faixas médio e longo não se sobrepõem: a oferta é a soma
                total = (total or 0) + t
            for r in part:
                if r["id"] not in seen:
                    seen.add(r["id"]); out.append(r)
        if total is not None:
            out.meta["total_results"] = total
        return out
    after = int(d.get("after_days", 365))
    if mode == "api":
        return yt_api.search(q, lang, region, int(d.get("pages", 1)), after, d.get("duration", "any"), d.get("order", "viewCount"), d.get("category"))
    if ytdlp_tools is None or not ytdlp_tools.YTDLP:
        raise SystemExit("modo ytdlp pedido, mas o yt-dlp não está instalado (pip install -U yt-dlp)")
    # A UI não tem filtro de 2 anos: usar year descartava todo o segundo ano.
    upload = "any" if after == 0 or after > 365 else "year" if after > 30 else UPLOAD.get(after, "month")
    sort = {"viewCount": "views", "date": "date", "relevance": "relevance"}.get(d.get("order", "viewCount"), "views")
    rows = ytdlp_tools.search(q, int(d.get("ytdlp_n", 40)), sort, upload, d.get("duration", "any"), hl=lang)
    rows = enrich_ytdlp(rows) if d.get("enrich", True) else rows
    # Datas exatas só existem após enriquecimento; sem elas a faixa da UI é aproximada.
    if after and d.get("enrich", True):
        from common import parse_dt, days_ago_iso
        cutoff = parse_dt(days_ago_iso(after))
        rows = [r for r in rows if not r.get("published") or (parse_dt(r["published"]) and parse_dt(r["published"]) >= cutoff)]
    return rows


def jobs(plan, run, mode, only, langs, force_mode=False, refresh=False):
    """Consultas que ainda faltam (as já salvas são puladas)."""
    out = []
    for c in plan["cells"]:
        if only and c["id"] not in only:
            continue
        cmode = mode if force_mode else c.get("mode", mode)
        for l, qs in c["queries"].items():
            if langs and l not in langs:
                continue
            modes = ["api", "ytdlp"] if cmode == "both" else [cmode]
            for qi, q in enumerate(qs if isinstance(qs, list) else [qs]):
                for m in modes:
                    f = run / "raw" / "search" / f"{c['id']}__{l}.{m}{'' if qi == 0 else '.' + str(qi)}.json"
                    saved = read_json(f, {})
                    sig = signature(q, l, region_for(plan, l), cell_filters(plan.get("defaults", {}), c, l), m)
                    if refresh or saved.get("signature") != sig:
                        out.append((c, l, q, m, f))
    return out


def cost_of(job, d):
    c, l, q, m, f = job
    flt = cell_filters(d, c, l)
    k = 2 if flt.get("duration") == "longform" else 1
    if m == "api":
        searches = k * int(flt.get("pages", 1))
        return {"searches": searches, "units": 2 * searches, "requests": 3 * searches}
    units = 2 * ceil(int(flt.get("ytdlp_n", 40)) / 50) * k if flt.get("enrich", True) and load_env().get("YT_API_KEY") else 0
    return {"searches": 0, "units": units, "requests": units}


def estimate_cost(todo, defaults):
    estimates = [cost_of(j, defaults) for j in todo]
    return {k: sum(e[k] for e in estimates) for k in ("searches", "units", "requests")}


def log_estimate(cost):
    status = yt_api.quota_status()
    left = status["remaining_local"]
    budget = status["budget_local"]
    blocked = any(cost[k] and not budget[k] for k in ("searches", "units"))
    days = max((ceil(cost[k] / budget[k]) if budget[k] else 0) for k in ("searches", "units"))
    horizon = "bloqueado por orçamento zero" if blocked else f"~{days} dia(s) de orçamento local"
    log(f"estimativa sem cache: até {cost['searches']} buscas + {cost['units']} unidades gerais ({cost['requests']} chamadas HTTP); {horizon}")
    log(f"restante LOCAL hoje: {left['searches']} buscas + {left['units']} unidades gerais; saldo Google desconhecido")
    if any(cost[k] > left[k] for k in ("searches", "units")):
        log("AVISO: coleta excede o orçamento local de hoje; reduza o escopo selecionado ou retome após a virada.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True)
    ap.add_argument("--mode", choices=["api", "ytdlp", "both"])
    ap.add_argument("--refresh", action="store_true", help="recoleta os arquivos de resultado (o cache HTTP continua valendo)")
    ap.add_argument("--only")
    ap.add_argument("--langs")
    ap.add_argument("--estimate", action="store_true")
    ap.add_argument("--probes", action="store_true", help="roda as sondagens de títulos (plan.probes)")
    ap.add_argument("--triage", action="store_true", help="executa somente um plano de triagem limitado criado por triage.py")
    a = ap.parse_args()
    run = Path(a.run)
    set_run(run)
    plan = read_json(run / "plan.json")
    if not plan:
        raise SystemExit(f"plan.json não encontrado em {run}")
    load_env(run)
    try:
        validate_plan(plan)
    except ValueError as e:
        raise SystemExit(str(e))
    d = plan.get("defaults", {})
    # Estimar é livre; coletar exige uma escolha persistida e ainda correspondente ao plano.
    if not a.estimate:
        from selection import require_selection
        try:
            require_selection(run, plan, mode=a.mode, probes=a.probes, triage=a.triage)
            if a.triage:
                from selection import estimate_plan
                triage_cost = estimate_plan(plan)
                cap = read_json(run / "selection.json", {})
                cap_s, cap_u = int(cap.get("max_searches", 24)), int(cap.get("max_units", 100))
                if a.refresh or a.probes or triage_cost["searches"] > cap_s or triage_cost["units"] > cap_u:
                    raise ValueError(f"Triagem limitada a {cap_s} buscas/{cap_u} gerais, sem refresh ou sondagens; escolha humana necessária para expandir.")
        except ValueError as e:
            log(str(e))
            sys.exit(4)
    langs_cfg = {l["lang"]: l for l in plan.get("languages", [])}
    only = set(a.only.split(",")) if a.only else None
    langs = set(a.langs.split(",")) if a.langs else None

    if a.probes:
        mode = a.mode or d.get("probe_mode", "ytdlp")
        if mode not in ("api", "ytdlp"):
            raise SystemExit("sondagens aceitam --mode api ou ytdlp")
        todo = [(p, l, q) for p in plan.get("probes", []) for l, q in p["queries"].items()
                if (not only or p['id'] in only) and (not langs or l in langs) and (a.refresh or read_json(run / "raw" / "probes" / f"{p['id']}__{l}.json", {}).get("signature") != signature(q, l, region_for(plan, l), probe_filters(d, p), mode))]
        estimates = [cost_of(({"filters": probe_filters(d, p)}, l, q, mode, None), {}) for p, l, q in todo]
        log(f"faltam {len(todo)} sondagens · modo {mode}")
        log_estimate({k: sum(e[k] for e in estimates) for k in ("searches", "units", "requests")})
        if a.estimate:
            return
        for p, l, q in todo:
            f = run / "raw" / "probes" / f"{p['id']}__{l}.json"
            flt = probe_filters(d, p)
            try:
                rows = run_query(q, l, region_for(plan, l), flt, mode)
            except yt_api.QuotaExceeded as e:
                log("QUOTA:", e); sys.exit(3)
            write_json(f, {"probe": p["id"], "lang": l, "query": q, "mode": mode, "filters": flt, "fetched_at": stamp(),
                           "signature": signature(q, l, region_for(plan, l), flt, mode), "rows": rows[:15]})
            log(f"sonda {p['id']:<14} {l} {len(rows):>3}")
        return

    mode = a.mode or d.get("mode", "api")
    todo = jobs(plan, run, mode, only, langs, force_mode=bool(a.mode), refresh=a.refresh)
    cost = estimate_cost(todo, d)
    n_api = sum(1 for j in todo if j[3] == "api")
    log(f"faltam {len(todo)} consultas ({n_api} pela API)")
    log_estimate(cost)
    if a.estimate:
        return
    pending, failed = [], []
    for i, (c, l, q, m, f) in enumerate(todo):
        flt = cell_filters(d, c, l)
        try:
            rows = run_query(q, l, langs_cfg.get(l, {}).get("region"), flt, m)
        except yt_api.QuotaExceeded as e:
            pending = [f"{x[0]['id']}/{x[1]}/{x[3]}" for x in todo[i:]]
            log("QUOTA:", str(e)[:200])
            log(f"faltam {len(pending)}:", ", ".join(pending))
            log("Para seguir hoje sem gastar buscas: ponha as consultas que faltam em mode ytdlp no plano e registre a aprovação de novo "
                "(selection.py approve; custa só unidades gerais do enriquecimento). Ou retome depois da virada da cota (meia-noite do Pacífico).")
            sys.exit(3)
        except RuntimeError as e:
            log("erro", c["id"], l, m, e)
            failed.append(f"{c['id']}/{l}/{m}")
            continue
        write_json(f, {"cell": c["id"], "lang": l, "query": q, "mode": m, "filters": flt, "fetched_at": stamp(),
                       "meta": dict(getattr(rows, "meta", None) or {}),
                       "signature": signature(q, l, region_for(plan, l), flt, m), "rows": list(rows)})
        log(f"{c['id']:<18} {l:<3} {m:<5} {len(rows):>3} vídeos")
    log(f"fim · cota hoje: {quota_used()}")
    if failed:
        log("COLETA INCOMPLETA:", ", ".join(failed))
        sys.exit(2)


if __name__ == "__main__":
    main()
