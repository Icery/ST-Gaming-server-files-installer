# installer.py
import os
import sys
import stat
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
import zipfile
import base64
import io
import webbrowser

# CONFIG_IMPORT_MARKER
from config import *

# ============ Embedded Data (由 build.py 自動填入) ============
EMBEDDED_DATA = ""
APP_VERSION = "1.0.0"
APP_COMMIT = ""

# ============ Helpers ============
def get_current_dir():
    """取得程式所在目錄"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

def get_embedded_data():
    """取得嵌入的資料"""
    if not EMBEDDED_DATA:
        return None
    return base64.b64decode(EMBEDDED_DATA)

def set_readonly(file_path):
    """設定檔案為唯讀"""
    try:
        # 移除寫入權限，保留讀取和執行權限
        os.chmod(file_path, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        return True
    except Exception:
        return False

def extract_files(target_dir, progress_callback=None):
    """解壓縮檔案到目標資料夾"""
    data = get_embedded_data()
    if not data:
        raise Exception("沒有嵌入的檔案資料")
    
    zip_buffer = io.BytesIO(data)
    
    # 取得唯讀檔案列表（如果有定義）
    readonly_list = []
    if 'READONLY_FILES' in dir():
        readonly_list = READONLY_FILES if READONLY_FILES else []
    
    with zipfile.ZipFile(zip_buffer, 'r') as zf:
        file_list = zf.namelist()
        total = len(file_list)
        
        for i, file_name in enumerate(file_list):
            target_path = os.path.join(target_dir, file_name)
            
            if file_name.endswith('/'):
                os.makedirs(target_path, exist_ok=True)
            else:
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                
                # 如果檔案已存在且是唯讀，先移除唯讀屬性才能覆蓋
                if os.path.exists(target_path):
                    try:
                        os.chmod(target_path, stat.S_IRUSR | stat.S_IWUSR)
                    except Exception:
                        pass
                
                with zf.open(file_name) as source:
                    with open(target_path, 'wb') as target:
                        target.write(source.read())
                
                # 檢查是否需要設為唯讀
                # 比對檔名（支援完整路徑或只有檔名）
                for readonly_file in readonly_list:
                    # 標準化路徑分隔符
                    normalized_name = file_name.replace('\\', '/')
                    normalized_readonly = readonly_file.replace('\\', '/')
                    
                    if normalized_name == normalized_readonly or normalized_name.endswith('/' + normalized_readonly) or normalized_name == normalized_readonly.lstrip('/'):
                        set_readonly(target_path)
                        break
            
            if progress_callback:
                progress_callback(i + 1, total, file_name)

def get_file_count():
    """取得嵌入的檔案數量"""
    data = get_embedded_data()
    if not data:
        return 0
    
    zip_buffer = io.BytesIO(data)
    with zipfile.ZipFile(zip_buffer, 'r') as zf:
        return len([f for f in zf.namelist() if not f.endswith('/')])

def validate_location():
    """驗證程式是否在正確位置"""
    current_dir = get_current_dir()
    
    if REQUIRED_FILE:
        required_path = os.path.join(current_dir, REQUIRED_FILE)
        if not os.path.isfile(required_path):
            return False, current_dir
    
    return True, current_dir

# ============ GUI ============
class InstallerApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"{APP_TITLE} v{APP_VERSION}")
        self.root.geometry("520x550")
        self.root.resizable(False, False)
        
        self.install_dir = None
        self.center_window()
        self.setup_ui()
        self.check_location()
    
    def center_window(self):
        self.root.update_idletasks()
        width = 520
        height = 550
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
    
    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 標題
        title_label = ttk.Label(
            main_frame,
            text=APP_TITLE,
            font=("Microsoft JhengHei", 14, "bold")
        )
        title_label.pack(pady=(0, 5))
        
        # 版本
        version_text = f"v{APP_VERSION}"
        if APP_COMMIT:
            version_text += f" ({APP_COMMIT})"
        
        version_label = ttk.Label(
            main_frame,
            text=version_text,
            font=("Arial", 9),
            foreground="gray"
        )
        version_label.pack(pady=(0, 10))
        
        # 說明文字框
        desc_frame = ttk.LabelFrame(main_frame, text="說明", padding=8)
        desc_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        desc_text = tk.Text(
            desc_frame,
            font=("Microsoft JhengHei", 9),
            wrap=tk.WORD,
            height=14,
            relief=tk.FLAT,
            bg=self.root.cget('bg'),
            cursor="arrow"
        )
        desc_text.insert(tk.END, INSTALL_DESCRIPTION.strip())
        desc_text.config(state=tk.DISABLED)
        desc_text.pack(fill=tk.BOTH, expand=True)
        
        # 檔案數量
        file_count = get_file_count()
        info_label = ttk.Label(
            main_frame,
            text=f"將安裝 {file_count} 個檔案",
            font=("Microsoft JhengHei", 9)
        )
        info_label.pack(pady=(0, 5))
        
        # 目前位置
        self.location_var = tk.StringVar(value="檢查中...")
        self.location_label = ttk.Label(
            main_frame,
            textvariable=self.location_var,
            font=("Consolas", 8),
            foreground="gray"
        )
        self.location_label.pack(pady=(0, 10))
        
        # 進度條
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            main_frame,
            variable=self.progress_var,
            maximum=100,
            length=450
        )
        self.progress_bar.pack(pady=(0, 8))
        
        # 狀態
        self.status_var = tk.StringVar(value=STATUS_READY)
        self.status_label = ttk.Label(
            main_frame,
            textvariable=self.status_var,
            font=("Microsoft JhengHei", 9)
        )
        self.status_label.pack(pady=(0, 10))
        
        # 按鈕框架
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=(5, 0))
        
        # 安裝按鈕
        self.install_btn = ttk.Button(
            btn_frame,
            text=BTN_INSTALL,
            command=self.start_install,
            width=15
        )
        self.install_btn.pack(side=tk.LEFT, padx=5)
        
        # 取消按鈕
        self.cancel_btn = ttk.Button(
            btn_frame,
            text=BTN_CANCEL,
            command=self.root.quit,
            width=15
        )
        self.cancel_btn.pack(side=tk.LEFT, padx=5)
    
    def check_location(self):
        """檢查程式位置"""
        valid, current_dir = validate_location()
        self.install_dir = current_dir
        
        # 顯示目前路徑
        display_path = current_dir
        if len(display_path) > 55:
            display_path = "..." + display_path[-52:]
        
        self.location_var.set(f"安裝位置: {display_path}")
        
        if not valid:
            self.status_var.set(STATUS_WRONG_LOCATION)
            self.install_btn.config(state=tk.DISABLED)
            self.location_label.config(foreground="red")
        else:
            self.status_var.set(STATUS_READY)
            self.location_label.config(foreground="green")
    
    def update_progress(self, current, total, filename):
        progress = (current / total) * 100
        self.progress_var.set(progress)
        
        display_name = filename
        if len(display_name) > 45:
            display_name = "..." + display_name[-42:]
        
        self.status_var.set(STATUS_INSTALLING.format(filename=display_name))
        self.root.update()
    
    def start_install(self):
        if not self.install_dir:
            return
        
        self.install_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.DISABLED)
        
        try:
            extract_files(self.install_dir, self.update_progress)
            self.progress_var.set(100)
            self.status_var.set(STATUS_COMPLETE)
            
            # 完成對話框
            complete_msg = COMPLETE_MESSAGE.format(version=APP_VERSION).strip()
            messagebox.showinfo("安裝完成", complete_msg)
            
            # 開啟網站
            if WEBSITE_URL:
                webbrowser.open(WEBSITE_URL)
            
            self.root.quit()
            
        except Exception as e:
            messagebox.showerror("錯誤", f"安裝過程發生錯誤:\n{str(e)}")
            self.status_var.set(STATUS_FAILED)
            self.install_btn.config(state=tk.NORMAL)
            self.cancel_btn.config(state=tk.NORMAL)
    
    def run(self):
        self.root.mainloop()

# ============ Main ============
if __name__ == "__main__":
    if not EMBEDDED_DATA:
        messagebox.showerror(
            "錯誤",
            "此安裝程式沒有包含任何檔案資料。\n請使用 build.py 重新建置。"
        )
        sys.exit(1)
    
    app = InstallerApp()
    app.run()