"""Exportação portátil de evidências, sem cache global ou arquivos de credenciais."""
from __future__ import annotations

import re
import zipfile
import shutil
from pathlib import Path

SECRET_PATTERN = re.compile(rb"AIza[A-Za-z0-9_-]{35}")
ROOT_FILES = {"plan.json", "proposal.json", "selection.json", "analysis.json", "notas.md",
              "relatorio.html", "relatorio.artifact.html"}
SUFFIXES = {".json", ".md", ".html", ".png", ".jpg", ".jpeg", ".webp", ".vtt", ".srt", ".txt"}


def migrate_legacy_state(old, new):
    """Só quota/cache sem segredos. Não sobrescreve estado já presente nem duplica contadores."""
    old, new = Path(old), Path(new)
    copied = []
    if old.resolve() == new.resolve():
        return copied
    new.mkdir(parents=True, exist_ok=True)
    if (old / "quota.json").is_file() and not (new / "quota.json").exists():
        shutil.copy2(old / "quota.json", new / "quota.json")
        copied.append("quota.json")
    if (old / "cache").is_dir() and not (new / "cache").exists():
        shutil.copytree(old / "cache", new / "cache", ignore=shutil.ignore_patterns('.env', '.env.*'))
        copied.append("cache")
    return copied


def export_run(run, output):
    run, output = Path(run).resolve(), Path(output).resolve()
    files = []
    for p in run.rglob("*"):
        if not p.is_file() or p.is_symlink() or p.resolve() == output:
            continue
        rel = p.relative_to(run)
        if any(part.startswith(".") or part == "__pycache__" for part in rel.parts):
            continue
        allowed = (len(rel.parts) == 1 and rel.name in ROOT_FILES or
                   rel.parts[0] in {"raw", "data", "triage"} and p.suffix.lower() in SUFFIXES)
        if allowed:
            data = p.read_bytes()
            if SECRET_PATTERN.search(data):
                raise ValueError(f"Possível credencial em {rel}; remova-a antes de exportar.")
            files.append((rel.as_posix(), data))
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in files:
            archive.writestr(name, data)
    return output
