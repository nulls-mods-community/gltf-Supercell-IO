#!/usr/bin/env python3
"""Build script for gltf_supercell_io Blender extension.

Downloads Python wheels at build time and packages the extension.
Wheels are never stored in git - they are generated during build.

Exception: neko_web_api_client is a custom OpenAPI-generated client
not on PyPI, so its wheel is committed to git.
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ADDON_DIR = REPO_ROOT / "gltf_supercell_io"
WHEELS_DIR = ADDON_DIR / "wheels"
VENDOR_DIR = ADDON_DIR / "vendor"
WHEELS_REQUIREMENTS = REPO_ROOT / "requirements-wheels.txt"
MANIFEST_PATH = ADDON_DIR / "blender_manifest.toml"


def download_wheels():
    """Download wheels using pip into the wheels directory.

    Uses pip's -d/--dest to get .whl files, which Blender's
    extension system requires.
    """
    print(f"Downloading wheels to {WHEELS_DIR}...")

    # Clean existing wheels
    if WHEELS_DIR.exists():
        shutil.rmtree(WHEELS_DIR)
    WHEELS_DIR.mkdir(parents=True)

    # Copy the custom neko wheel from vendor (not on PyPI)
    neko_wheel_name = "neko_web_api_client-1.1.0-py3-none-any.whl"
    neko_src = VENDOR_DIR / neko_wheel_name
    if neko_src.exists():
        shutil.copy2(neko_src, WHEELS_DIR / neko_wheel_name)
        print(f"  Included (custom): {neko_wheel_name}")
    else:
        print(f"  WARNING: Custom wheel not found in vendor/: {neko_wheel_name}")

    # Use pip download to get .whl files from PyPI
    pip_cmd = shutil.which("pip3") or shutil.which("pip") or "pip"
    result = subprocess.run(
        [
            pip_cmd,
            "download",
            "-d",
            str(WHEELS_DIR),
            "-r",
            str(WHEELS_REQUIREMENTS),
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"pip download failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)

    # List what we got
    wheel_files = sorted(WHEELS_DIR.glob("*.whl"))
    print(f"Found {len(wheel_files)} wheel files:")
    for w in wheel_files:
        print(f"  {w.name}")

    return wheel_files


def update_manifest(wheel_files):
    """Update blender_manifest.toml with actual wheel filenames.

    The manifest uses placeholders that get replaced with actual
    wheel filenames at build time.
    """
    if not MANIFEST_PATH.exists():
        print("No blender_manifest.toml found, skipping update.")
        return

    content = MANIFEST_PATH.read_text()

    # Replace the wheels section with actual files
    # Match from "wheels = [" to the closing "]"
    wheels_block_pattern = r"wheels\s*=\s*\[.*?\]"
    replacement = "wheels = [\n"
    for whl in sorted(wheel_files):
        replacement += f'  "./wheels/{whl.name}",\n'
    replacement += "]"

    new_content = re.sub(
        wheels_block_pattern,
        replacement,
        content,
        flags=re.DOTALL,
    )

    MANIFEST_PATH.write_text(new_content)
    print(f"Updated {MANIFEST_PATH} with {len(wheel_files)} wheels")


def build_addon_zip(tag: str = "dev") -> Path:
    """Build the final .zip file for the Blender extension."""
    print(f"\nBuilding extension zip (tag: {tag})...")

    dist_dir = REPO_ROOT / "dist"
    dist_dir.mkdir(exist_ok=True)

    output_zip = dist_dir / f"gltf_supercell_io_{tag}.zip"

    addon_root = ADDON_DIR

    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(addon_root):
            # Skip __pycache__ and .git
            dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git")]

            for file in files:
                if file.endswith((".pyc", ".pyo")):
                    continue

                file_path = Path(root) / file
                arc_name = file_path.relative_to(REPO_ROOT)

                # Write to zip with correct relative path
                zf.write(file_path, arc_name)

    print(f"Built: {output_zip}")
    print(f"Size: {output_zip.stat().st_size / 1024:.1f} KB")
    return output_zip


def generate_index_json(version: str, zip_path: Path, output_path: Path) -> Path:
    """Generate index.json with resolved archive_url for Blender extensions.

    The archive_url points to a GitHub release download, so it remains
    stable across builds. This allows the index.json to be committed to
    git and used directly by Blender's extension system.
    """
    # Parse the manifest using proper TOML parsing
    with open(MANIFEST_PATH, "rb") as f:
        manifest = tomllib.load(f)

    # Extract metadata from parsed TOML
    addon_id = manifest.get("id", "")
    name = manifest.get("name", "")
    manifest_version = manifest.get("version", "")
    tagline = manifest.get("tagline", "")
    maintainer = manifest.get("maintainer", "")
    addon_type = manifest.get("type", "add-on")
    website = manifest.get("website", "")
    blender_min = manifest.get("blender_version_min", "")
    license_list = manifest.get("license", [])
    tags = manifest.get("tags", [])
    permissions = manifest.get("permissions", {})

    # Compute archive hash
    archive_size = zip_path.stat().st_size
    with open(zip_path, "rb") as f:
        archive_hash = "sha256:" + hashlib.sha256(f.read()).hexdigest()

    # Build GitHub release URL from the website field
    archive_filename = f"gltf_supercell_io_{version}.zip"
    if "github.com" in website:
        # Extract owner/repo from GitHub URL
        repo_match = re.search(r"github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$", website)
        if repo_match:
            owner = repo_match.group(1)
            repo = repo_match.group(2)
            archive_url = f"https://github.com/{owner}/{repo}/releases/download/v{version}/{archive_filename}"
        else:
            print(
                f"WARNING: Could not parse GitHub URL from {website}, using local path",
                file=sys.stderr,
            )
            archive_url = f"./{archive_filename}"
    else:
        archive_url = f"./{archive_filename}"

    index_data = {
        "version": "v1",
        "blocklist": [],
        "data": [
            {
                "schema_version": "1.0.0",
                "id": addon_id,
                "name": name,
                "tagline": tagline,
                "version": manifest_version,
                "type": addon_type,
                "maintainer": maintainer,
                "license": license_list,
                "blender_version_min": blender_min,
                "website": website,
                "permissions": permissions,
                "tags": tags,
                "python_versions": ["3"],
                "archive_url": archive_url,
                "archive_size": archive_size,
                "archive_hash": archive_hash,
            }
        ],
    }

    with open(output_path, "w") as f:
        json.dump(index_data, f, indent=2)
        f.write("\n")

    print(f"Generated: {output_path}")
    print(f"  archive_url: {archive_url}")
    print(f"  archive_size: {archive_size}")
    print(f"  archive_hash: {archive_hash}")
    return output_path


def install_into_venv():
    """Install wheels into the project venv for type checking."""
    print("Installing wheels into virtual environment for type checking...")

    # Find the venv
    venv_dir = REPO_ROOT / ".venv"
    if not venv_dir.exists():
        print("ERROR: No .venv found. Create one with: python3 -m venv .venv")
        sys.exit(1)

    # Download wheels to temp dir
    temp_wheels = REPO_ROOT / ".build-wheels"
    if temp_wheels.exists():
        shutil.rmtree(temp_wheels)
    temp_wheels.mkdir(parents=True)

    # Copy custom neko wheel
    neko_wheel_name = "neko_web_api_client-1.1.0-py3-none-any.whl"
    neko_src = VENDOR_DIR / neko_wheel_name
    if neko_src.exists():
        shutil.copy2(neko_src, temp_wheels / neko_wheel_name)

    # Download PyPI wheels
    download_cmd = shutil.which("pip3") or shutil.which("pip") or "pip"
    result = subprocess.run(
        [
            download_cmd,
            "download",
            "-d",
            str(temp_wheels),
            "-r",
            str(WHEELS_REQUIREMENTS),
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"pip download failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)

    # Install into venv using uv (or venv's python + ensurepip)
    uv_cmd = shutil.which("uv")
    python_cmd = (
        str(venv_dir / "bin" / "python3")
        if sys.platform != "win32"
        else str(venv_dir / "Scripts" / "python.exe")
    )

    whl_files = list(temp_wheels.glob("*.whl"))

    if uv_cmd:
        # Use uv to install wheels into venv
        result = subprocess.run(
            [uv_cmd, "pip", "install", "--python", python_cmd]
            + [str(w) for w in whl_files],
            capture_output=True,
            text=True,
        )
    else:
        # Fallback: ensure pip in venv, then install
        subprocess.run([python_cmd, "-m", "ensurepip"], capture_output=True)
        pip_in_venv = (
            str(venv_dir / "bin" / "pip3")
            if sys.platform != "win32"
            else str(venv_dir / "Scripts" / "pip.exe")
        )
        result = subprocess.run(
            [pip_in_venv, "install"] + [str(w) for w in whl_files],
            capture_output=True,
            text=True,
        )

    shutil.rmtree(temp_wheels)

    if result.returncode != 0:
        print(f"install failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)

    print("✅ Wheels installed into venv for type checking.")


def release_build(version: str):
    """Build a release version with stable index.json."""
    print("\n=== Release Build ===")

    # Step 1: Download wheels (generated, never committed except neko)
    wheels = download_wheels()

    if not wheels:
        print("No wheels found! Check requirements-wheels.txt.", file=sys.stderr)
        sys.exit(1)

    # Step 2: Update manifest with actual wheel filenames
    update_manifest(wheels)

    zip_path = build_addon_zip(version)  # tag = version for release

    # Step 4: Generate index.json with resolved archive_url (output to repo root)
    index_path = REPO_ROOT / "index.json"
    generate_index_json(version, zip_path, index_path)

    print("\n✅ Release build complete!")
    print(f"  Zip: {zip_path}")
    print(f"  Index: {index_path}")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "build"
    version = sys.argv[2] if len(sys.argv) > 2 else "dev"

    if mode == "install":
        install_into_venv()
    elif mode == "build":
        # Step 1: Download wheels (generated, never committed except neko)
        wheels = download_wheels()

        if not wheels:
            print("No wheels found! Check requirements-wheels.txt.", file=sys.stderr)
            sys.exit(1)

        # Step 2: Update manifest with actual wheel filenames
        update_manifest(wheels)

        # Step 3: Build the zip
        zip_path = build_addon_zip(version)

        print(f"\n✅ Build complete: {zip_path}")
    elif mode == "release" and version != "dev":
        release_build(version)
    else:
        print(f"Unknown mode: {mode}. Use 'build', 'release', or 'install'.")
        sys.exit(1)
