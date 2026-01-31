"""
MacDL CLI - Command Line Interface
"""

import asyncio
import click
from pathlib import Path
from typing import Optional

from macdl import __version__
from macdl.config import Config
from macdl.core import Downloader, DownloadJob, ProgressStats, format_size, format_time
from macdl.plugins import get_registry


@click.group()
@click.version_option(version=__version__, prog_name="MacDL")
def cli():
    """MacDL - A lightweight download manager for macOS"""
    pass


@cli.command()
@click.argument("url")
@click.option("-o", "--output", help="Output directory or filename")
@click.option("-t", "--threads", default=8, help="Number of download threads")
@click.option("-q", "--quiet", is_flag=True, help="Suppress progress output")
def download(url: str, output: str | None, threads: int, quiet: bool):
    """Download a file from URL
    
    Supports direct HTTP/HTTPS links and file hosting sites like GoFile, Bunkr.
    """
    from rich.console import Console
    
    console = Console()
    
    console.print(f"[bold green]🚀 MacDL v{__version__}[/bold green]")
    console.print(f"[dim]📥 URL:[/dim] {url}")
    
    # Parse output path
    output_path = Path(output) if output else None
    
    # Run the async download
    try:
        job = asyncio.run(_download_with_plugin(url, output_path, threads, quiet, console))
        
        if job and job.status.value == "completed":
            console.print(f"\n[bold green]✅ Download complete![/bold green]")
            console.print(f"[dim]📁 Saved to:[/dim] {job.output_path}")
            console.print(f"[dim]📊 Size:[/dim] {format_size(job.downloaded_size)}")
        elif job:
            console.print(f"\n[bold red]❌ Download failed: {job.error_message}[/bold red]")
            
    except Exception as e:
        console.print(f"\n[bold red]❌ Error: {e}[/bold red]")
        raise SystemExit(1)


async def _download_with_plugin(
    url: str,
    output_path: Path | None,
    threads: int,
    quiet: bool,
    console,
) -> Optional[DownloadJob]:
    """Download with plugin support - extracts real URLs from hosting sites"""
    from rich.progress import (
        Progress,
        SpinnerColumn,
        TextColumn,
        BarColumn,
        DownloadColumn,
        TransferSpeedColumn,
        TimeRemainingColumn,
    )
    
    config = Config.load()
    config.threads_per_download = threads
    
    # Check if a plugin handles this URL
    registry = get_registry()
    plugin = registry.get_plugin_for_url(url)
    
    if plugin and plugin.name != "http":
        console.print(f"[dim]🔌 Plugin:[/dim] {plugin.name} ({plugin.description})")
        
        try:
            # Extract real download URLs using plugin
            if not quiet:
                console.print(f"[dim]⏳ Extracting download links...[/dim]")
            
            async with plugin:
                download_infos = await plugin.extract(url)
            
            if not download_infos:
                console.print("[bold red]❌ No downloadable files found[/bold red]")
                return None
            
            console.print(f"[dim]📦 Found:[/dim] {len(download_infos)} file(s)")
            
            # Download each file
            last_job = None
            for i, info in enumerate(download_infos, 1):
                console.print(f"\n[bold][{i}/{len(download_infos)}][/bold] {info.filename}")
                last_job = await _download_single(
                    info.url,
                    output_path,
                    threads,
                    quiet,
                    console,
                    filename=info.filename,
                    extra_headers=info.headers,
                )
            
            return last_job
            
        except Exception as e:
            console.print(f"[bold red]❌ Plugin extraction failed: {e}[/bold red]")
            console.print("[dim]Falling back to direct download...[/dim]")
    
    # Direct download (no plugin or fallback)
    return await _download_single(url, output_path, threads, quiet, console)


