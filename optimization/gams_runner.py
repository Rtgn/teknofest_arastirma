"""
gams.exe çalıştırma ve çalışma dizini.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Optional

from core.config import resolve_gams_executable

logger = logging.getLogger(__name__)

# https://www.gams.com/latest/docs/UG_GAMSReturnCodes.html
_GAMS_RETURN_HINTS_TR: dict[int, str] = {
    2: "derleme hatası (compilation)",
    3: "çalışma hatası (execution)",
    5: "dosya hatası (file)",
    6: "komut satırı parametre hatası",
    7: "lisans hatası — geçersiz/süresi dolmuş/eksik lisans; GAMS License Manager veya gamslice.txt kontrol edin",
    8: "GAMS sistem hatası",
    9: "GAMS başlatılamadı",
}


def _read_lst_tail(cwd: Path, gms_name: str, max_lines: int = 80) -> str:
    base = Path(gms_name).stem
    lst = cwd / f"{base}.lst"
    if not lst.is_file():
        return ""
    try:
        with open(lst, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            chunk = min(size, 384_000)
            f.seek(max(0, size - chunk))
            data = f.read().decode("utf-8", errors="replace")
    except OSError:
        return ""
    lines = data.splitlines()
    tail = lines[-max_lines:] if len(lines) > max_lines else lines
    return "\n".join(tail).strip()


def _format_gams_failure(
    cwd: Path,
    gms_name: str,
    returncode: int,
    proc: subprocess.CompletedProcess,
) -> str:
    hint = _GAMS_RETURN_HINTS_TR.get(returncode, "")
    if hint:
        hint = f" [{hint}]"
    stream = (proc.stderr or "") + "\n" + (proc.stdout or "")
    stream = stream.strip()
    if len(stream) > 3500:
        stream = stream[:3500] + "\n…"
    lst_tail = _read_lst_tail(cwd, gms_name)
    parts = [f"kod={returncode}{hint}"]
    if stream:
        parts.append(stream)
    if lst_tail:
        parts.append(f"--- {Path(gms_name).stem}.lst (son satırlar) ---\n{lst_tail}")
    elif not stream:
        parts.append(
            f"(stdout/stderr boş; ayrıntı için bakın: {cwd / Path(gms_name).stem}.lst)"
        )
    return "\n\n".join(parts)


def is_gams_available() -> bool:
    return resolve_gams_executable() is not None


def run_gams_model(
    cwd: Path,
    gms_name: str = "new3.gms",
    *,
    list_options: str = "lo=2",
    timeout_sec: int = 600,
) -> subprocess.CompletedProcess:
    exe = resolve_gams_executable()
    if not exe:
        raise FileNotFoundError(
            "GAMS bulunamadı. GAMS_EXE ortam değişkenini ayarlayın veya PATH'e ekleyin."
        )
    gms = cwd / gms_name
    if not gms.is_file():
        raise FileNotFoundError(f"GAMS model dosyası yok: {gms}")

    cmd = [exe, str(gms), list_options]
    logger.info("GAMS: cwd=%s cmd=%s", cwd, cmd)
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout_sec,
        shell=False,
    )
    if proc.returncode != 0:
        detail = _format_gams_failure(cwd, gms_name, proc.returncode, proc)
        logger.error("GAMS çıkış kodu %s\n%s", proc.returncode, detail[:6000])
        raise RuntimeError(f"GAMS hata: {detail[:4000]}")
    return proc


def ensure_model_file(target_dir: Path, source_gms: Path) -> Path:
    """Kaynak new3.gms yoksa hata; varsa hedefe kopyala."""
    import shutil

    if not source_gms.is_file():
        raise FileNotFoundError(f"Kaynak GAMS modeli yok: {source_gms}")
    dst = target_dir / source_gms.name
    target_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_gms, dst)
    return dst
