"""Sinais grátis de demanda, tendência e fit cultural (sem gastar buscas da YouTube API).

1) suggest — autocomplete do YouTube por idioma/país. Mostra como as pessoas digitam o tema naquele mercado
   (consultas nativas, gírias, empréstimos) e prova que existe busca. Com --expand, faz "sopa de letras"
   (semente + a, b, c...) para mapear a cauda longa e descobrir subnichos.
     python scripts/signals.py suggest "sportwetten" --lang de --region DE [--expand] --out f.json

2) wiki — interesse relativo pelo mesmo conceito em várias Wikipédias (pageviews dos últimos 12 meses ÷
   tráfego total daquela Wikipédia = "partes por milhão") e tendência (últimos 12 meses ÷ 12 anteriores).
   `index` (100 = idioma com maior interesse) e `rel` (× a mediana dos idiomas; > 1,5 = acima do normal) mostram onde
   o tema pesa mais na cultura; `yoy` é a variação do artigo, `total_yoy` a da Wikipédia inteira (que vem caindo em
   quase todo idioma) e `trend` usa a variação relativa a ela (`yoy_rel`: ±15% = subindo/caindo). Use o artigo de um
   idioma como semente; os outros vêm pelos sitelinks do Wikidata. Idioma sem artigo ou sem dado fica com null (não é zero).
     python scripts/signals.py wiki "Simpson's paradox" --lang en --targets pt,es,fr,de,it,ja,pl,ro,bg,tr,id,nl --out f.json

3) trending — o que está em alta agora num país: buscas em alta do Google Trends (RSS, com as notícias ligadas) e, com
   chave da YouTube API, o gráfico "em alta" do YouTube (2 unidades gerais, nenhuma busca). Serve para achar o que
   está quente e separar demanda de base de pico de evento.
     python scripts/signals.py trending --geo BR [--youtube] [--category 27] [--n 25] --out f.json

4) news — manchetes recentes do Google Notícias (RSS, sem chave) sobre o tema num país e o ritmo da última semana
   contra o resto do mês (`ratio` > 1,5 = a cobertura acelera; < 0,67 = esfria). Serve para ver evento e pico.
     python scripts/signals.py news "finanças pessoais" --lang pt --region BR [--days 30] --out f.json

Limites: autocomplete não informa volume; a Wikipédia mede curiosidade enciclopédica, não consumo de vídeo; "em alta" é
retrato do momento; notícia mede cobertura da imprensa, não demanda. Use os sinais como apoio para F (fit cultural) e
para a leitura de tendência, nunca sozinhos.
"""
from __future__ import annotations

import argparse
import json
import os
import string
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import cache_get, cache_put, load_env, log, stamp, write_json

# A política de User-Agent da Wikimedia pede um contato: AMY_CONTACT (e-mail ou URL, no ambiente ou no .env) entra aqui.
_CONTACT = (load_env().get("AMY_CONTACT") or "").strip()
UA = {"User-Agent": "DarkNiche/1.0 (analise-mercado-yt; uso local" + (f"; {_CONTACT}" if _CONTACT else "") + ")"}
BROWSER_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"}


def _fetch(url, ttl_h=72, headers=None, as_json=True):
    key = ("J:" if as_json else "T:") + url
    hit = cache_get(key, ttl_h)
    if hit is not None:
        return hit["text"] if not as_json else hit
    req = urllib.request.Request(url, headers=headers or UA)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                raw = r.read().decode("utf-8", "replace")
            data = json.loads(raw) if as_json else raw
            cache_put(key, data if as_json else {"text": raw})
            return data
        except Exception as e:
            blocked = "Tunnel connection failed" in str(e) or "Name or service not known" in str(e) or "getaddrinfo" in str(e)
            if attempt == 2 or blocked:
                raise RuntimeError(f"{url[:90]}… → {e}")
            time.sleep(1.5 * (attempt + 1))


def _get_json(url, ttl_h=72):
    return _fetch(url, ttl_h)


