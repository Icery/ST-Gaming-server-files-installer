"""
建置腳本 - 將 config.py 和檔案資料嵌入到 installer
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
    """讀取 config.py 內容"""
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
    
    # 檢查必要檔案
    if not os.path.isfile(CONFIG_FILE):
        print(f"\n錯誤: 找不到 {CONFIG_FILE}")
        return False
    
    if not os.path.isfile(TEMPLATE_FILE):
        print(f"\n錯誤: 找不到 {TEMPLATE_FILE}")
        return False
    
    # 檢查來源資料夾
    if not os.path.isdir(SOURCE_DIR):
        print(f"\n錯誤: 找不到 {SOURCE_DIR} 資料夾")
        os.makedirs(SOURCE_DIR, exist_ok=True)
        print(f"已建立 {SOURCE_DIR} 資料夾，請放入檔案後重新執行")
        return False
    
    file_count = sum(len(files) for _, _, files in os.walk(SOURCE_DIR))
    if file_count == 0:
        print(f"\n錯誤: {SOURCE_DIR} 資料夾是空的")
        return False
    
    print(f"\n打包 {file_count} 個檔案...")
    print("-" * 40)
    
    # 壓縮檔案
    zip_data = create_zip_from_folder(SOURCE_DIR)
    b64_data = base64.b64encode(zip_data).decode('utf-8')
    
    print("-" * 40)
    print(f"壓縮完成: {len(zip_data):,} -> {len(b64_data):,} bytes")
    
    # 讀取 config
    print(f"\n讀取 {CONFIG_FILE}...")
    config_content = read_config()
    
    # 讀取 installer 模板
    print(f"讀取 {TEMPLATE_FILE}...")
    with open(TEMPLATE_FILE, 'r', encoding='utf-8') as f:
        installer_content = f.read()
    
    # 移除 import config 那行，改為直接嵌入 config 內容
    installer_content = installer_content.replace(
        '# 從 config 讀取設定 (build.py 會將此區塊替換為 config.py 內容)\nfrom config import *',
        f'# ============ Config (自動嵌入) ============\n{config_content}'
    )
    
    # 替換版本和資料
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
    
    # 寫入輸出檔
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(output)
    
    print(f"\n產生: {OUTPUT_FILE}")
    print(f"\n打包 exe:")
    print(f"  pyinstaller --onefile --windowed --name STG-Installer-{version} {OUTPUT_FILE}")
    
    return True

if __name__ == "__main__":
    build_installer()