"""Centralised Rich logger for pdf-tools."""
from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

console = Console(highlight=False)


# ── Section banners ──────────────────────────────────────────────────────────

def section(title: str) -> None:
    console.print(Panel(f"[bold cyan]{title}[/]", box=box.ROUNDED, expand=False))


def subsection(label: str) -> None:
    console.print(f"\n[bold white]{label}[/]")


# ── Per-file events ───────────────────────────────────────────────────────────

def processing(path: Path) -> None:
    console.print(f"  [dim]↳ processing[/]  [yellow]{path.name}[/]")


def produced(path: Path, extra: str = "") -> None:
    tail = f"  [dim]{extra}[/]" if extra else ""
    console.print(f"  [green]✔ produced[/]   [bold]{path}[/]{tail}")


def skipped(path: Path, reason: str = "") -> None:
    tail = f"  ({reason})" if reason else ""
    console.print(f"  [yellow]⚠ skipped[/]    [dim]{path.name}[/]{tail}")


def error(path: Path, reason: str) -> None:
    console.print(f"  [red]✖ error[/]      [dim]{path.name}[/]  — {reason}")


def info(msg: str) -> None:
    console.print(f"  [dim]{msg}[/]")


# ── Summary table ─────────────────────────────────────────────────────────────

def summary_table(rows: list[tuple[str, ...]], headers: list[str]) -> None:
    """Print a Rich table from (header, *rows) data."""
    tbl = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold magenta")
    for h in headers:
        tbl.add_column(h)
    for row in rows:
        tbl.add_row(*row)
    console.print(tbl)
