from __future__ import annotations

import click


class Console:
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

