"""
YYYY-MM periyot string'leri: parse, doğrulama, dosya adı yardımcıları.
"""

from __future__ import annotations

import re


def parse_period(period: str) -> tuple[int, int]:
    """'2026-05' -> (2026, 5)."""
    s = str(period).strip()
    m = re.match(r"^(\d{4})-(\d{1,2})$", s)
    if not m:
        raise ValueError(f"Geçersiz periyot (YYYY-MM): {period!r}")
    y, mo = int(m.group(1)), int(m.group(2))
    if not (1 <= mo <= 12):
        raise ValueError(f"Ay 1–12 olmalı: {period!r}")
    return y, mo


def format_period(year: int, month: int) -> str:
    """(2026, 5) -> '2026-05'."""
    if not (1 <= month <= 12):
        raise ValueError("month 1–12 olmalı")
    return f"{year}-{month:02d}"


def matches_lca_filename(period: str) -> str:
    return f"matches_LCA_{period}.xlsx"


def process_capacity_monthly_filename(period: str) -> str:
    return f"process_capacity_monthly_{period}.xlsx"


def selected_matches_filename(period: str) -> str:
    return f"selected_matches_{period}.xlsx"


def selected_raw_filename(period: str) -> str:
    return f"selected_raw_{period}.xlsx"


def simulation_period(base_period: str, scenario_id: int) -> str:
    return f"{str(base_period).strip()}__SIM{int(scenario_id)}"
