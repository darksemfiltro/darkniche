"""Opcional: "assistir" trechos de um vídeo do YouTube com o Gemini (aceita URL do YouTube direto).

  python scripts/gemini_video.py <videoId|URL> --out f.json [--start 0 --end 180] [--model gemini-2.5-flash]

Precisa de GEMINI_API_KEY (variável de ambiente ou .env). O modelo padrão vem de GEMINI_MODEL; confira na
documentação do Google qual é o modelo Flash atual se o padrão for recusado. Analisar trechos (--start/--end)
custa bem menos que o vídeo inteiro. Para a maioria das análises, transcrição + prints (ytdlp_tools) bastam:
use isto quando precisar de ritmo de motion, texto em tela e sincronia fala↔imagem com mais precisão.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_env, log, protect_ids, vid_of, write_json

PROMPT = """Você é um analista de formato de vídeo para YouTube. Analise o trecho e responda SOMENTE com JSON válido:
{
 "hook": "o que acontece nos primeiros 30 s e por que prende (ou não)",
 "blocks": [{"start":"mm:ss","end":"mm:ss","type":"gancho|identificacao|promessa|contrato|didatico|virada|caso|desmonte|outro_lado|sintese|payoff|cta|midroll","summary":"..."}],
 "visual": {"base":"motion/ícones | stock | imagem IA | 3D | apresentador | desenho | mapa/infográfico | misto",
            "background":"descreva o fundo (fixo? cor?)", "palette":["#hex ou nome"], "typography":"estilo e uso de texto na tela",
            "face_on_camera": true, "avatar_or_mascot": "descrição ou null"},
 "motion": {"events_per_min_estimate": 0, "entry_styles":["pop","slide","escala","contador","morph"], "camera":"zooms/pans e quando",
            "sync_with_speech":"como os elementos se sincronizam com a fala"},
 "narration": {"voice":"humana/TTS/ambígua", "pace_wpm_estimate": 0, "person":"1ª/3ª", "tone":"..."},
 "retention_devices": ["open loops, perguntas na voz do espectador, metáforas, números concretos, callbacks..."],
 "automation_notes": "o que seria fácil/difícil de reproduzir com código e IA"
}"""


def analyze(video, start=None, end=None, model=None):
    key = load_env().get("GEMINI_API_KEY")
    if not key:
        raise SystemExit("GEMINI_API_KEY ausente: use transcrição + prints (ytdlp_tools) ou a skill `watch`.")
    vid = re.search(r"([\w-]{11})(?:[?&].*)?$", video)
    url = video if video.startswith("http") else f"https://www.youtube.com/watch?v={video}"
    part = {"fileData": {"fileUri": url}}
    if start is not None or end is not None:
        part["videoMetadata"] = {k: v for k, v in (("startOffset", f"{start}s" if start is not None else None),
                                                   ("endOffset", f"{end}s" if end is not None else None)) if v}
    body = {"contents": [{"parts": [part, {"text": PROMPT}]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2}}
    models = [model or os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"), "gemini-flash-latest"]
    resp = None
    for model in dict.fromkeys(models):  # se o modelo padrão sair de linha, tenta o alias "latest"
        api = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        req = urllib.request.Request(api, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json", "x-goog-api-key": key})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                resp = json.load(r)
            break
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "replace")[:500]
            if e.code == 404 and model != models[-1]:
                log(f"modelo {model} indisponível; tentando {models[-1]}")
                continue
            raise SystemExit(f"Gemini {e.code}: {msg}")
    text = "".join(p.get("text", "") for c in resp.get("candidates", []) for p in c.get("content", {}).get("parts", []))
    try:
        out = json.loads(text)
    except json.JSONDecodeError:
        out = {"raw": text}
    out["_meta"] = {"video": vid.group(1) if vid else video, "model": model, "start": start, "end": end,
                    "usage": resp.get("usageMetadata")}
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video"); ap.add_argument("--out", required=True)
    ap.add_argument("--start", type=int); ap.add_argument("--end", type=int); ap.add_argument("--model")
    a = ap.parse_args(protect_ids(sys.argv[1:]))
    a.video = a.video if a.video.startswith("http") else vid_of(a.video)
    res = analyze(a.video, a.start, a.end, a.model)
    write_json(a.out, res)
    log("ok", a.out, res.get("_meta", {}).get("usage"))