async def _download_single(
    url: str,
    output_path: Path | None,
    threads: int,
    quiet: bool,
    console,
    filename: str | None = None,
    extra_headers: dict | None = None,
) -> DownloadJob:
    """Download a single file with progress display"""
    from rich.progress import (
        Progress,
        SpinnerColumn,
        TextColumn,
        BarColumn,
        DownloadColumn,
        TransferSpeedColumn,
        TimeRemainingColumn,
    )
    
    config = Config.load()
    config.threads_per_download = threads
    
    async with Downloader(config=config) as dl:
        # Get file info first
        info = await dl.get_file_info(url, extra_headers)
        display_name = filename or info.filename
        
        if not quiet:
            console.print(f"[dim]📄 File:[/dim] {display_name}")
            console.print(f"[dim]📊 Size:[/dim] {format_size(info.size) if info.size else 'Unknown'}")
            console.print(f"[dim]🧵 Threads:[/dim] {threads}")
            console.print(f"[dim]🔄 Resume:[/dim] {'Supported' if info.resume_supported else 'Not supported'}")
        
        if quiet:
            return await dl.download(url, output_path=output_path, filename=filename, headers=extra_headers)
        
        # With progress display
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.fields[filename]}"),
            BarColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            console=console,
        )
        
        with progress:
            task_id = progress.add_task(
                "Downloading",
                filename=display_name,
                total=info.size or 0,
            )
            
            def on_progress(job: DownloadJob, stats: ProgressStats):
                progress.update(task_id, completed=stats.downloaded)
            
            dl.progress_callback = on_progress
            
            return await dl.download(url, output_path=output_path, filename=filename, headers=extra_headers)


@cli.command()
def gui():
    """Launch the graphical interface"""
    click.echo("🖥️  GUI coming in Phase 7!")


@cli.command()
def config():
    """Show current configuration"""
    from rich.console import Console
    from rich.table import Table
    
    console = Console()
    cfg = Config.load()
    
    table = Table(title="MacDL Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Download Directory", cfg.download_dir)
    table.add_row("Max Concurrent Downloads", str(cfg.max_concurrent_downloads))
    table.add_row("Threads per Download", str(cfg.threads_per_download))
    table.add_row("Chunk Size", format_size(cfg.chunk_size))
    table.add_row("Timeout", f"{cfg.timeout}s")
    table.add_row("Max Retries", str(cfg.max_retries))
    table.add_row("Enabled Plugins", ", ".join(cfg.enabled_plugins))
    
    console.print(table)


@cli.command()
def plugins():
    """List available plugins"""
    from rich.console import Console
    from rich.table import Table
    
    console = Console()
    registry = get_registry()
    
    table = Table(title="Available Plugins")
    table.add_column("Name", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Domains", style="green")
    
    for plugin_info in registry.list_plugins():
        domains = ", ".join(plugin_info["domains"][:3])
        if len(plugin_info["domains"]) > 3:
            domains += f" (+{len(plugin_info['domains']) - 3} more)"
        table.add_row(
            plugin_info["name"],
            plugin_info["description"],
            domains or "(all URLs)",
        )
    
    console.print(table)


@cli.command()
@click.argument("urls", nargs=-1)
@click.option("-f", "--file", "url_file", type=click.Path(exists=True), help="File containing URLs")
@click.option("-o", "--output", help="Output directory")
@click.option("-t", "--threads", default=8, help="Number of download threads")
def batch(urls: tuple[str, ...], url_file: str | None, output: str | None, threads: int):
    """Download multiple files"""
    from rich.console import Console
    
    console = Console()
    
    # Collect URLs
    all_urls = list(urls)
    
    if url_file:
        with open(url_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    all_urls.append(line)
    
    if not all_urls:
        console.print("[bold red]❌ No URLs provided[/bold red]")
        raise SystemExit(1)
    
    console.print(f"[bold green]🚀 MacDL v{__version__}[/bold green]")
    console.print(f"[dim]📦 Batch download:[/dim] {len(all_urls)} URLs")
    
    # Download each URL
    output_path = Path(output) if output else None
    success = 0
    failed = 0
    
    for i, url in enumerate(all_urls, 1):
        console.print(f"\n[bold]━━━ [{i}/{len(all_urls)}] ━━━[/bold]")
        console.print(f"[dim]URL:[/dim] {url}")
        try:
            job = asyncio.run(_download_with_plugin(url, output_path, threads, False, console))
            if job and job.status.value == "completed":
                success += 1
            else:
                failed += 1
        except Exception as e:
            console.print(f"[red]Failed: {e}[/red]")
            failed += 1
    
    console.print(f"\n[bold]📊 Summary:[/bold] {success} succeeded, {failed} failed")


if __name__ == "__main__":
    cli()
