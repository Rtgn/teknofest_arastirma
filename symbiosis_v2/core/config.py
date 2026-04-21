"""
Proje kökü, runtime dizini, LCA ve GAMS yolları.
"""

from __future__ import annotations

import os
from pathlib import Path

# symbiosis_v2 kökü (bu dosya: symbiosis_v2/core/config.py)
PACKAGE_ROOT: Path = Path(__file__).resolve().parent.parent
BASE_DIR: Path = PACKAGE_ROOT  # alias

DATA_SCHEMAS_DIR: Path = PACKAGE_ROOT / "data_schemas" / "templates"
RESOURCE_USE_TEMPLATE_PATH: Path = DATA_SCHEMAS_DIR / "resource_use_template.xlsx"
RESOURCE_EMISSION_TEMPLATE_PATH: Path = DATA_SCHEMAS_DIR / "resource_emission_template.xlsx"
RUNTIME_DIR: Path = PACKAGE_ROOT / "data_runtime"
OPTIMIZATION_DIR: Path = PACKAGE_ROOT / "optimization"
GAMS_MODEL_REL: Path = Path("gms") / "new3.gms"
GAMS_BUILD_GDX_REL: Path = Path("gms") / "build_gdx.gms"

# Ortam değişkenleri
ENV_LCA_API_URL = "LCA_API_URL"
ENV_LCA_SERVICE_URL = "LCA_SERVICE_URL"  # geriye dönük
ENV_GAMS_EXE = "GAMS_EXE"
ENV_USE_MOCK_LCA = "USE_MOCK_LCA"
ENV_SYMBIOSIS_STRICT_MATCHES = "SYMBIOSIS_STRICT_MATCHES"
ENV_SKIP_WASTE_LINKS_AUTOGEN = "SYMBIOSIS_SKIP_WASTE_LINKS_AUTOGEN"
# Varsayılan kapalı; SYMBIOSIS_ALLOW_SELF_SYMBIOSIS=1 ile aynı fabrika içi eşleşme açılır
ENV_ALLOW_SELF_SYMBIOSIS = "SYMBIOSIS_ALLOW_SELF_SYMBIOSIS"
# MILP: `pulp` (varsayılan, PuLP+CBC, GAMS lisansı gerekmez) | `gams`
ENV_SYMBIOSIS_SOLVER = "SYMBIOSIS_SOLVER"


def get_lca_api_url() -> str:
    return (
        os.environ.get(ENV_LCA_API_URL)
        or os.environ.get(ENV_LCA_SERVICE_URL)
        or "http://127.0.0.1:8001"
    ).rstrip("/")


def get_gams_exe_path() -> str | None:
    raw = os.environ.get(ENV_GAMS_EXE)
    if raw:
        p = Path(raw.strip().strip('"'))
        if p.is_file():
            return str(p)
        if p.is_dir():
            for name in ("gams.exe", "GAMS.exe", "gams"):
                cand = p / name
                if cand.is_file():
                    return str(cand)
    return None


def resolve_gams_executable() -> str | None:
    """PATH ve yaygın Windows kurulumları (tk_arastirma webapp gams_util ile uyumlu)."""
    import platform
    import shutil

    p = get_gams_exe_path()
    if p and Path(p).is_file():
        return p
    for name in ("gams", "gams.exe"):
        w = shutil.which(name)
        if w:
            return w
    if platform.system() == "Windows":
        for pf in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")):
            if not pf:
                continue
            root = Path(pf) / "GAMS"
            if not root.is_dir():
                continue
            try:
                for ver in sorted(root.iterdir(), reverse=True):
                    exe = ver / "gams.exe"
                    if exe.is_file():
                        return str(exe)
            except OSError:
                continue
    return None


def use_mock_lca() -> bool:
    v = os.environ.get(ENV_USE_MOCK_LCA, "").strip().lower()
    return v in ("1", "true", "yes", "on")


def resolve_symbiosis_solver() -> str:
    """``pulp`` | ``gams``. Varsayılan ``pulp`` (yerel CBC/HiGHS; demo GAMS sınırı yok)."""
    v = os.environ.get(ENV_SYMBIOSIS_SOLVER, "pulp").strip().lower()
    return v if v in ("pulp", "gams") else "pulp"


def allow_self_symbiosis() -> bool:
    """
    False (varsayılan): aynı fabrikada kaynak=hedef (self-simbiyoz) satırları üretilmez ve seçim çıktısına düşmez.
    ``SYMBIOSIS_ALLOW_SELF_SYMBIOSIS=1`` (veya true/yes/on): iç tesis eşleşmelerine izin verilir.
    """
    v = os.environ.get(ENV_ALLOW_SELF_SYMBIOSIS, "").strip().lower()
    if not v:
        return False
    return v in ("1", "true", "yes", "on")


def default_new3_gms_path() -> Path:
    return OPTIMIZATION_DIR / GAMS_MODEL_REL


def default_build_gdx_gms_path() -> Path:
    return OPTIMIZATION_DIR / GAMS_BUILD_GDX_REL
