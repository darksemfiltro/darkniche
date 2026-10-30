"""Cliente da YouTube Data API v3 com cache, contador de cota e filtros avançados.

Quota vigente (Google, 08/10/2026): search.list tem bucket próprio, 100 chamadas/dia;
videos/channels/playlistItems/commentThreads custam 1 unidade do bucket geral (10.000/dia).
O contador é local e conservador: não revela o saldo do projeto no Google Cloud.

Uso como CLI (python scripts/yt_api.py ...):
  quota                                         -> unidades e buscas gastas hoje (contador local)
  channel <@handle|URL|UCid> [--max 200] --out f.json
  search "<consulta>" [--lang pt] [--region BR] [--after 365] [--duration any|short|medium|long]
         [--order viewCount|relevance|date] [--pages 1] [--category 27] --out f.json
  videos <id> [<id>...] --out f.json
  comments <videoId> [--max 300] [--order relevance|time] --out f.json
  popular <PAÍS> [--category 27] [--n 50] --out f.json   -> "em alta" agora no país (2 unidades gerais, sem buscas)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (cache_get, cache_put, days_ago_iso, iso_duration, load_env, log, quota_add,
                    protect_ids, quota_used, vid_of, write_json, quota_lock, pacific_day, redact)

BASE = "https://www.googleapis.com/youtube/v3/"
COST = {"search": 1}
TTL_H = {"search": 24 * 7, "videos": 20, "channels": 72, "playlistItems": 20, "commentThreads": 72}


def budgets():
    config = load_env()
    try:
        general = int(config.get("YT_DAILY_BUDGET", "9500"))
        searches = int(config.get("YT_SEARCH_DAILY_BUDGET", "95"))
        if general < 0 or searches < 0:
            raise ValueError
        return general, searches
    except ValueError:
        raise SystemExit("YT_DAILY_BUDGET e YT_SEARCH_DAILY_BUDGET precisam ser inteiros ≥ 0.")


def quota_status():
    general, searches = budgets()
    used = quota_used()
    return {"day_pacific": pacific_day(), "used_local": used,
            "budget_local": {"units": general, "searches": searches},
            "remaining_local": {"units": max(0, general - used["units"]),
                                "searches": max(0, searches - used["searches"])},
            "default_google_allocation": {"units": 10000, "searches": 100},
            "remaining_google": None,
            "note": "Saldo real exige acesso autenticado ao projeto no Google Cloud; chave de API não informa uso externo. Contador reserva cada tentativa HTTP."}


class QuotaExceeded(RuntimeError):
    pass


def _key():
    k = load_env().get("YT_API_KEY")
    if not k:
        raise SystemExit("YT_API_KEY não encontrada. Defina a variável de ambiente ou crie um .env com YT_API_KEY=...")
    return k


def api(ep, use_cache=True, **params):
    cost = COST.get(ep, 1)
    ck = ep + "?" + urllib.parse.urlencode(sorted(params.items()))
    if use_cache:
        hit = cache_get(ck, TTL_H.get(ep, 24))
        if hit is not None:
            return hit
    key = _key()
    # Cabeçalho evita colocar a chave em URLs/tracebacks/proxies de histórico.
    req = urllib.request.Request(BASE + ep + "?" + urllib.parse.urlencode(params),
                                 headers={"X-Goog-Api-Key": key})
    for attempt in range(4):
        with quota_lock():
            used = quota_used()
            general, searches = budgets()
            bucket = "searches" if ep == "search" else "units"
            limit = searches if ep == "search" else general
            if used[bucket] + cost > limit:
                raise QuotaExceeded(f"orçamento diário local de {bucket} atingido ({used[bucket]}/{limit}). Espere a virada no Pacífico ou ajuste o orçamento ao limite do seu projeto.")
            quota_add(cost, search=(ep == "search"))
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                data = json.load(r)
            if use_cache:
                cache_put(ck, data)
            return data
        except urllib.error.HTTPError as e:
            body = redact(e.read().decode("utf-8", "replace"))
            if e.code in (403, 429) and any(x in body.lower() for x in ("quotaexceeded", "dailylimitexceeded", "daily limit", "quota exceeded")):
                raise QuotaExceeded(f"{ep}: {e.code} {body[:400]}") from None
            if (e.code in (429, 500, 502, 503, 504) or "rateLimitExceeded" in body) and attempt < 3:
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError(f"{ep} {e.code}: {body[:400]}") from None
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            if attempt < 3:
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError(f"{ep}: rede indisponível ({redact(e)})") from None


# ---------- canais ----------
def resolve_channel(ref):
    """@handle, URL (/@x, /channel/UC.., /c/x, /user/x) ou UC... -> channelId (1 unidade; busca só no último caso)."""
    ref = ref.strip()
    m = re.search(r"(UC[0-9A-Za-z_-]{22})", ref)
    if m:
        return m.group(1)
    m = re.search(r"youtube\.com/(@[^/?#]+)", ref)
    handle = m.group(1) if m else (ref if ref.startswith("@") else None)
    if handle:
        items = api("channels", part="id", forHandle=handle).get("items", [])
        if items:
            return items[0]["id"]
    m = re.search(r"youtube\.com/user/([^/?#]+)", ref)
    if m:
        items = api("channels", part="id", forUsername=m.group(1)).get("items", [])
        if items:
            return items[0]["id"]
    name = re.sub(r".*/(c/)?", "", ref)
    items = api("search", part="snippet", q=name, type="channel", maxResults=1).get("items", [])
    if items:
        return items[0]["snippet"]["channelId"]
    raise SystemExit(f"canal não encontrado: {ref}")


def channels(ids):
    out, ids = [], list(dict.fromkeys(i for i in ids if i))
    for i in range(0, len(ids), 50):
        out += api("channels", part="snippet,statistics,contentDetails,brandingSettings,topicDetails", id=",".join(ids[i:i + 50])).get("items", [])
    return out


def uploads(channel_id, max_n=200):
    pl = "UU" + channel_id[2:]
    ids, tok = [], None
    while len(ids) < max_n:
        p = dict(part="contentDetails", playlistId=pl, maxResults=50)
        if tok:
            p["pageToken"] = tok
        try:
            r = api("playlistItems", **p)
        except QuotaExceeded:
            raise  # QuotaExceeded herda de RuntimeError: engolir aqui gravava perfis vazios como se estivessem prontos
        except RuntimeError as e:
            log("uploads:", e)
            break
        ids += [x["contentDetails"]["videoId"] for x in r.get("items", [])]
        tok = r.get("nextPageToken")
        if not tok:
            break
    return ids[:max_n]


# ---------- vídeos ----------
def videos(ids):
    out, ids = [], list(dict.fromkeys(i for i in ids if i))
    for i in range(0, len(ids), 50):
        out += api("videos", part="snippet,statistics,contentDetails,status", id=",".join(ids[i:i + 50])).get("items", [])
    return out


def video_row(v, ch=None):
    s, sn, cd = v.get("statistics", {}), v["snippet"], v["contentDetails"]
    row = {
        "id": v["id"], "title": sn["title"], "published": sn["publishedAt"],
        "lang": (sn.get("defaultAudioLanguage") or sn.get("defaultLanguage") or "").split("-")[0] or None,
        "views": int(s.get("viewCount", 0) or 0), "likes": int(s.get("likeCount", 0) or 0),
        "comments": int(s.get("commentCount", 0) or 0), "dur": iso_duration(cd.get("duration")),
        "channel_id": sn["channelId"], "channel": sn["channelTitle"], "category": sn.get("categoryId"),
        "tags": sn.get("tags", [])[:15], "desc_links": len(re.findall(r"https?://", sn.get("description", ""))),
        "caption": cd.get("caption") == "true",
    }
    if ch:
        cs = ch.get("statistics", {})
        row.update({"subs": None if cs.get("hiddenSubscriberCount") else int(cs.get("subscriberCount", 0) or 0), "ch_views": int(cs.get("viewCount", 0) or 0),
                    "ch_videos": int(cs.get("videoCount", 0) or 0), "ch_created": ch["snippet"].get("publishedAt"),
                    "ch_country": ch["snippet"].get("country")})
    return row


# ---------- busca ----------
class Rows(list):
    """Linhas de uma busca + metadados dela. meta["total_results"] é a estimativa do YouTube de quantos vídeos
    casam com a consulta e os filtros (aproximada, com teto em 1.000.000): serve para comparar oferta entre células."""

    def __init__(self, items=(), meta=None):
        super().__init__(items)
        self.meta = dict(meta or {})


def search(q, lang=None, region=None, pages=1, after_days=365, duration=None, order="viewCount",
           category=None, max_results=50, enrich=True):
    """Custo: uma busca por página + até 2×ceil(resultados/50) unidades gerais."""
    if pages < 1 or not 1 <= max_results <= 50:
        raise ValueError("pages deve ser ≥ 1 e max_results entre 1 e 50")
    ids, tok, total = [], None, None
    for _ in range(pages):
        p = dict(part="id", q=q, type="video", maxResults=max_results, order=order)
        if lang:
            p["relevanceLanguage"] = "zh-Hant" if lang == "zh" else lang
        if region:
            p["regionCode"] = region
        if after_days:
            p["publishedAfter"] = days_ago_iso(after_days)
        if duration and duration != "any":
            p["videoDuration"] = duration
        if category:
            p["videoCategoryId"] = str(category)
        if tok:
            p["pageToken"] = tok
        r = api("search", **p)
        if total is None:
            total = (r.get("pageInfo") or {}).get("totalResults")
        ids += [i["id"]["videoId"] for i in r.get("items", []) if i["id"].get("videoId")]
        tok = r.get("nextPageToken")
        if not tok:
            break
    if not enrich:
        return ids
    vs = videos(ids)
    chs = {c["id"]: c for c in channels([v["snippet"]["channelId"] for v in vs])}
    order_idx = {vid: i for i, vid in enumerate(ids)}
    rows = [video_row(v, chs.get(v["snippet"]["channelId"])) for v in vs]
    rows.sort(key=lambda r: order_idx.get(r["id"], 999))
    return Rows(rows, {"total_results": total} if total is not None else {})


def most_popular(region, category=None, n=50, use_cache=True):
    """Gráfico "em alta" do YouTube num país (1 unidade geral + 1 dos canais). Sinal em tempo real do que sobe agora;
    não é busca, então não gasta o bucket de buscas. `category` = videoCategoryId (ex.: 27 educação, 28 ciência)."""
    p = dict(part="snippet,statistics,contentDetails", chart="mostPopular", regionCode=region, maxResults=min(50, max(1, n)))
    if category:
        p["videoCategoryId"] = str(category)
    vs = api("videos", use_cache=use_cache, **p).get("items", [])
    chs = {c["id"]: c for c in channels([v["snippet"]["channelId"] for v in vs])}
    return [video_row(v, chs.get(v["snippet"]["channelId"])) for v in vs]


# ---------- comentários ----------
def comments(video_id, max_n=300, order="relevance"):
    out, tok = [], None
    while len(out) < max_n:
        p = dict(part="snippet", videoId=video_id, maxResults=100, order=order, textFormat="plainText")
        if tok:
            p["pageToken"] = tok
        try:
            r = api("commentThreads", **p)
        except QuotaExceeded:
            raise
        except RuntimeError as e:
            if "commentsDisabled" in str(e):
                log("comentários desativados:", video_id)
                break
            raise
        for it in r.get("items", []):
            s = it["snippet"]["topLevelComment"]["snippet"]
            out.append({"text": s["textDisplay"], "likes": s["likeCount"], "replies": it["snippet"]["totalReplyCount"],
                        "at": s["publishedAt"], "author": s.get("authorDisplayName")})
        tok = r.get("nextPageToken")
        if not tok:
            break
    return out[:max_n]


def channel_dump(ref, max_videos=200):
    cid = resolve_channel(ref)
    found = channels([cid])
    if not found:
        raise RuntimeError(f"canal indisponível: {cid}")
    ch = found[0]
    vs = videos(uploads(cid, max_videos))
    return {"channel": ch, "videos": [video_row(v, ch) for v in vs]}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("quota")
    c = sub.add_parser("channel"); c.add_argument("ref"); c.add_argument("--max", type=int, default=200); c.add_argument("--out", required=True)
    s = sub.add_parser("search"); s.add_argument("q"); s.add_argument("--lang"); s.add_argument("--region"); s.add_argument("--after", type=int, default=365)
    s.add_argument("--duration", default="any"); s.add_argument("--order", default="viewCount"); s.add_argument("--pages", type=int, default=1)
    s.add_argument("--category"); s.add_argument("--out", required=True)
    v = sub.add_parser("videos"); v.add_argument("ids", nargs="+"); v.add_argument("--out", required=True)
    m = sub.add_parser("comments"); m.add_argument("vid"); m.add_argument("--max", type=int, default=300); m.add_argument("--order", default="relevance"); m.add_argument("--out", required=True)
    pp = sub.add_parser("popular"); pp.add_argument("region"); pp.add_argument("--category"); pp.add_argument("--n", type=int, default=50); pp.add_argument("--out", required=True)
    a = ap.parse_args(protect_ids(sys.argv[1:]))
    if hasattr(a, "ids"):
        a.ids = [vid_of(x) for x in a.ids]
    if hasattr(a, "vid"):
        a.vid = vid_of(a.vid)
    try:
        if a.cmd == "quota":
            print(json.dumps(quota_status(), ensure_ascii=False, indent=2)); sys.exit(0)
        if a.cmd == "channel":
            res = channel_dump(a.ref, a.max)
        elif a.cmd == "search":
            res = search(a.q, a.lang, a.region, a.pages, a.after, a.duration, a.order, a.category)
        elif a.cmd == "videos":
            res = [video_row(x) for x in videos(a.ids)]
        elif a.cmd == "popular":
            res = most_popular(a.region.upper(), a.category, a.n)
        else:
            res = comments(a.vid, a.max, a.order)
        write_json(a.out, res)
        log(f"ok {a.out} · cota hoje: {quota_used()}")
    except QuotaExceeded as e:
        log("QUOTA:", e); sys.exit(3)
