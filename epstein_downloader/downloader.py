"""Download functionality using aria2c."""

import os
import subprocess
import shutil
import socket
import urllib.request
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .config import (
    DATASETS,
    DOJ_COOKIE,
    get_zip_url,
    get_magnet_with_trackers,
    TRACKERS,
)

console = Console()


def check_aria2c() -> bool:
    """Check if aria2c is installed and available."""
    return shutil.which("aria2c") is not None


def get_aria2c_install_instructions() -> str:
    """Return installation instructions for aria2c."""
    return """
aria2c is required but not found. Please install it:

Windows (winget):  winget install aria2.aria2
Windows (scoop):   scoop install aria2
macOS (brew):      brew install aria2
Linux (apt):       sudo apt install aria2
Linux (yum):       sudo yum install aria2
"""


def diagnose_torrent_connectivity() -> dict:
    """Diagnose torrent connectivity issues."""
    console.print("\n[bold cyan]=== TORRENT CONNECTIVITY DIAGNOSTICS ===[/bold cyan]\n")

    results = {
        "dht_cache": {"exists": False, "path": None, "size": None},
        "trackers": {},
        "aria2_version": None,
        "network": {},
    }

    # Check aria2 version
    try:
        result = subprocess.run(["aria2c", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            results["aria2_version"] = version_line
            console.print(f"[green]✓[/green] aria2c installed: {version_line}")
        else:
            console.print("[red]✗[/red] aria2c not found or error")
    except Exception as e:
        console.print(f"[red]✗[/red] Error checking aria2c: {e}")

    # Check DHT cache
    dht_cache_path = Path.home() / ".cache" / "aria2" / "dht.dat"
    results["dht_cache"]["path"] = str(dht_cache_path)
    if dht_cache_path.exists():
        results["dht_cache"]["exists"] = True
        results["dht_cache"]["size"] = dht_cache_path.stat().st_size
        console.print(f"[green]✓[/green] DHT cache exists: {dht_cache_path} ({dht_cache_path.stat().st_size} bytes)")
    else:
        console.print(f"[yellow]⚠[/yellow] DHT cache NOT found: {dht_cache_path}")
        console.print("    [dim]This may cause DHT initialization errors[/dim]")

    # Test trackers
    console.print("\n[bold]Testing Trackers:[/bold]")
    for tracker in TRACKERS:
        tracker_name = tracker.split("://")[1].split(":")[0]
        results["trackers"][tracker_name] = {"reachable": False, "response_time": None}

        if tracker.startswith("http://"):
            try:
                import time
                start = time.time()
                req = urllib.request.Request(tracker, method="GET")
                with urllib.request.urlopen(req, timeout=5) as response:
                    elapsed = time.time() - start
                    results["trackers"][tracker_name]["reachable"] = True
                    results["trackers"][tracker_name]["response_time"] = elapsed
                    console.print(f"  [green]✓[/green] {tracker_name} - {elapsed:.2f}s")
            except Exception as e:
                console.print(f"  [red]✗[/red] {tracker_name} - Error: {str(e)[:50]}")
        elif tracker.startswith("udp://"):
            # UDP trackers cannot be easily tested with HTTP
            console.print(f"  [dim]?[/dim] {tracker_name} - UDP (cannot test with HTTP)")
        else:
            console.print(f"  [dim]?[/dim] {tracker_name} - Unknown protocol")

    # Check network ports
    console.print("\n[bold]Network Port Check:[/bold]")
    ports_to_check = [6918, 6971]  # Default aria2 ports
    for port in ports_to_check:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(("127.0.0.1", port))
                if result == 0:
                    console.print(f"  [green]✓[/green] Port {port} is in use (aria2 may be running)")
                else:
                    console.print(f"  [dim]✓[/dim] Port {port} is available")
        except Exception as e:
            console.print(f"  [red]✗[/red] Port {port} - Error: {e}")

    return results


class Downloader:
    """Handles all download operations."""

    def __init__(self, output_dir: Path, concurrent: int = 5):
        self.output_dir = Path(output_dir)
        self.concurrent = concurrent
        self.torrents_dir = self.output_dir / "torrents"
        self.zips_dir = self.output_dir / "zips"

        # Create directories
        self.torrents_dir.mkdir(parents=True, exist_ok=True)
        self.zips_dir.mkdir(parents=True, exist_ok=True)

    def download_torrent(self, magnet: str, name: str) -> bool:
        """Download a torrent using aria2c."""
        if not check_aria2c():
            console.print(get_aria2c_install_instructions(), style="red")
            return False

        magnet_full = get_magnet_with_trackers(magnet)
        console.print(f"[yellow]Starting torrent: {name}[/yellow]")

        # DIAGNOSTIC: Log magnet link details
        console.print(f"[dim]DEBUG: Original magnet: {magnet[:80]}...[/dim]")
        console.print(f"[dim]DEBUG: Full magnet length: {len(magnet_full)} characters[/dim]")
        console.print(f"[dim]DEBUG: Output directory: {self.torrents_dir}[/dim]")

        # DIAGNOSTIC: Check DHT cache file
        dht_cache_path = Path.home() / ".cache" / "aria2" / "dht.dat"
        if dht_cache_path.exists():
            console.print(f"[dim]DEBUG: DHT cache exists: {dht_cache_path}[/dim]")
            console.print(f"[dim]DEBUG: DHT cache size: {dht_cache_path.stat().st_size} bytes[/dim]")
            # FIX: Detect and remove corrupted DHT cache (empty or too small)
            if dht_cache_path.stat().st_size < 100:
                console.print(f"[yellow]DHT cache appears corrupted (too small), removing...[/yellow]")
                dht_cache_path.unlink()
        else:
            console.print(f"[dim]DEBUG: DHT cache does NOT exist: {dht_cache_path}[/dim]")
            console.print(f"[dim]DEBUG: This may cause DHT initialization error[/dim]")

        # DIAGNOSTIC: Check if output directory exists
        if self.torrents_dir.exists():
            console.print(f"[dim]DEBUG: Output directory exists[/dim]")
        else:
            console.print(f"[dim]DEBUG: Output directory does NOT exist, will be created[/dim]")

        # FIX: Ensure aria2 cache directory exists for DHT
        aria2_cache = Path.home() / ".cache" / "aria2"
        aria2_cache.mkdir(parents=True, exist_ok=True)

        args = [
            "aria2c",
            magnet_full,
            f"--dir={self.torrents_dir}",
            "--seed-time=0",
            "--max-connection-per-server=16",
            "--split=16",
            "--min-split-size=1M",
            "--bt-stop-timeout=600",
            "--bt-tracker-timeout=60",
            "--continue=true",
            "--auto-file-renaming=false",
            "--console-log-level=notice",
            "--summary-interval=5",
            # FIX: Enhanced DHT configuration for better peer discovery
            "--enable-dht=true",
            "--enable-dht6=false",
            "--bt-enable-lpd=true",
            "--bt-max-peers=100",
            "--bt-request-peer-speed-limit=50K",
            f"--dht-file-path={aria2_cache}/dht.dat",
            "--dht-listen-port=6881-6999",
            "--dht-entry-point=router.bittorrent.com:6881",
            "--dht-entry-point6=router.bittorrent.com:6881",
            # FIX: Add more trackers for better peer discovery
            "--bt-tracker-connect-timeout=30",
            "--bt-tracker-interval=60",
        ]

        # DIAGNOSTIC: Log aria2 command
        console.print(f"[dim]DEBUG: aria2c command: {' '.join(args[:3])} ... (truncated)[/dim]")

        try:
            # Run in foreground so user can see progress
            result = subprocess.run(args, check=False)
            console.print(f"[dim]DEBUG: aria2c return code: {result.returncode}[/dim]")
            return result.returncode == 0
        except Exception as e:
            console.print(f"[red]Error downloading torrent: {e}[/red]")
            return False

    def download_zip(self, dataset_num: int) -> bool:
        """Download a ZIP file directly."""
        if not check_aria2c():
            console.print(get_aria2c_install_instructions(), style="red")
            return False

        dataset = DATASETS.get(dataset_num)
        if not dataset or not dataset.zip_available:
            console.print(f"[red]Dataset {dataset_num} ZIP not available[/red]")
            return False

        url = get_zip_url(dataset_num)
        filename = f"DataSet{dataset_num}.zip"
        output_path = self.zips_dir / filename

        if output_path.exists():
            console.print(f"[dim]SKIP: {filename} already exists[/dim]")
            return True

        console.print(f"[yellow]Downloading: {filename}[/yellow]")
        if dataset.zip_size_mb:
            console.print(f"[dim]  Size: ~{dataset.zip_size_mb} MB[/dim]")

        args = [
            "aria2c",
            url,
            f"--dir={self.zips_dir}",
            f"--out={filename}",
            f"--header=Cookie: {DOJ_COOKIE}",
            "--max-connection-per-server=8",
            "--split=8",
            "--min-split-size=10M",
            "--continue=true",
            "--auto-file-renaming=false",
            "--timeout=120",
            "--max-tries=10",
            "--retry-wait=5",
            "--console-log-level=notice",
            "--summary-interval=10",
        ]

        try:
            result = subprocess.run(args, check=False)
            return result.returncode == 0
        except Exception as e:
            console.print(f"[red]Error downloading ZIP: {e}[/red]")
            return False

    def download_all_zips(self) -> dict:
        """Download all available ZIP files."""
        results = {}
        for num, dataset in DATASETS.items():
            if dataset.zip_available:
                console.print(f"\n[bold]Dataset {num}[/bold]")
                results[num] = self.download_zip(num)
        return results

    def download_all_torrents(self) -> dict:
        """Download all available torrents."""
        results = {}
        for num, dataset in DATASETS.items():
            if dataset.magnet:
                console.print(f"\n[bold]Dataset {num} (Torrent)[/bold]")
                results[num] = self.download_torrent(
                    dataset.magnet, f"DataSet{num}"
                )
        return results

    def download_pdf_list(self, urls: List[str], output_dir: Path) -> bool:
        """Download a list of PDF URLs using aria2c."""
        if not check_aria2c():
            console.print(get_aria2c_install_instructions(), style="red")
            return False

        if not urls:
            console.print("[dim]No URLs to download[/dim]")
            return True

        output_dir.mkdir(parents=True, exist_ok=True)

        # Create URL list file for aria2c
        url_list_file = self.output_dir / "pdf-urls-temp.txt"
        with open(url_list_file, "w") as f:
            for url in urls:
                filename = url.split("/")[-1]
                f.write(f"{url}\n")
                f.write(f"  dir={output_dir}\n")
                f.write(f"  out={filename}\n")

        console.print(f"[yellow]Downloading {len(urls)} PDFs...[/yellow]")

        args = [
            "aria2c",
            f"--input-file={url_list_file}",
            f"--header=Cookie: {DOJ_COOKIE}",
            f"--max-concurrent-downloads={self.concurrent}",
            "--max-connection-per-server=4",
            "--continue=true",
            "--auto-file-renaming=false",
            "--timeout=60",
            "--max-tries=5",
            "--retry-wait=3",
            "--console-log-level=notice",
            "--summary-interval=30",
        ]

        try:
            result = subprocess.run(args, check=False)
            # Clean up temp file
            url_list_file.unlink(missing_ok=True)
            return result.returncode == 0
        except Exception as e:
            console.print(f"[red]Error downloading PDFs: {e}[/red]")
            return False
