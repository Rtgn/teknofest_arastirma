"""
Proje kökü, runtime dizini ve LCA yolları.
"""

from __future__ import annotations

import os
from pathlib import Path

# Proje kökü (bu dosya: core/config.py)
PACKAGE_ROOT: Path = Path(__file__).resolve().parent.parent
BASE_DIR: Path = PACKAGE_ROOT  # alias

DATA_SCHEMAS_DIR: Path = PACKAGE_ROOT / "data_schemas" / "templates"
RESOURCE_USE_TEMPLATE_PATH: Path = DATA_SCHEMAS_DIR / "resource_use_template.xlsx"
RESOURCE_EMISSION_TEMPLATE_PATH: Path = DATA_SCHEMAS_DIR / "resource_emission_template.xlsx"
OUTPUTS_DIR: Path = PACKAGE_ROOT / "outputs"
RUNTIME_DIR: Path = OUTPUTS_DIR / "runtime"
OPTIMIZATION_DIR: Path = PACKAGE_ROOT / "optimization"

# Ortam değişkenleri
ENV_LCA_API_URL = "LCA_API_URL"
ENV_LCA_SERVICE_URL = "LCA_SERVICE_URL"  # geriye dönük
ENV_USE_MOCK_LCA = "USE_MOCK_LCA"
ENV_SYMBIOSIS_STRICT_MATCHES = "SYMBIOSIS_STRICT_MATCHES"
ENV_SKIP_WASTE_LINKS_AUTOGEN = "SYMBIOSIS_SKIP_WASTE_LINKS_AUTOGEN"
# Varsayılan kapalı; SYMBIOSIS_ALLOW_SELF_SYMBIOSIS=1 ile aynı fabrika içi eşleşme açılır
ENV_ALLOW_SELF_SYMBIOSIS = "SYMBIOSIS_ALLOW_SELF_SYMBIOSIS"


def get_lca_api_url() -> str:
    return (
        os.environ.get(ENV_LCA_API_URL)
        or os.environ.get(ENV_LCA_SERVICE_URL)
        or "http://127.0.0.1:5050/api/lca"
    ).rstrip("/")


def use_mock_lca() -> bool:
    v = os.environ.get(ENV_USE_MOCK_LCA, "").strip().lower()
    return v in ("1", "true", "yes", "on")


def allow_self_symbiosis() -> bool:
    """
    False (varsayılan): aynı fabrikada kaynak=hedef (self-simbiyoz) satırları üretilmez ve seçim çıktısına düşmez.
    ``SYMBIOSIS_ALLOW_SELF_SYMBIOSIS=1`` (veya true/yes/on): iç tesis eşleşmelerine izin verilir.
    """
    v = os.environ.get(ENV_ALLOW_SELF_SYMBIOSIS, "").strip().lower()
    if not v:
        return False
    return v in ("1", "true", "yes", "on")
