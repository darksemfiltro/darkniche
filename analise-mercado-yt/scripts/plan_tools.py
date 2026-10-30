"""Identidade das coletas: retomar só quando consulta, filtros, modo e região coincidem."""
from __future__ import annotations

import hashlib
import json
import re


def cell_filters(defaults, cell, lang):
    return {**(defaults or {}), **(cell.get("filters") or {}), **((cell.get("filters_lang") or {}).get(lang) or {})}


def region_for(plan, lang):
    return next((x.get("region") for x in plan.get("languages") or [] if x["lang"] == lang), None)


def signature(query, lang, region, filters, mode):
    # Somente parâmetros de coleta. keywords/exclude são filtros locais e não gastam API novamente.
    defaults = {"after_days": 365, "duration": "any", "order": "viewCount", "pages": 1,
                "category": None, "ytdlp_n": 40, "enrich": True}
    effective = {k: filters.get(k, v) for k, v in defaults.items()}
    spec = {"query": query, "lang": lang, "region": region, "filters": effective, "mode": mode}
    return hashlib.sha256(json.dumps(spec, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def probe_filters(defaults, probe):
    return {**defaults, "after_days": defaults.get("probe_after_days", 730),
            "duration": probe.get("duration", "any"), "ytdlp_n": 15, "pages": 1}


def raw_is_current(data, plan, probe=False):
    group = "probes" if probe else "cells"
    name = "probe" if probe else "cell"
    cell = next((c for c in plan.get(group, []) if c["id"] == data.get(name)), None)
    if not cell:
        return False
    lang = data.get("lang")
    queries = cell.get("queries", {}).get(lang, [])
    queries = queries if isinstance(queries, list) else [queries]
    if data.get("query") not in queries:
        return False
    flt = probe_filters(plan.get("defaults", {}), cell) if probe else cell_filters(plan.get("defaults", {}), cell, lang)
    return data.get("signature") == signature(data["query"], lang, region_for(plan, lang), flt, data.get("mode"))


def validate_plan(plan):
    """Falhar antes de gastar quota ou usar IDs como caminhos."""
    declared = {l.get("lang") for l in plan.get("languages") or []}
    for group in ("cells", "probes"):
        ids = set()
        for c in plan.get(group) or []:
            cid = c.get("id", "")
            if not re.fullmatch(r"[A-Za-z0-9_-]+", cid) or cid in ids:
                raise ValueError(f"{group}: id inválido ou repetido: {cid!r}")
            ids.add(cid)
            if not c.get("queries"):
                raise ValueError(f"{group}/{cid}: sem consultas (queries): a coleta não teria o que buscar")
            for lang, qs in c["queries"].items():
                if not re.fullmatch(r"[A-Za-z][A-Za-z0-9-]*", lang):
                    raise ValueError(f"idioma inválido: {lang!r}")
                if declared and lang not in declared:
                    # "pt-BR" nas consultas passava e voltava com zero vídeos, parecendo falta de demanda
                    raise ValueError(f"{group}/{cid}: o idioma {lang!r} das consultas não está em plan.languages "
                                     f"({', '.join(sorted(declared))}). Use o código curto (pt, não pt-BR) e declare o idioma em languages.")
                if group == "probes" and not isinstance(qs, str):
                    raise ValueError(f"sondagem {cid}/{lang}: use uma consulta em texto")
                if not isinstance(qs, (str, list)) or not qs or any(not isinstance(q, str) or not q.strip() for q in (qs if isinstance(qs, list) else [qs])):
                    raise ValueError(f"consultas inválidas: {cid}/{lang}")
                f = probe_filters(plan.get("defaults", {}), c) if group == "probes" else cell_filters(plan.get("defaults", {}), c, lang)
                if f.get("duration", "any") not in ("any", "short", "medium", "long", "longform"):
                    raise ValueError(f"duração inválida: {cid}/{lang}")
                if int(f.get("pages", 1)) < 1 or int(f.get("after_days", 365)) < 0 or int(f.get("ytdlp_n", 40)) < 1:
                    raise ValueError(f"filtros numéricos inválidos: {cid}/{lang}")
            mode = c.get("mode", plan.get("defaults", {}).get("mode", "api"))
            if mode not in ("api", "ytdlp", "both"):
                raise ValueError(f"modo inválido: {mode}")
