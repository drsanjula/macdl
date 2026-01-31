"""
MacDL CLI - Command Line Interface

Placeholder for Phase 5 implementation.
"""

import click

from macdl import __version__


@click.group()
@click.version_option(version=__version__, prog_name="MacDL")
def cli():
    """MacDL - A lightweight download manager for macOS"""
    pass


@cli.command()
@click.argument("url")
@click.option("-o", "--output", help="Output directory or filename")
@click.option("-t", "--threads", default=8, help="Number of download threads")
def download(url: str, output: str | None, threads: int):
    """Download a file from URL"""
    click.echo(f"🚀 MacDL v{__version__}")
    click.echo(f"📥 Downloading: {url}")
    click.echo(f"📁 Output: {output or 'current directory'}")
    click.echo(f"🧵 Threads: {threads}")
    click.echo("\n⚠️  Core download engine coming in Phase 2!")


@cli.command()
def gui():
    """Launch the graphical interface"""
    click.echo("🖥️  GUI coming in Phase 7!")


@cli.command()
def config():
    """Configure MacDL settings"""
    from macdl.config import Config
    cfg = Config.load()
    click.echo("⚙️  Current Configuration:")
    click.echo(f"   Download directory: {cfg.download_dir}")
    click.echo(f"   Max concurrent: {cfg.max_concurrent_downloads}")
    click.echo(f"   Threads per download: {cfg.threads_per_download}")


if __name__ == "__main__":
    cli()