# ---------------- autocomplete ----------------
def suggest(q, lang="en", region=None, expand=False, pause=0.25):
    def one(term):
        p = {"client": "firefox", "ds": "yt", "hl": lang, "q": term, "ie": "utf-8", "oe": "utf-8"}
        if region:
            p["gl"] = region
        url = "https://suggestqueries.google.com/complete/search?" + urllib.parse.urlencode(p)
        try:
            d = _get_json(url, 72)
            return d[1] if isinstance(d, list) and len(d) > 1 else []
        except RuntimeError as e:
            log(e)
            return None if term == q else []
    base = one(q)
    if base is None:  # sem rede para o autocomplete: não adianta tentar as 30 expansões
        raise SystemExit("autocomplete inacessível (rede bloqueada para suggestqueries.google.com?). Siga sem este sinal e registre a limitação.")
    out = {"seed": q, "lang": lang, "region": region, "fetched_at": stamp(), "base": base, "expanded": {}}
    if expand:
        letters = string.ascii_lowercase
        if lang in ("pt", "es", "fr", "it", "ro", "tr", "pl", "de"):
            letters += {"pt": "ç", "es": "ñ", "fr": "é", "it": "è", "ro": "ș", "tr": "ş", "pl": "ł", "de": "ü"}[lang]
        for ch in letters:
            out["expanded"][ch] = one(f"{q} {ch}") or []
            time.sleep(pause)
        for pre in ({"pt": ["como", "por que", "o que"], "es": ["cómo", "por qué", "qué"], "en": ["how", "why", "what"],
                     "fr": ["comment", "pourquoi"], "de": ["wie", "warum"], "it": ["come", "perché"]}.get(lang, [])):
            out["expanded"][pre + "…"] = one(f"{pre} {q}") or []
            time.sleep(pause)
    allq = list(dict.fromkeys(out["base"] + [s for v in out["expanded"].values() for s in v]))
    out["all"] = allq
    out["count"] = len(allq)
    return out


# ---------------- wikipedia ----------------
def _qid(title, lang, depth=0):
    url = f"https://{lang}.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
        {"action": "query", "prop": "pageprops", "titles": title, "redirects": 1, "format": "json"})
    pages = _get_json(url, 720).get("query", {}).get("pages", {})
    for p in pages.values():
        if p.get("pageprops", {}).get("wikibase_item"):
            return p["pageprops"]["wikibase_item"], p.get("title")
    url = f"https://{lang}.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
        {"action": "query", "list": "search", "srsearch": title, "srlimit": 1, "format": "json"})
    hits = _get_json(url, 720).get("query", {}).get("search", [])
    if hits and depth == 0:  # uma só volta: a página achada pela busca pode não ter Wikidata e chamaria a si mesma sem fim
        return _qid(hits[0]["title"], lang, 1)
    return None, None


