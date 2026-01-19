# build.py
"""
Build script - embeds config.py and file data into installer
"""

import os
import sys
import zipfile
import base64
import io
import subprocess

# ============ Config ============
SOURCE_DIR = "source_files"
CONFIG_FILE = "config.py"
TEMPLATE_FILE = "installer.py"
OUTPUT_FILE = "installer_built.py"

# ============ Git Helpers ============
def run_git_command(args):
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except Exception:
        return None

def get_git_version():
    version = run_git_command(["describe", "--tags", "--abbrev=0"])
    if version:
        return version.lstrip('v')
    
    commit = run_git_command(["rev-parse", "--short", "HEAD"])
    return f"dev-{commit}" if commit else "0.0.0"

def get_git_commit():
    return run_git_command(["rev-parse", "--short", "HEAD"]) or ""

# ============ Build ============
def create_zip_from_folder(folder_path):
    buffer = io.BytesIO()
    
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                arc_name = os.path.relpath(file_path, folder_path)
                zf.write(file_path, arc_name)
                print(f"  + {arc_name}")
    
    return buffer.getvalue()

def read_config():
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return f.read()

def build_installer():
    print("=" * 50)
    print("Building Installer")
    print("=" * 50)
    
    version = get_git_version()
    commit = get_git_commit()
    
    print(f"\nVersion: {version}")
    print(f"Commit:  {commit}")
    
    # Check required files
    if not os.path.isfile(CONFIG_FILE):
        print(f"\nError: {CONFIG_FILE} not found")
        return False
    
    if not os.path.isfile(TEMPLATE_FILE):
        print(f"\nError: {TEMPLATE_FILE} not found")
        return False
    
    # Check source folder
    if not os.path.isdir(SOURCE_DIR):
        print(f"\nError: {SOURCE_DIR} folder not found")
        os.makedirs(SOURCE_DIR, exist_ok=True)
        print(f"Created {SOURCE_DIR} folder, please add files and run again")
        return False
    
    file_count = sum(len(files) for _, _, files in os.walk(SOURCE_DIR))
    if file_count == 0:
        print(f"\nError: {SOURCE_DIR} folder is empty")
        return False
    
    print(f"\nPacking {file_count} files...")
    print("-" * 40)
    
    # Compress files
    zip_data = create_zip_from_folder(SOURCE_DIR)
    b64_data = base64.b64encode(zip_data).decode('utf-8')
    
    print("-" * 40)
    print(f"Compressed: {len(zip_data):,} -> {len(b64_data):,} bytes (base64)")
    
    # Read config
    print(f"\nReading {CONFIG_FILE}...")
    config_content = read_config()
    
    # Read installer template
    print(f"Reading {TEMPLATE_FILE}...")
    with open(TEMPLATE_FILE, 'r', encoding='utf-8') as f:
        installer_content = f.read()
    
    # Replace import with embedded config (using English marker to avoid encoding issues)
    installer_content = installer_content.replace(
        '# CONFIG_IMPORT_MARKER\nfrom config import *',
        f'# ============ Config (embedded) ============\n{config_content}'
    )
    
    # Replace version and data
    output = installer_content.replace(
        'EMBEDDED_DATA = ""',
        f'EMBEDDED_DATA = "{b64_data}"'
    ).replace(
        'APP_VERSION = "1.0.0"',
        f'APP_VERSION = "{version}"'
    ).replace(
        'APP_COMMIT = ""',
        f'APP_COMMIT = "{commit}"'
    )
    
    # Write output
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(output)
    
    print(f"\nGenerated: {OUTPUT_FILE}")
    print(f"\nBuild exe:")
    print(f"  pyinstaller --onefile --windowed --name ST-Gaming-package-{version} {OUTPUT_FILE}")
    
    return True

if __name__ == "__main__":
    success = build_installer()
    sys.exit(0 if success else 1)