"""Formatare de date în limba română, fără dependență de locale-ul sistemului."""
from datetime import date

MONTHS = [
    "ianuarie", "februarie", "martie", "aprilie", "mai", "iunie",
    "iulie", "august", "septembrie", "octombrie", "noiembrie", "decembrie",
]
WEEKDAYS = ["Luni", "Marți", "Miercuri", "Joi", "Vineri", "Sâmbătă", "Duminică"]


def format_date_long(d: date) -> str:
    """Ex.: «Sâmbătă, 5 iulie 2026»"""
    return f"{WEEKDAYS[d.weekday()]}, {d.day} {MONTHS[d.month - 1]} {d.year}"


def format_date_short(d: date) -> str:
    """Ex.: «Sâmbătă, 5 iulie»"""
    return f"{WEEKDAYS[d.weekday()]}, {d.day} {MONTHS[d.month - 1]}"


def format_month_year(year: int, month: int) -> str:
    """Ex.: «Iulie 2026»"""
    return f"{MONTHS[month - 1].capitalize()} {year}"