def _sitelinks(qid):
    d = _get_json(f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json", 720)
    ent = d["entities"][qid]
    return {k[:-4]: v["title"] for k, v in ent.get("sitelinks", {}).items() if k.endswith("wiki") and k not in ("commonswiki", "specieswiki")}


def _range(months=24):
    """Meses fechados: do primeiro dia de `months` meses atrás até o último dia do mês passado."""
    end = datetime.now(timezone.utc).replace(day=1)
    start = end
    for _ in range(months):
        start = (start - timedelta(days=1)).replace(day=1)
    return start.strftime("%Y%m%d"), (end - timedelta(days=1)).strftime("%Y%m%d")


def _series(lang, title, start, end):
    """Views mensais do artigo (lista em ordem de mês) ou None quando a API não tem dado (404, rede)."""
    t = urllib.parse.quote(title.replace(" ", "_"), safe="")
    url = f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/{lang}.wikipedia/all-access/user/{t}/monthly/{start}/{end}"
    try:
        return [i["views"] for i in _get_json(url, 168).get("items", [])]
    except RuntimeError:
        return None


def _total_series(lang, start, end):
    url = f"https://wikimedia.org/api/rest_v1/metrics/pageviews/aggregate/{lang}.wikipedia/all-access/user/monthly/{start}/{end}"
    try:
        return [i["views"] for i in _get_json(url, 720).get("items", [])]
    except RuntimeError:
        return None


def wiki(title, lang="en", targets=None):
    qid, canon = _qid(title, lang)
    if not qid:
        raise SystemExit(f"artigo não encontrado: {title} ({lang})")
    links = _sitelinks(qid)
    start, end = _range(24)
    langs = targets or sorted(links)
    rows = []
    for l in dict.fromkeys([lang] + list(langs)):
        t = links.get(l)
        if not t:
            rows.append({"lang": l, "title": None, "views": None, "ppm": None, "yoy": None, "trend": None, "exists": False})
            continue
        s = _series(l, t, start, end)
        tot = _total_series(l, start, end)
        row = {"lang": l, "title": t, "exists": True, "url": f"https://{l}.wikipedia.org/wiki/{urllib.parse.quote(t.replace(' ', '_'))}",
               "views": None, "ppm": None, "yoy": None, "total_yoy": None, "yoy_rel": None, "trend": None, "series": None}
        if s:
            # a variação anual compara 12 meses com os 12 anteriores; com menos de 24 meses de série (artigo novo) não há variação
            last, prev = sum(s[-12:]), (sum(s[-24:-12]) if len(s) >= 24 else None)
            row["views"], row["series"] = last, s[-24:]
            tot12 = sum(tot[-12:]) if tot and len(tot) >= 12 else None
            row["ppm"] = round(last / tot12 * 1e6, 3) if tot12 else None
            tot_prev = sum(tot[-24:-12]) if tot and len(tot) >= 24 else None
            if tot12 and tot_prev:
                row["total_yoy"] = round(tot12 / tot_prev - 1, 2)  # a Wikipédia inteira também varia: tendência é relativa a ela
            if prev and prev >= 200 and last >= 200:  # abaixo disso a variação é só ruído
                row["yoy"] = round(last / prev - 1, 2)
                if row["total_yoy"] is not None and row["total_yoy"] > -0.95:
                    row["yoy_rel"] = round((1 + row["yoy"]) / (1 + row["total_yoy"]) - 1, 2)
                    row["trend"] = "subindo" if row["yoy_rel"] >= 0.15 else "caindo" if row["yoy_rel"] <= -0.15 else "estável"
        else:
            row["error"] = "sem dado de pageviews (artigo novo, redirecionamento ou API indisponível)"
        rows.append(row)
    have = sorted(r["ppm"] for r in rows if r["ppm"])
    base = max(have) if have else None
    med = have[len(have) // 2] if have else None
    for r in rows:
        r["index"] = round(100 * r["ppm"] / base) if r["ppm"] is not None and base else None  # 100 = idioma com maior interesse relativo
        r["rel"] = round(r["ppm"] / med, 2) if r["ppm"] is not None and med else None          # × a mediana dos idiomas (> 1,5 = pesa mais ali)
    rows.sort(key=lambda r: -(r["ppm"] or -1))
    return {"qid": qid, "seed": canon, "period": [start, end], "fetched_at": stamp(), "rows": rows}


# ---------------- em alta agora ----------------
def trending(geo="BR", n=25, youtube=False, category=None):
    """Buscas em alta do Google Trends (RSS) e, opcionalmente, o gráfico "em alta" do YouTube no país."""
    url = "https://trends.google.com/trending/rss?" + urllib.parse.urlencode({"geo": geo.upper()})
    out = {"geo": geo.upper(), "fetched_at": stamp(), "google_trends": [], "youtube_popular": None}
    try:
        root = ET.fromstring(_fetch(url, 3, BROWSER_UA, as_json=False))
        for it in root.iter("item"):
            out["google_trends"].append({
                "query": (it.findtext("title") or "").strip(), "traffic": it.findtext("{*}approx_traffic"),
                "published": it.findtext("pubDate"),
                "news": [{"title": x.findtext("{*}news_item_title"), "url": x.findtext("{*}news_item_url"),
                          "source": x.findtext("{*}news_item_source")} for x in it.findall("{*}news_item")][:3]})
        out["google_trends"] = out["google_trends"][:n]
    except (RuntimeError, ET.ParseError) as e:
        log(f"Google Trends indisponível: {str(e)[-120:]}")
    if youtube:
        try:
            import yt_api
            for cat in ([category, None] if category else [None]):  # nem toda categoria tem gráfico "em alta" (404)
                try:
                    rows = yt_api.most_popular(geo.upper(), cat, n)
                except RuntimeError as e:
                    if cat and "404" in str(e):
                        log(f"categoria {cat} sem gráfico em alta em {geo.upper()}; usando o geral")
                        continue
                    raise
                out["youtube_popular"] = [{k: r.get(k) for k in ("id", "title", "channel", "channel_id", "views", "published", "dur", "category", "subs")}
                                          for r in rows]
                out["youtube_category"] = cat
                break
        except (SystemExit, RuntimeError) as e:  # sem chave ou sem cota: o resto do sinal continua valendo
            log(f"YouTube em alta indisponível: {str(e)[:120]}")
    return out


# ---------------- notícias ----------------
def news(q, lang="pt", region="BR", days=30, n=40):
    """Manchetes do Google Notícias (RSS) e ritmo de cobertura: últimos 7 dias contra o resto da janela."""
    from email.utils import parsedate_to_datetime
    region = (region or "US").upper()
    loc = {"hl": f"{lang}-{region}", "gl": region, "ceid": f"{region}:{lang}"}
    now = datetime.now(timezone.utc)

    def grab(window):
        url = "https://news.google.com/rss/search?" + urllib.parse.urlencode({"q": f"{q} when:{window}d", **loc})
        root = ET.fromstring(_fetch(url, 3, BROWSER_UA, as_json=False))
        rows = []
        for it in root.iter("item"):
            try:
                when = parsedate_to_datetime(it.findtext("pubDate"))
            except (TypeError, ValueError):
                continue
            src = it.find("source")
            rows.append({"title": (it.findtext("title") or "").strip(), "url": it.findtext("link"), "published": when.astimezone(timezone.utc).strftime("%Y-%m-%d"),
                         "source": src.text if src is not None else None, "age": (now - when).days})
        return rows

    out = {"query": q, "lang": lang, "region": region, "days": days, "fetched_at": stamp(), "items": [], "n_total": 0,
           "n_7d": 0, "ratio": None, "trend": None, "capped": False, "sources": 0}
    try:
        rows = grab(days)
        last7 = sum(1 for r in rows if r["age"] <= 7)
        out.update(n_total=len(rows), n_7d=last7, capped=len(rows) >= 95, sources=len({r["source"] for r in rows if r["source"]}),
                   items=[{k: r[k] for k in ("title", "url", "published", "source")} for r in rows[:n]])
        if out["capped"]:  # o RSS devolve no máximo ~100 itens: compara a semana com a anterior numa janela de 14 dias
            r14 = grab(14)
            if len(r14) < 95:
                last7 = sum(1 for r in r14 if r["age"] <= 7)
                before = len(r14) - last7
                out["n_7d"], out["window_for_ratio"] = last7, 14
                out["ratio"] = round(last7 / max(before, 0.5), 2) if len(r14) >= 8 else None
        elif len(rows) >= 8:
            weeks_prev = max(0.5, (days - 7) / 7)
            prev = len(rows) - last7
            out["ratio"] = round(last7 / (prev / weeks_prev), 2) if prev else None
            if not prev:  # toda a cobertura da janela caiu na última semana
                out["trend"] = "acelerando"
        if out["ratio"] is not None:
            out["trend"] = "acelerando" if out["ratio"] >= 1.5 else "esfriando" if out["ratio"] <= 0.67 else "estável"
    except (RuntimeError, ET.ParseError) as e:
        log(f"Google Notícias indisponível: {str(e)[-120:]}")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("suggest"); s.add_argument("q"); s.add_argument("--lang", default="en"); s.add_argument("--region")
    s.add_argument("--expand", action="store_true"); s.add_argument("--out", required=True)
    w = sub.add_parser("wiki"); w.add_argument("title"); w.add_argument("--lang", default="en"); w.add_argument("--targets"); w.add_argument("--out", required=True)
    t = sub.add_parser("trending"); t.add_argument("--geo", required=True); t.add_argument("--n", type=int, default=25)
    t.add_argument("--youtube", action="store_true"); t.add_argument("--category"); t.add_argument("--out", required=True)
    nw = sub.add_parser("news"); nw.add_argument("q"); nw.add_argument("--lang", default="pt"); nw.add_argument("--region", default="BR")
    nw.add_argument("--days", type=int, default=30); nw.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.cmd == "suggest":
        res = suggest(a.q, a.lang, a.region, a.expand)
        log(f"{res['count']} sugestões")
    elif a.cmd == "trending":
        res = trending(a.geo, a.n, a.youtube, a.category)
        log(f"{len(res['google_trends'])} buscas em alta · YouTube: {len(res['youtube_popular'] or [])} vídeos")
    elif a.cmd == "news":
        res = news(a.q, a.lang, a.region, a.days)
        log(f"{res['n_total']} notícias em {a.days} dias ({res['n_7d']} na última semana) · fontes {res['sources']} · ritmo {res['ratio']} {res['trend'] or ''}"
            + (f" (janela de {res['window_for_ratio']} dias: o RSS corta em ~100 itens)" if res.get("window_for_ratio") else ""))
    else:
        try:
            res = wiki(a.title, a.lang, a.targets.split(",") if a.targets else None)
        except RuntimeError as e:
            raise SystemExit(f"Wikipédia/Wikidata inacessível ({str(e)[-120:]}). Siga sem este sinal e registre a limitação.")
        for r in res["rows"]:
            log(f"{r['lang']:<4} {str(r['title'])[:40]:<40} views={r['views']} ppm={r['ppm']} índice={r['index']} ×mediana={r['rel']} tendência={r['trend']}")
    write_json(a.out, res)
