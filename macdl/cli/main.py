"""
MacDL CLI - Command Line Interface
"""

import asyncio
import click
from pathlib import Path

from macdl import __version__
from macdl.config import Config
from macdl.core import Downloader, DownloadJob, ProgressStats, format_size, format_time


def create_progress_display():
    """Create a rich progress display for downloads"""
    from rich.console import Console
    from rich.progress import (
        Progress,
        SpinnerColumn,
        TextColumn,
        BarColumn,
        DownloadColumn,
        TransferSpeedColumn,
        TimeRemainingColumn,
    )
    
    console = Console()
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.fields[filename]}"),
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        console=console,
    )
    
    return console, progress


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
    """Download a file from URL"""
    from rich.console import Console
    
    console = Console()
    
    console.print(f"[bold green]🚀 MacDL v{__version__}[/bold green]")
    console.print(f"[dim]📥 URL:[/dim] {url}")
    
    # Parse output path
    output_path = Path(output) if output else None
    
    # Run the async download
    try:
        job = asyncio.run(_download_async(url, output_path, threads, quiet, console))
        
        if job.status.value == "completed":
            console.print(f"\n[bold green]✅ Download complete![/bold green]")
            console.print(f"[dim]📁 Saved to:[/dim] {job.output_path}")
            console.print(f"[dim]📊 Size:[/dim] {format_size(job.downloaded_size)}")
        else:
            console.print(f"\n[bold red]❌ Download failed: {job.error_message}[/bold red]")
            
    except Exception as e:
        console.print(f"\n[bold red]❌ Error: {e}[/bold red]")
        raise SystemExit(1)


async def _download_async(
    url: str,
    output_path: Path | None,
    threads: int,
    quiet: bool,
    console,
) -> DownloadJob:
    """Async download implementation with progress display"""
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
    
    # Track task ID for progress updates
    task_id = None
    
    if quiet:
        # No progress display
        async with Downloader(config=config) as dl:
            return await dl.download(url, output_path=output_path)
    
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
    
    async with Downloader(config=config) as dl:
        # Get file info first
        info = await dl.get_file_info(url)
        console.print(f"[dim]📄 File:[/dim] {info.filename}")
        console.print(f"[dim]📊 Size:[/dim] {format_size(info.size) if info.size else 'Unknown'}")
        console.print(f"[dim]🧵 Threads:[/dim] {threads}")
        console.print(f"[dim]🔄 Resume:[/dim] {'Supported' if info.resume_supported else 'Not supported'}")
        console.print()
        
        with progress:
            task_id = progress.add_task(
                "Downloading",
                filename=info.filename,
                total=info.size or 0,
            )
            
            def on_progress(job: DownloadJob, stats: ProgressStats):
                progress.update(task_id, completed=stats.downloaded)
            
            # Override the downloader's progress callback
            dl.progress_callback = on_progress
            
            return await dl.download(url, output_path=output_path)


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
    console.print(f"[dim]📦 Batch download:[/dim] {len(all_urls)} files")
    
    # Download each URL
    output_path = Path(output) if output else None
    success = 0
    failed = 0
    
    for i, url in enumerate(all_urls, 1):
        console.print(f"\n[bold][{i}/{len(all_urls)}][/bold] {url}")
        try:
            job = asyncio.run(_download_async(url, output_path, threads, False, console))
            if job.status.value == "completed":
                success += 1
            else:
                failed += 1
        except Exception as e:
            console.print(f"[red]Failed: {e}[/red]")
            failed += 1
    
    console.print(f"\n[bold]📊 Summary:[/bold] {success} succeeded, {failed} failed")


if __name__ == "__main__":
    cli()
