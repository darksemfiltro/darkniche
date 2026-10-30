"""Nota de oportunidade "oceano azul" + produção + receita + velocidade, com travas, incerteza, confiança e veredito.

  python scripts/score.py --run <pasta>          (lê analysis.json, grava analysis.scored.json e imprime o ranking)

Cada oportunidade em analysis.json traz `scores` com eixos 1–5 (v), justificativa (why) e se foi medido (measured):
  D demanda · L lacuna de oferta · F fit cultural · G formato subutilizado     → Oceano (O)
  A automação · K custo de IA (5 = barato) · S fazer sozinho/localmente          → Produção (P)
  M receita · V velocidade (canais novos crescendo) · R risco (5 = muito arriscado, entra como trava)

  O = 0,30·D + 0,30·L + 0,25·F + 0,15·G
  P = (A + K + S) / 3
  Nota = 20 · (0,50·O + 0,25·P + 0,15·M + 0,10·V)            (0–100; pesos ajustáveis em analysis.weights)

Travas: D≤2 (oceano vazio), L≤2 (mar vermelho), F≤2 (não conversa com o mercado) e R≥4 limitam ao tier B;
R=5 vira C; incerteza > 50% dos eixos do oceano sem medição limita ao B e marca "validar".
Tiers: S ≥ 80 · A ≥ 70 · B ≥ 58 · C < 58.

Veredito (a resposta curta que o relatório mostra no topo):
  EVITAR  demanda vazia (D≤2), tema que não conversa com o mercado (F≤2), mar vermelho sem formato diferente (L≤2 e G≤3),
          risco proibitivo (R=5) ou tier C
  GO      tier S ou A, incerteza ≤ 50%, risco < 4 e confiança média ou alta
  TESTAR  o resto: promissor, mas falta medir ou o risco pede cuidado; `missing` diz o que medir primeiro
Confiança: alta = incerteza ≤ 25% e 10+ vídeos long-form nas células que sustentam a oportunidade; média = incerteza ≤ 50% e
5+; baixa = o resto. Sem os dados das células, vale só a incerteza.
`range` mostra a nota se cada eixo do oceano ainda julgado estivesse 1 ponto pior ou melhor.
"""
from __future__ import annotations

import argparse
import os
import sys
import math
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import read_json, write_json

W_DEFAULT = {"O": 0.50, "P": 0.25, "M": 0.15, "V": 0.10, "D": 0.30, "L": 0.30, "F": 0.25, "G": 0.15}
TIERS = [("S", 80), ("A", 70), ("B", 58), ("C", 0)]
ORDER = "SABC"
HOW = {"D": "mais uma consulta curta no idioma e leitura do topo (metodologia §2 e §15)",
       "L": "ler o topo, perfilar os canais dedicados ao nicho (profile_channels.py --extra) e conferir quem concorre de verdade",
       "F": "autocomplete e Wikipédia do país (signals.py) + pesquisa web local sobre consumo e regulação (pesquisa-web.md)",
       "G": "grade de thumbnails do topo (visual.py sheets) e classificação dos estilos (metodologia §12)"}


def val(scores, k, default=3):
    x = scores.get(k)
    if isinstance(x, dict):
        return float(x.get("v", default))
    return float(x) if x is not None else float(default)


def _total(w, D, L, F, G, A, K, S_, M, V):
    O = w["D"] * D + w["L"] * L + w["F"] * F + w["G"] * G
    P = (A + K + S_) / 3
    return O, P, round(20 * (w["O"] * O + w["P"] * P + w["M"] * M + w["V"] * V))


def _tier(total):
    return next(t for t, cut in TIERS if total >= cut)


