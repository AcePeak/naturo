"""naturo setup — download naturo_core.dll from GitHub."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import click

from naturo.version import __version__

REPO = "AcePeak/naturo"
DLL_NAME = "naturo_core.dll"
ARTIFACT_NAME = "naturo-core-dll"


def _bin_dir() -> Path:
    """Return the package bin/ directory."""
    return Path(__file__).resolve().parent.parent / "bin"


def _dll_path() -> Path:
    return _bin_dir() / DLL_NAME


def _gh_available() -> bool:
    """Check if the GitHub CLI is installed and authenticated."""
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True, timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _download_via_gh(dest: Path) -> bool:
    """Download DLL using `gh` CLI from the latest successful workflow run."""
    click.echo("Using GitHub CLI to download artifact...")
    with tempfile.TemporaryDirectory() as tmp:
        try:
            # Get the latest successful run on main
            result = subprocess.run(
                [
                    "gh", "run", "list",
                    "--repo", REPO,
                    "--branch", "main",
                    "--status", "success",
                    "--workflow", "build.yml",
                    "--limit", "1",
                    "--json", "databaseId",
                ],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                click.echo(f"  Failed to list runs: {result.stderr.strip()}")
                return False

            import json
            runs = json.loads(result.stdout)
            if not runs:
                click.echo("  No successful runs found on main branch.")
                return False

            run_id = runs[0]["databaseId"]
            click.echo(f"  Found run #{run_id}")

            # Download the artifact
            dl_result = subprocess.run(
                [
                    "gh", "run", "download", str(run_id),
                    "--repo", REPO,
                    "--name", ARTIFACT_NAME,
                    "--dir", tmp,
                ],
                capture_output=True, text=True, timeout=120,
            )
            if dl_result.returncode != 0:
                click.echo(f"  Download failed: {dl_result.stderr.strip()}")
                return False

            # Find the DLL in the downloaded artifacts
            dll_file = _find_dll_in_dir(Path(tmp))
            if not dll_file:
                click.echo("  DLL not found in downloaded artifact.")
                return False

            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dll_file, dest)
            return True

        except (subprocess.TimeoutExpired, Exception) as e:
            click.echo(f"  Error: {e}")
            return False


def _download_via_release(dest: Path) -> bool:
    """Download DLL from the latest GitHub Release using requests."""
    click.echo("Downloading from GitHub Releases...")
    try:
        import requests
    except ImportError:
        click.echo("  'requests' package not installed. Install it: pip install requests")
        return False

    # Try version-tagged release first, then latest
    urls_to_try = [
        f"https://api.github.com/repos/{REPO}/releases/tags/v{__version__}",
        f"https://api.github.com/repos/{REPO}/releases/latest",
    ]

    for api_url in urls_to_try:
        try:
            resp = requests.get(api_url, timeout=15)
            if resp.status_code != 200:
                continue

            release = resp.json()
            tag = release.get("tag_name", "unknown")

            # Look for the DLL or a wheel in the release assets
            for asset in release.get("assets", []):
                name = asset["name"]
                if name == DLL_NAME or name.endswith(".dll"):
                    click.echo(f"  Found {name} in release {tag}")
                    return _download_asset(asset["browser_download_url"], dest)

            # If no bare DLL, look for a wheel that might contain it
            for asset in release.get("assets", []):
                name = asset["name"]
                if name.endswith(".whl") and "win" in name:
                    click.echo(f"  Found wheel {name} in release {tag}")
                    return _extract_dll_from_wheel(asset["browser_download_url"], dest)

        except Exception as e:
            click.echo(f"  Error checking release: {e}")
            continue

    click.echo("  No suitable release found.")
    return False


def _download_via_gh_release(dest: Path) -> bool:
    """Download DLL from GitHub Release using `gh` CLI."""
    click.echo("Trying GitHub CLI for release download...")
    try:
        # Try version-specific tag first
        for tag in [f"v{__version__}", ""]:
            args = ["gh", "release", "download", "--repo", REPO, "--pattern", f"*{DLL_NAME}*", "--dir", str(dest.parent)]
            if tag:
                args.insert(3, tag)

            result = subprocess.run(args, capture_output=True, text=True, timeout=60)
            if result.returncode == 0 and dest.exists():
                return True

        # Try downloading the wheel from release
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                ["gh", "release", "download", "--repo", REPO, "--pattern", "*.whl", "--dir", tmp],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode == 0:
                for whl in Path(tmp).glob("*.whl"):
                    if "win" in whl.name:
                        return _extract_dll_from_local_wheel(whl, dest)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return False


def _download_asset(url: str, dest: Path) -> bool:
    """Download a file from a URL with progress."""
    import requests

    try:
        resp = requests.get(url, stream=True, timeout=60)
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0))
        dest.parent.mkdir(parents=True, exist_ok=True)

        downloaded = 0
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded * 100 // total
                    click.echo(f"\r  Downloading: {pct}%", nl=False)

        click.echo()  # newline after progress
        return True
    except Exception as e:
        click.echo(f"\n  Download failed: {e}")
        return False


def _extract_dll_from_wheel(url: str, dest: Path) -> bool:
    """Download a wheel from URL and extract the DLL."""
    import requests

    with tempfile.TemporaryDirectory() as tmp:
        whl_path = Path(tmp) / "naturo.whl"
        try:
            resp = requests.get(url, stream=True, timeout=120)
            resp.raise_for_status()
            with open(whl_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            return _extract_dll_from_local_wheel(whl_path, dest)
        except Exception as e:
            click.echo(f"  Wheel download failed: {e}")
            return False


def _extract_dll_from_local_wheel(whl_path: Path, dest: Path) -> bool:
    """Extract DLL from a local wheel file."""
    import zipfile

    try:
        with zipfile.ZipFile(whl_path) as zf:
            for name in zf.namelist():
                if name.endswith(DLL_NAME):
                    click.echo(f"  Extracting {DLL_NAME} from wheel...")
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(name) as src, open(dest, "wb") as dst:
                        shutil.copyfileobj(src, dst)
                    return True
        click.echo(f"  {DLL_NAME} not found in wheel.")
        return False
    except Exception as e:
        click.echo(f"  Extraction failed: {e}")
        return False


def _find_dll_in_dir(directory: Path) -> Path | None:
    """Recursively find naturo_core.dll in a directory."""
    for p in directory.rglob(DLL_NAME):
        return p
    return None


@click.command("setup")
@click.option("--force", is_flag=True, help="Re-download even if DLL already exists")
def setup(force: bool):
    """Download naturo_core native engine.

    Detects the current naturo version and downloads the matching
    naturo_core.dll from GitHub. Required for Windows desktop automation
    commands (capture, list, click, etc.).

    On non-Windows platforms, the native DLL is not needed — all
    platform-independent commands work without it.
    """
    if platform.system() != "Windows":
        click.echo(f"naturo v{__version__}")
        click.echo("ℹ️  Native DLL is only required on Windows.")
        click.echo("   All platform-independent commands (mcp, config, etc.) work without it.")
        return

    dest = _dll_path()

    if dest.exists() and not force:
        size_kb = dest.stat().st_size / 1024
        click.echo(f"✅ {DLL_NAME} already exists ({size_kb:.0f} KB)")
        click.echo(f"   Location: {dest}")
        click.echo("   Use --force to re-download.")
        return

    click.echo(f"naturo v{__version__} — downloading {DLL_NAME}")
    click.echo(f"Target: {dest}")
    click.echo()

    use_gh = _gh_available()

    # Strategy 1: gh CLI + release
    if use_gh:
        if _download_via_gh_release(dest):
            _report_success(dest)
            return

    # Strategy 2: GitHub API releases (no auth needed for public repos)
    if _download_via_release(dest):
        _report_success(dest)
        return

    # Strategy 3: gh CLI + workflow artifacts (needs auth)
    if use_gh:
        if _download_via_gh(dest):
            _report_success(dest)
            return

    # All strategies failed
    click.echo()
    click.echo("❌ Could not download naturo_core.dll automatically.")
    click.echo()
    click.echo("Manual options:")
    click.echo(f"  1. Download from: https://github.com/{REPO}/releases")
    click.echo(f"  2. Build from source: cmake -B build -S core && cmake --build build --config Release")
    click.echo(f"  3. Place the DLL at: {dest}")
    sys.exit(1)


def _report_success(dest: Path):
    size_kb = dest.stat().st_size / 1024
    click.echo()
    click.echo(f"✅ {DLL_NAME} downloaded successfully ({size_kb:.0f} KB)")
    click.echo(f"   Location: {dest}")
