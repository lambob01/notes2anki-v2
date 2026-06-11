from __future__ import annotations

from typing import Iterable, Sequence

import click


class Console:
    def progress(self, items: Sequence | Iterable, label: str):
        return click.progressbar(items, label=label, show_pos=True)

    def info(self, message: str) -> None:
        click.secho(message, fg="cyan")

    def success(self, message: str) -> None:
        click.secho(message, fg="green")

    def warn(self, message: str) -> None:
        click.secho(message, fg="yellow")

    def error(self, message: str) -> None:
        click.secho(message, fg="red", err=True)

    def muted(self, message: str) -> None:
        click.secho(message, fg="bright_black")