def compute(op, w=None, cells=None):
    w = {**W_DEFAULT, **(w or {})}
    s = op.get("scores") or {}
    for k in "DLFGAKSMVR":
        raw = s.get(k)
        value = raw.get("v") if isinstance(raw, dict) else raw
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 1 <= value <= 5:
            raise ValueError(f"{op.get('id', '?')}.{k}: nota obrigatória entre 1 e 5")
        if k in "DLFG" and (not isinstance(raw, dict) or type(raw.get("measured")) is not bool):
            raise ValueError(f"{op.get('id', '?')}.{k}: measured precisa ser true/false")
    for group in ("OPMV", "DLFG"):
        if any(isinstance(w[k], bool) or not isinstance(w[k], (int, float)) or not math.isfinite(w[k]) or w[k] < 0 for k in group) or not math.isclose(sum(w[k] for k in group), 1, abs_tol=1e-6):
            raise ValueError(f"pesos de {group} precisam ser não negativos e somar 1")
    D, L, F, G = (val(s, k) for k in "DLFG")
    A, K, S_ = val(s, "A"), val(s, "K"), val(s, "S")
    M, V, R = val(s, "M"), val(s, "V"), val(s, "R", 2)
    O, P, total = _total(w, D, L, F, G, A, K, S_, M, V)  # arredonda antes do tier: o que se lê é o que vale
    tier = _tier(total)
    caps = []
    if D <= 2: caps.append(("B", "pouca demanda: oceano vazio"))
    if L <= 2: caps.append(("B", "muita oferta: mar vermelho"))
    if F <= 2: caps.append(("B", "tema não conversa com o mercado"))
    if R >= 4: caps.append(("B", "risco alto (política, saúde, jurídico ou plataforma)"))
    if R >= 5: caps.append(("C", "risco proibitivo"))
    measured = [k for k in "DLFG" if isinstance(s.get(k), dict) and s[k].get("measured")]
    u = round(1 - len(measured) / 4, 2)
    if u > 0.5: caps.append(("B", "incerteza alta: validar antes de produzir"))
    for cap, _ in caps:
        if ORDER.index(cap) > ORDER.index(tier):
            tier = cap

    # confiança: incerteza dos eixos do oceano + tamanho da amostra das células que sustentam a oportunidade
    n_long, parcial = None, False
    if cells:
        sup = [cells[c] for c in op.get("cells", []) if c in cells]
        ns = [c["m"]["n_long"] for c in sup]
        n_long = min(ns) if ns else None
        # sem data ou inscritos (modo sem chave) o ritmo, a porta aberta e o frescor ficam sem medição: o veredito não chega a GO
        parcial = any({"sem_datas", "sem_inscritos"} & set(c["m"].get("flags") or []) for c in sup)
    confidence ="alta" if u <= 0.25 and (n_long is None or n_long >= 10) else "média" if u <= 0.5 and (n_long is None or n_long >= 5) else "baixa"
    if parcial:
        confidence = "baixa"

    # veredito
    reasons = []
    if D <= 2: reasons.append("demanda vazia")
    if F <= 2: reasons.append("o tema não conversa com o mercado")
    if L <= 2 and G <= 3: reasons.append("mar vermelho sem formato diferente")
    if R >= 5: reasons.append("risco proibitivo")
    if tier == "C" and not reasons: reasons.append("nota abaixo de 58")
    if reasons:
        verdict = "EVITAR"
    elif tier in ("S", "A") and u <= 0.5 and R < 4 and confidence != "baixa":
        verdict = "GO"
        reasons.append(f"tier {tier} com evidência {confidence}")
    else:
        verdict = "TESTAR"
        if u > 0.5: reasons.append("a maior parte do oceano ainda é julgamento")
        if R >= 4: reasons.append("risco alto pede teste pequeno e cuidado com a plataforma")
        if tier == "B" and not caps: reasons.append("nota intermediária")
        if confidence == "baixa" and u <= 0.5:
            reasons.append("sem data ou inscritos nas células (modo sem chave): ritmo e porta aberta sem medição" if parcial else "amostra pequena nas células")
        if not reasons: reasons.append("promissor, falta confirmar")
    missing = [{"axis": k, "how": HOW[k]} for k in "DLFG" if k not in measured]

    # faixa da nota: eixos do oceano ainda julgados 1 ponto pior / melhor
    vals = dict(zip("DLFG", (D, L, F, G)))
    lo = {k: (max(1, v - 1) if k not in measured else v) for k, v in vals.items()}
    hi = {k: (min(5, v + 1) if k not in measured else v) for k, v in vals.items()}
    t_lo = _total(w, lo["D"], lo["L"], lo["F"], lo["G"], A, K, S_, M, V)[2]
    t_hi = _total(w, hi["D"], hi["L"], hi["F"], hi["G"], A, K, S_, M, V)[2]
    return {"O": round(O, 2), "P": round(P, 2), "total": total, "tier": tier,
            "caps": [r for _, r in caps], "uncertainty": u,
            "verdict": verdict, "confidence": confidence, "reasons": reasons, "missing": missing,
            "range": [t_lo, t_hi], "n_long_min": n_long,
            "blue_ocean": D >= 3 and L >= 4 and F >= 3 and G >= 3 and R < 4 and u <= 0.5}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True)
    a = ap.parse_args()
    run = Path(a.run)
    an = read_json(run / "analysis.json")
    if not an:
        raise SystemExit("analysis.json não encontrado")
    cells = {f"{c['id']}__{c['lang']}": c for c in read_json(run / "data" / "cells.json", [])}
    ops = an["opportunities"] = an.get("opportunities") or []  # ausente ou null vale lista vazia (relatório técnico, só com dados)
    for op in ops:
        op["computed"] = compute(op, an.get("weights"), cells)
    ops.sort(key=lambda o: (ORDER.index(o["computed"]["tier"]), -o["computed"]["total"]))
    write_json(run / "analysis.scored.json", an)
    if not ops:
        print("analysis.json sem oportunidades: o relatório sai só com os dados coletados")
    for op in ops:
        c = op["computed"]
        flag = " · OCEANO AZUL" if c["blue_ocean"] else ""
        print(f"{c['verdict']:<6} {c['tier']} {c['total']:>3} ({c['range'][0]}–{c['range'][1]})  conf {c['confidence']:<5} O={c['O']:.2f} P={c['P']:.2f}  {op['name']} [{op.get('lang')}]{flag}"
              + (f"  ⚠ {'; '.join(c['caps'])}" if c["caps"] else ""))


if __name__ == "__main__":
    main()
