"""Utilidades compartilhadas da skill analise-mercado-yt.

Só stdlib. Funciona em Windows, macOS e Linux. Todo arquivo é lido e gravado em UTF-8
(no Windows o padrão é cp1252 e quebraria acentos).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import statistics as st
import sys
import time
import tempfile
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Configuração (chave no .env, perfil.json) mora em HOME. Cache, cota e trava moram em DATA (padrão: o mesmo HOME);
# aponte AMY_DATA para outro disco quando o da configuração for pequeno ou quando quiser dados portáteis.
HOME = Path(os.environ["AMY_HOME"]).expanduser() if os.environ.get("AMY_HOME") else Path.home() / ".analise-mercado-yt"
DATA = Path(os.environ["AMY_DATA"]).expanduser() if os.environ.get("AMY_DATA") else HOME
CACHE_DIR = DATA / "cache"
QUOTA_FILE = DATA / "quota.json"

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


# ---------- texto ----------
def norm_text(s):
    """Minúsculas e sem acentos: base de toda comparação de títulos, consultas e nomes de canal."""
    import unicodedata
    return "".join(ch for ch in unicodedata.normalize("NFKD", (s or "").lower()) if not unicodedata.combining(ch))


# ---------- arquivos ----------
def read_json(path, default=None):
    p = Path(path)
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8-sig"))


def write_json(path, data, indent=1):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    # Arquivos temporários únicos evitam colisões entre processos/agentes.
    fd, name = tempfile.mkstemp(dir=p.parent, prefix=p.name + ".", suffix=".tmp")
    tmp = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=indent, allow_nan=False)
        tmp.replace(p)
    finally:
        tmp.unlink(missing_ok=True)


def glob_files(folder, pattern="*.json"):
    """Arquivos de uma pasta, em ordem. Ao contrário de glob.glob(str(pasta / "*.json")), não trata [ ] * ? do nome da
    pasta como curinga (uma pasta "analise [Clientes]" dava zero arquivos, sem erro)."""
    return sorted(str(p) for p in Path(folder).glob(pattern))


def slug(text, maxlen=48):
    t = text.lower()
    t = re.sub(r"[áàâãä]", "a", t); t = re.sub(r"[éèêë]", "e", t); t = re.sub(r"[íìîï]", "i", t)
    t = re.sub(r"[óòôõö]", "o", t); t = re.sub(r"[úùûü]", "u", t); t = t.replace("ç", "c").replace("ñ", "n")
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    if len(t) > maxlen:  # corta na última palavra inteira
        cut = t[:maxlen + 1].rfind("-")
        t = t[:cut] if cut > maxlen // 2 else t[:maxlen]
    # título sem letra latina (japonês, árabe…) viraria "x" e a segunda análise do mês bateria na primeira
    return t.strip("-") or ("x-" + hashlib.sha1(text.encode("utf-8")).hexdigest()[:6])


# ---------- credenciais ----------
YT_KEY_NAMES = ("YT_API_KEY", "YOUTUBE_API_KEY", "YOUTUBE_DATA_API_KEY", "YOUTUBE_DATA_API_V3_KEY")
ENV_NAMES = (*YT_KEY_NAMES, "GEMINI_API_KEY", "GEMINI_MODEL", "YT_DAILY_BUDGET", "YT_SEARCH_DAILY_BUDGET", "AMY_CONTACT")


def read_text_any(path):
    """Lê texto em UTF-8 (com ou sem BOM) ou UTF-16 (o PowerShell 5.1 grava arquivos assim com `>`)."""
    raw = Path(path).read_bytes()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16")
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("cp1252", "replace")


def env_config(run_dir=None):
    """Ambiente > .env da análise > pasta atual > AMY_HOME. Não imprime nem copia segredos."""
    config, sources = {}, {}
    for name in ENV_NAMES:
        if os.environ.get(name, "").strip():
            config[name] = os.environ[name].strip()
            sources[name] = "ambiente:" + name
    for base in [Path(run_dir) if run_dir else None, Path.cwd(), HOME]:
        if not base:
            continue
        env = base / ".env"
        if env.exists():
            values = {}
            for line in read_text_any(env).splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.removeprefix("export ").split("=", 1)
                k, v = k.strip(), v.strip()
                if v.startswith(('"', "'")):
                    quote = v[0]
                    v = v[1:].split(quote, 1)[0]
                else:
                    v = re.split(r"\s+#", v, maxsplit=1)[0].strip()
                if k in ENV_NAMES and v:
                    values[k] = v
            # Um alias no ambiente ganha de qualquer nome encontrado em .env.
            have_yt = any(config.get(k) for k in YT_KEY_NAMES)
            for k, v in values.items():
                if k not in config and not (k in YT_KEY_NAMES and have_yt):
                    config[k], sources[k] = v, str(env) + ":" + k
    key_name = next((k for k in YT_KEY_NAMES if config.get(k)), None)
    if key_name:
        config["YT_API_KEY"] = config[key_name]
        sources["YT_API_KEY"] = sources[key_name]
    return config, sources


def load_env(run_dir=None):
    # _RUN permite que os clientes chamados por profile/comments/reference leiam o .env da análise.
    return env_config(run_dir if run_dir is not None else _RUN)[0]


def redact(text):
    """Mascara chaves do Google (AIza…), chaves estilo sk-… e pares key=/token=/secret= em mensagens de erro e logs."""
    s = re.sub(r"AIza[0-9A-Za-z_-]{20,}", "[CHAVE OCULTA]", str(text))
    s = re.sub(r"\bsk-[A-Za-z0-9_-]{20,}", "[CHAVE OCULTA]", s)
    # o nome do campo pode ter prefixo (YT_API_KEY=, access_token=, client_secret=): \b antes de "key" falhava depois de "_"
    return re.sub(r"(?i)\b([\w-]*(?:key|token|secret|passw(?:or)?d)[\w-]*)=([^&\s\"']+)", r"\1=[OCULTO]", s)


# ---------- cota (o dia da API vira à meia-noite do Pacífico) ----------
def pacific_day():
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%d")
    except (ImportError, KeyError):
        # Windows sem tzdata: regras de horário de verão dos EUA desde 2007.
        now = datetime.now(timezone.utc)
        march = datetime(now.year, 3, 8, 10, tzinfo=timezone.utc)
        march += timedelta(days=(6 - march.weekday()) % 7)
        november = datetime(now.year, 11, 1, 9, tzinfo=timezone.utc)
        november += timedelta(days=(6 - november.weekday()) % 7)
        return (now - timedelta(hours=7 if march <= now < november else 8)).strftime("%Y-%m-%d")


def quota_used():
    q = read_json(QUOTA_FILE, {})
    return normalize_quota(q.get(pacific_day(), {}))


def normalize_quota(q):
    q = dict(q or {})
    units, searches = q.get("units", 0), q.get("searches", 0)
    if q and q.get("schema", 1) < 2:
        units = max(0, units - 100 * searches)
        q["migrated_estimate"] = True
    return {**q, "schema": 2, "units": units, "searches": searches,
            "requests": q.get("requests", units + searches)}


_RUN = None


def set_run(run_dir):
    """Liga o contador de cota da análise atual (data/quota.json), além do contador do dia."""
    global _RUN
    _RUN = Path(run_dir) if run_dir else None


@contextmanager
def quota_lock():
    """Lock do SO: liberado mesmo se o processo morrer (Windows/POSIX)."""
    lock_dir = QUOTA_FILE.parent  # o lock mora ao lado do contador (e acompanha quem o desloca, como os testes)
    lock_dir.mkdir(parents=True, exist_ok=True)
    with (lock_dir / "quota.lock").open("a+b") as stream:
        stream.seek(0, 2)
        if stream.tell() == 0:
            stream.write(b"0"); stream.flush()
        stream.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def quota_add(units, search=False):
    """Chamar dentro de quota_lock para reservar antes de enviar cada tentativa HTTP.

    schema 2: units = bucket geral; searches = bucket Search Queries (separado).
    """
    def add(q):
        q = normalize_quota(q)
        q["units"] += 0 if search else units
        q["searches"] += units if search else 0
        q["requests"] += 1
        return q
    if _RUN is not None:
        rq = add(read_json(_RUN / "data" / "quota.json", {}))
        write_json(_RUN / "data" / "quota.json", rq, indent=0)
    q = read_json(QUOTA_FILE, {})
    day = pacific_day()
    q[day] = add(q.get(day, {}))
    for k in list(q):  # guarda só 14 dias
        if k < (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d"):
            q.pop(k, None)
    write_json(QUOTA_FILE, q, indent=0)


# ---------- cache ----------
def cache_get(key, ttl_hours):
    f = CACHE_DIR / (hashlib.sha1(key.encode("utf-8")).hexdigest() + ".json")
    if f.exists() and (time.time() - f.stat().st_mtime) < ttl_hours * 3600:
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def cache_put(key, data):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    f = CACHE_DIR / (hashlib.sha1(key.encode("utf-8")).hexdigest() + ".json")
    write_json(f, data, indent=None)


# ---------- tempo e números ----------
NOW = datetime.now(timezone.utc)
def stamp():
    """Carimbo UTC de uma coleta (minuto): vai nos arquivos brutos e aparece no relatório como "dados de"."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


