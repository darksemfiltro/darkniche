"""Empacota só o código e os notebooks para enviar ao Colab. Nunca inclui análises, .env, cache nem exemplos.

    python analise-mercado-yt/extras/colab/package_colab.py [--out dist/DarkNiche-Colab.zip]

O ZIP tem requirements.txt na raiz e a skill em analise-mercado-yt/ (scripts, references, assets, agents, extras/colab).
"""
from __future__ import annotations

import argparse
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]  # extras/colab -> extras -> analise-mercado-yt -> raiz do pacote
SKILL = ROOT / "analise-mercado-yt"
EXT = {"scripts": {".py"}, "references": {".md"}, "assets": {".json", ".html", ".js"}, "agents": {".yaml"},
       "extras": {".py", ".md", ".ipynb"}}


def package(output):
    output = Path(output).resolve()
    paths = [ROOT / "README.md", ROOT / "requirements.txt", ROOT / "LICENSE", SKILL / "SKILL.md"]
    for folder, extensions in EXT.items():
        paths.extend(p for p in (SKILL / folder).rglob("*")
                     if p.is_file() and p.suffix in extensions and "__pycache__" not in p.parts)
    payload = []
    for p in sorted(set(q for q in paths if q.exists())):
        if p.is_symlink():
            raise ValueError("Symlinks não são empacotados.")
        data = p.read_bytes()
        if re.search(rb"AIza[A-Za-z0-9_-]{35}", data):
            raise ValueError(f"Possível credencial em {p.name}; pacote não gerado.")
        payload.append((p.relative_to(ROOT).as_posix(), data))
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in payload:
            archive.writestr(name, data)
    return output


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=ROOT / "dist/DarkNiche-Colab.zip")
    print(package(ap.parse_args().out))