SHORT_MAX = 180  # segundos: Shorts vão até 3 min
LONG_MIN = 480  # segundos: abaixo disso não é "long-form" (uma só régua em metrics e profile_channels)
MATURE_DAYS = 14  # vídeos mais novos que isso ainda estão acumulando views; ficam fora de comparações de patamar


def parse_dt(iso):
    if not iso:
        return None
    try:
        d = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def age_days(iso):
    d = parse_dt(iso)
    return max(1, (NOW - d).days) if d else None


def iso_duration(s):
    m = re.match(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", s or "")
    if not m:
        return 0
    d, h, mi, se = [int(x or 0) for x in m.groups()]
    return d * 86400 + h * 3600 + mi * 60 + se


def median(xs):
    xs = [x for x in xs if x is not None]
    return st.median(xs) if xs else 0


def pct(xs, q):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return 0
    i = min(len(xs) - 1, max(0, int(round(q * (len(xs) - 1)))))
    return xs[i]


def days_ago_iso(days):
    return (NOW - timedelta(days=days)).strftime("%Y-%m-%dT00:00:00Z")


# ---------- tamanho relativo de mercado por idioma (público de YouTube, EN = 1,0) ----------
# Aproximação para normalizar views entre mercados de tamanhos muito diferentes. Revise com references/mercados.md
# e sobrescreva por análise em plan.languages[].size quando tiver número melhor.
MARKET_SIZE = {
    "en": 1.0, "es": 0.70, "hi": 0.60, "pt": 0.33, "id": 0.30, "ar": 0.30, "ru": 0.25, "fr": 0.20, "de": 0.18,
    "ja": 0.17, "vi": 0.14, "tr": 0.13, "th": 0.10, "ko": 0.10, "it": 0.10, "pl": 0.07, "nl": 0.045, "ro": 0.03,
    "cs": 0.02, "hu": 0.017, "el": 0.015, "sv": 0.02, "uk": 0.05, "bg": 0.011, "fil": 0.15, "ms": 0.05,
    # idiomas menores (ordem de grandeza; sobrescreva em plan.languages[].size quando tiver número melhor)
    "bn": 0.20, "ur": 0.20, "ta": 0.12, "fa": 0.05, "zh": 0.06, "he": 0.03, "da": 0.02, "no": 0.025, "fi": 0.02,
    "sk": 0.01, "sr": 0.012, "hr": 0.01,
}


def market_size(lang, plan=None):
    for l in (plan or {}).get("languages") or []:
        if l.get("lang") == lang and l.get("size"):
            try:
                return float(str(l["size"]).replace(",", "."))  # "0,33" também vale
            except ValueError:
                break
    return MARKET_SIZE.get(lang, 0.05)


def size_known(lang, plan=None):
    """False quando o tamanho do mercado do idioma é só o palpite padrão (0,05): o equivalente em EN fica pouco confiável."""
    return lang in MARKET_SIZE or any(l.get("lang") == lang and l.get("size") for l in (plan or {}).get("languages") or [])


# Região padrão (regionCode da API) de cada idioma. Idioma fora da lista fica sem região: melhor omitir do que inventar.
# Troque com `--langs es-AR,pt-PT,en-GB` ou editando plan.languages. ru→KZ: público russófono monetizável fora da Rússia.
LANG_REGION = {
    "pt": "BR", "es": "MX", "en": "US", "fr": "FR", "de": "DE", "it": "IT", "ja": "JP", "pl": "PL", "tr": "TR",
    "id": "ID", "bg": "BG", "ro": "RO", "nl": "NL", "ko": "KR", "hi": "IN", "vi": "VN", "th": "TH", "ar": "SA",
    "ru": "KZ", "uk": "UA", "cs": "CZ", "hu": "HU", "el": "GR", "sv": "SE", "fil": "PH", "ms": "MY", "zh": "TW",
    "he": "IL", "da": "DK", "no": "NO", "fi": "FI", "bn": "BD", "ur": "PK", "ta": "IN", "fa": None, "sk": "SK",
    "sr": "RS", "hr": "HR",
}
LANG_LABEL = {"pt": "PT-BR"}


def parse_lang_spec(spec):
    """'pt' → ('pt', 'BR', 'PT-BR') · 'es-AR' → ('es', 'AR', 'ES-AR') · 'xx' → ('xx', None, 'XX')."""
    s = str(spec).strip().replace("_", "-")
    lang, _, reg = s.partition("-")
    lang, reg = lang.lower(), reg.upper() or None
    region = reg or LANG_REGION.get(lang)
    label = f"{lang.upper()}-{reg}" if reg else LANG_LABEL.get(lang, lang.upper())
    return lang, region, label


# ---------- idioma (heurística leve para títulos) ----------
_STOP = {
    "pt": {"que", "não", "como", "você", "para", "uma", "dos", "das", "por", "mais", "isso", "seu", "sua", "é", "são", "ao", "nao", "voce", "porque", "quem",
           "do", "da", "em", "os", "com", "ele", "ela", "pelo", "pela", "muito", "tem", "foi", "vai", "já"},
    "es": {"que", "cómo", "como", "para", "una", "los", "las", "por", "más", "qué", "del", "por qué", "esto", "tu", "es", "son", "nadie", "así", "muy", "el",
           "en", "un", "con", "lo", "al", "pero", "ya", "fue", "está", "hay", "sin", "cuando", "donde", "también"},
    "en": {"the", "how", "why", "what", "you", "your", "is", "are", "of", "and", "to", "in", "this", "that", "with", "for", "it", "explained"},
    "fr": {"le", "la", "les", "des", "est", "pourquoi", "comment", "une", "pour", "vous", "que", "qui", "du", "au", "ce", "c'est", "pas", "sur"},
    "de": {"der", "die", "das", "und", "ist", "warum", "wie", "nicht", "ein", "eine", "mit", "für", "den", "dem", "von", "zu", "auf", "sie", "wir"},
    "it": {"il", "lo", "gli", "della", "perché", "come", "che", "non", "una", "per", "sono", "del", "questo", "di", "nel", "alla"},
    "nl": {"de", "het", "een", "en", "van", "waarom", "hoe", "niet", "is", "dat", "die", "voor", "met", "je"},
    "pl": {"jak", "dlaczego", "nie", "się", "jest", "to", "na", "do", "czy", "co", "w", "z", "że", "polsce"},
    "ro": {"de", "și", "si", "în", "cum", "de ce", "nu", "este", "care", "pentru", "cu", "mai", "din", "pe"},
    "tr": {"ve", "bir", "bu", "nasıl", "neden", "için", "ile", "çok", "ne", "değil", "gibi", "da", "de"},
    "id": {"dan", "yang", "di", "ini", "itu", "bagaimana", "kenapa", "mengapa", "tidak", "dengan", "untuk", "ada", "dari"},
    "hi": {"ke", "ka", "ki", "hai", "kya", "kaise", "baad", "mein", "aur", "ko", "nahi", "kyun", "kab", "hua", "gaya", "tha", "sach"},
    # idiomas nórdicos, tcheco, húngaro, finlandês e vietnamita: palavras-função que quase só existem em cada um
    "sv": {"och", "att", "det", "är", "inte", "hur", "varför", "vad", "som", "för", "med", "på", "jag", "till", "har", "ett"},
    "da": {"og", "at", "er", "ikke", "hvordan", "hvorfor", "hvad", "som", "for", "med", "på", "jeg", "til", "har", "af", "det"},
    "no": {"og", "å", "er", "ikke", "hvordan", "hvorfor", "hva", "som", "for", "med", "på", "jeg", "til", "har", "av", "det"},
    "fi": {"ja", "on", "että", "ei", "se", "kuinka", "miksi", "mikä", "sinä", "minä", "oli", "ovat", "tämä", "mitä", "kun", "jos"},
    "cs": {"je", "že", "jak", "proč", "který", "jsou", "byl", "ale", "už", "nebo", "co", "pro", "jsem", "být", "tak"},
    "hu": {"és", "hogy", "nem", "egy", "miért", "hogyan", "volt", "vagy", "van", "ez", "meg", "már", "de", "az"},
    "vi": {"và", "của", "là", "cho", "không", "như", "thế", "nào", "tại", "sao", "một", "những", "được", "trong", "với"},
}


def guess_lang(text):
    return lang_evidence(text)["lang"]


def guess_lang_scored(text):
    e = lang_evidence(text)
    return e["lang"], e["strength"]


_SCRIPTS = [("ja", r"[\u3040-\u30ff]"), ("ko", r"[\uac00-\ud7af]"), ("zh", r"[\u4e00-\u9fff]"), ("cyr", r"[\u0400-\u04ff]"),
            ("ar", r"[\u0600-\u06ff]"), ("hi", r"[\u0900-\u097f]"), ("th", r"[\u0e00-\u0e7f]"), ("el", r"[\u0370-\u03ff]"),
            ("he", r"[\u0590-\u05ff]")]
CYRILLIC = {"ru", "bg", "uk", "sr", "mk", "be", "kk"}
ARABIC_SCRIPT = {"ar", "fa", "ur", "ps", "ku", "sd", "ug"}   # a escrita n\u00e3o separa estes idiomas: vale o metadado
DEVANAGARI = {"hi", "mr", "ne"}
CJK_GROUP = {"ja", "zh"}  # kanji sem kana n\u00e3o separa japon\u00eas de chin\u00eas
SCRIPT_GROUPS = (CYRILLIC, ARABIC_SCRIPT, DEVANAGARI, CJK_GROUP)
LANG_ALIAS = {"iw": "he", "nb": "no", "nn": "no", "in": "id", "tl": "fil"}  # c\u00f3digos antigos ou variantes que o YouTube devolve


def same_script(a, b):
    """True quando os dois idiomas usam a mesma escrita e o t\u00edtulo n\u00e3o os separa (fa e ar, ru e bg, ja e zh\u2026)."""
    return bool(a and b) and any(a in g and b in g for g in SCRIPT_GROUPS)


# Idiomas que o t\u00edtulo consegue confirmar (lista de palavras-fun\u00e7\u00e3o ou escrita pr\u00f3pria). Nos demais (fa, ur, bn, ta, sk, hr,
# sr, ms, fil\u2026) vale o metadado do YouTube e o filtro de relev\u00e2ncia da busca; ver metrics.cell_metrics.
VERIFIABLE =set(_STOP) | {"ja", "ko", "zh", "ar", "th", "el", "he", "ru", "uk", "bg"}


def can_verify_lang(lang):
    return lang in VERIFIABLE


def _cyrillic_lang(lo):
    if re.search(r"[їєґ]", lo) or re.search(r"(?<!\w)(і|та|що|як)(?!\w)", lo):
        return "uk"
    if re.search(r"[ыэё]", lo) or re.search(r"(?<!\w)(почему|это|что|который|работает|россии|для|только|можно|нужно|если|когда|после|будет|чтобы|зачем)(?!\w)", lo):
        return "ru"
    if "ъ" in lo or re.search(r"(?<!\w)(защо|са|ще|най|какво|няма|българия|това|трябва|когато|също)(?!\w)", lo):
        return "bg"
    return None  # cirílico sem marcador (как, не e и existem em ru, bg e uk): sem palavra que decida, não chute


def lang_evidence(text):
    """Evidência de idioma de um título: {"lang", "strength", "scores", "script_share", "script"}.
    strength 3 = escrita própria predominante (≥ 30% das letras: CJK, cirílico, árabe, devanágari, tailandês, grego);
    senão, nº de palavras-função reconhecidas do idioma vencedor. `scores` traz a contagem de cada idioma latino."""
    out = {"lang": None, "strength": 0, "scores": {}, "script_share": 0.0, "script": False}
    if not text:
        return out
    letters = [ch for ch in text if ch.isalpha()]
    n = max(1, len(letters))
    counts = {k: len(re.findall(rx, text)) for k, rx in _SCRIPTS}
    if counts["ja"]:  # kana define japonês mesmo com kanji
        counts["ja"] += counts["zh"]; counts["zh"] = 0
    k, c = max(counts.items(), key=lambda kv: kv[1])
    if c and c / n >= 0.3:
        out.update(lang=_cyrillic_lang(text.lower()) if k == "cyr" else k, strength=3, script_share=round(c / n, 2), script=True)
        return out
    low = text.lower()
    words = re.findall(r"[a-zà-ÿĀ-ɏḀ-ỿ']+", low)
    scores = {l: sum(1 for w in words if w in sw) for l, sw in _STOP.items()}
    if re.search(r"[ñ¿¡]", low):
        scores["es"] += 1
    if re.search(r"[ãõ]", low):
        scores["pt"] += 1
    top = max(scores.values()) if words else 0
    winners = [l for l, s in scores.items() if s == top] if top else []
    # As listas se sobrepõem (como e para existem em pt e es): empate não decide, e a ordem do dicionário não pode decidir.
    best = winners[0] if len(winners) == 1 else None
    score = top if best else 0
    by_letter = None  # letras que só existem em um idioma valem como evidência mesmo sem palavra-função
    if re.search(r"[ășțţ]", low) and best in (None, "pt", "it"):  # â e î existem também em pt e fr: não decidem
        best = by_letter = "ro"
    if re.search(r"[ığş]", low):
        best = by_letter = "tr"
    if re.search(r"[ąęłńśźż]", low):
        best = by_letter = "pl"
    if re.search(r"[ěřů]", low):
        best = by_letter = "cs"
    if re.search(r"[őű]", low):
        best = by_letter = "hu"
    if re.search(r"[ơưẠ-ỹ]", low):  # sem "đ": existe também em croata e sérvio
        best = by_letter = "vi"
    if re.search(r"ß|ä|ö|ü", low) and best in (None, "en"):
        best = by_letter = "de"
    out.update(lang=best if (score or by_letter) else None, strength=score, scores=scores)
    return out


MISLABEL = {"en", "hi"}  # idiomas que canais deixam como padrão mesmo publicando em outro


def video_lang(row):
    """Idioma provável de um vídeo. Os metadados do YouTube valem, salvo evidência forte do título:
    - escrita própria predominante diferente da declarada (ex.: título em japonês marcado como "en");
    - metadado "en"/"hi" (padrão comum de canal) com o título claramente em outro idioma (≥ 2 palavras-função
      a mais que o declarado): pega reupload dublado e hindi escrito em alfabeto latino;
    - título com ≥ 3 palavras-função de outro idioma e nenhuma do declarado.
    As listas de palavras-função se sobrepõem entre idiomas latinos, então diferenças pequenas não mudam nada."""
    meta = None
    for k in ("lang", "audio_lang", "defaultAudioLanguage", "defaultLanguage"):
        v = row.get(k)
        if v and v not in ("zxx", "und"):
            meta = v.split("-")[0].lower()
            break
    meta = LANG_ALIAS.get(meta, meta) if meta else None
    e = lang_evidence(row.get("title", ""))
    g = e["lang"]
    if not meta:
        return g
    if not g or g == meta:
        return meta
    if e["script"]:
        if g == "ja":  # kana só existe em japonês, mesmo com metadado zh
            return g
        return meta if same_script(meta, g) else g
    sm = e["scores"].get(meta, 0)
    if meta in MISLABEL and e["strength"] >= 2 and e["strength"] >= sm + 2:
        return g
    if e["strength"] >= 3 and sm == 0:
        return g
    return meta


VID_RE = re.compile(r"(?:v=|youtu\.be/|shorts/|live/|embed/)([\w-]{11})")


def vid_of(s):
    """ID de vídeo a partir de ID, URL ou 'v:ID'."""
    s = str(s).strip()
    if s.startswith("v:"):
        s = s[2:]
    m = VID_RE.search(s)
    return m.group(1) if m else s


def protect_ids(argv):
    """IDs de vídeo podem começar com '-' (ex.: -drnncoJNsI) e o argparse os confunde com opções.
    Troca esses tokens por 'v:<id>' antes do parse; use vid_of() para ler."""
    return [("v:" + a) if re.fullmatch(r"-[\w-]{10}", a) and not a.startswith("--") else a for a in argv]


def yt_video_url(vid):
    return f"https://www.youtube.com/watch?v={vid}"


def yt_channel_url(cid):
    return f"https://www.youtube.com/channel/{cid}"


def log(*a):
    print(*a, file=sys.stderr, flush=True)
