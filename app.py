import os
import sys
import subprocess
import shutil
import json
import re
import threading
import queue
import time

# --- Dependency Check & Auto-Install ---
REQUIRED_PACKAGES = ["customtkinter", "packaging"]

def check_and_install_dependencies():
    """Checks for required packages and installs them if missing using standard tkinter."""
    missing = []
    for pkg in REQUIRED_PACKAGES:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    
    if not missing:
        return

    import tkinter as tk
    from tkinter import messagebox

    root = tk.Tk()
    root.title("Setup Required")
    root.geometry("400x180")
    
    # Simple Style
    root.configure(bg="#2b2b2b")
    fg_color = "#ffffff"
    
    lbl = tk.Label(root, text=f"Wait! We need to setup some engines first.\n\nMissing: {', '.join(missing)}", 
                   justify="center", bg="#2b2b2b", fg=fg_color, font=("Arial", 11))
    lbl.pack(pady=20)

    def install():
        btn_install.config(state="disabled", text="Setting up engines...")
        root.update()
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing)
            messagebox.showinfo("Ready", "Engines are ready! Restarting app...")
            root.destroy()
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception as e:
            messagebox.showerror("Error", f"Failed: {e}")
            btn_install.config(state="normal", text="Try Again")

    btn_install = tk.Button(root, text="Autofix & Start", command=install, 
                            bg="#3b8ed0", fg="white", font=("Arial", 12, "bold"), padx=20, pady=5, borderwidth=0)
    btn_install.pack(pady=10)

    root.mainloop()
    sys.exit()

check_and_install_dependencies()

# --- Imports after dependency check ---
import customtkinter as ctk
from tkinter import messagebox
from packaging import version

# --- THEME CONSTANTS ---
COLOR_BG = "#1e1e1e"        # Main Background
COLOR_SIDEBAR = "#252526"   # Sidebar Background
COLOR_CARD = "#2d2d2d"      # Card/Content Background
COLOR_PRIMARY = "#3b8ed0"   # Action Blue
COLOR_SUCCESS = "#10b981"   # Success Green
COLOR_DANGER = "#ef4444"    # Error Red
COLOR_TEXT = "#e1e1e1"      # Main Text
COLOR_TEXT_DIM = "#a1a1a1"  # Secondary Text

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class InstallManager:
    """Handles system installation logic"""
    APP_NAME = "laravel-bulk-installer"
    
    # Use realpath to resolve symlinks and absolute paths correctly
    INSTALL_DIR = os.path.join(os.path.expanduser("~"), ".local", "share", APP_NAME)
    DESKTOP_DIR = os.path.join(os.path.expanduser("~"), ".local", "share", "applications")
    
    @staticmethod
    def is_installed():
        # Check if running script is inside the install dir
        current_script = os.path.realpath(os.path.abspath(__file__))
        install_dir_real = os.path.realpath(InstallManager.INSTALL_DIR)
        return current_script.startswith(install_dir_real)

    @staticmethod
    def install_system():
        try:
            # 1. Clean previous install
            if os.path.exists(InstallManager.INSTALL_DIR):
                shutil.rmtree(InstallManager.INSTALL_DIR)
            os.makedirs(InstallManager.INSTALL_DIR, exist_ok=True)
            os.makedirs(InstallManager.DESKTOP_DIR, exist_ok=True)
            
            # 2. Copy application file
            current_script = os.path.realpath(os.path.abspath(__file__))
            target_script = os.path.join(InstallManager.INSTALL_DIR, "app.py")
            
            shutil.copy2(current_script, target_script)
            os.chmod(target_script, 0o755)  # Make executable

            # 3. Download Icon
            icon_path = os.path.join(InstallManager.INSTALL_DIR, "laravel-icon.png")
            # Using a reliable source for the Laravel Logo (PNG)
            icon_url = "https://raw.githubusercontent.com/laravel/art/master/logo-lockup/5%20SVG/2%20CMYK/1%20Full%20Color/laravel-logolockup-cmyk-red.svg" 
            # Actually, let's use a PNG from a reliable source to avoid SVG issues on some DEs. 
            # Since I can't easily convert SVG to PNG here without heavy deps, I will try to find a direct PNG or just use the SVG if supported.
            # Most modern Linux DEs support SVG icons.
            
            # Helper to download
            try:
                import urllib.request
                # Using the official mark which is cleaner for an icon
                icon_url = "https://raw.githubusercontent.com/laravel/art/master/logomark/5%20SVG/2%20CMYK/1%20Full%20Color/laravel-logomark-cmyk-red.svg"
                urllib.request.urlretrieve(icon_url, icon_path)
            except Exception as e:
                print(f"Failed to download icon: {e}")
                # Fallback if download fails? We just won't have the custom icon, simple as that.
                icon_path = "utilities-terminal" # Fallback to generic system icon
            
            # 4. Create .desktop file
            exec_cmd = f"{sys.executable} \"{target_script}\""
            
            desktop_content = f"""[Desktop Entry]
Version=1.0
Type=Application
Name=Laravel Installer
GenericName=Laravel Setup Tool
Comment=Bulk Laravel Project Setup Tool
Exec={exec_cmd}
Icon={icon_path}
Categories=Development;
Terminal=false
StartupNotify=true
"""
            desktop_path = os.path.join(InstallManager.DESKTOP_DIR, "laravel-installer.desktop")
            
            with open(desktop_path, "w") as f:
                f.write(desktop_content)
                
            os.chmod(desktop_path, 0o755) # Trust the desktop file
            
            # 5. Attempt to update desktop database
            subprocess.run(["update-desktop-database", InstallManager.DESKTOP_DIR], 
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            return True
            
        except Exception as e:
            raise Exception(f"Installation Step Failed: {str(e)}")

class SidebarButton(ctk.CTkButton):
    """Custom styled sidebar button"""
    def __init__(self, master, text, command, **kwargs):
        super().__init__(master, text=text, command=command, 
                         fg_color="transparent", hover_color="#333333", 
                         anchor="w", height=40, font=("Segoe UI", 13), **kwargs)

class ProjectInstallerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Check Installation Status First
        if not InstallManager.is_installed():
            self.offer_installation()

        self.title("Laravel Bulk Project Installer")
        self.geometry("1000x800")
        self.configure(fg_color=COLOR_BG)

        # Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # State
        self.projects = []
        self.log_queue = queue.Queue()
        self.interaction_queue = queue.Queue()
        self.is_running = False

        self.setup_ui()
        
        # Start loops
        self.after(100, self.process_queues)

    def offer_installation(self):
        """Shows a dialog asking to install to system"""
        # We need a temporary window because the main loop hasn't started
        dialog = ctk.CTk()
        dialog.title("Welcome")
        dialog.geometry("500x300")
        dialog.configure(fg_color=COLOR_BG)
        
        # Center content
        frame = ctk.CTkFrame(dialog, fg_color="transparent")
        frame.place(relx=0.5, rely=0.5, anchor="center")
        
        ctk.CTkLabel(frame, text="Laravel Bulk Installer", font=("Segoe UI", 24, "bold")).pack(pady=10)
        ctk.CTkLabel(frame, text="Would you like to install this tool to your system?\nThis will create a shortcut in your applications menu.", 
                     font=("Segoe UI", 14), text_color=COLOR_TEXT_DIM).pack(pady=20)
        
        def do_install():
            try:
                InstallManager.install_system()
                messagebox.showinfo("Success", "Installation complete!\nYou can now find 'Laravel Installer' in your app menu.")
                dialog.destroy()
                # Relaunch from installed location? Or just let them close.
                sys.exit()
            except Exception as e:
                messagebox.showerror("Error", f"Install failed: {e}")

        def do_try():
            dialog.destroy()

        btn_box = ctk.CTkFrame(frame, fg_color="transparent")
        btn_box.pack(pady=20)
        
        ctk.CTkButton(btn_box, text="Run Once (Try)", fg_color="transparent", border_width=1, command=do_try).pack(side="left", padx=10)
        ctk.CTkButton(btn_box, text="Install to System", fg_color=COLOR_PRIMARY, command=do_install).pack(side="left", padx=10)
        
        dialog.mainloop()

    def setup_ui(self):
        # --- Sidebar ---
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=COLOR_SIDEBAR)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        ctk.CTkLabel(self.sidebar, text="INSTALLER", font=("Segoe UI", 20, "bold"), text_color=COLOR_PRIMARY).pack(pady=(30, 10), padx=20, anchor="w")
        
        ctk.CTkLabel(self.sidebar, text="MENU", font=("Segoe UI", 11, "bold"), text_color=COLOR_TEXT_DIM).pack(pady=(20, 5), padx=20, anchor="w")
        
        SidebarButton(self.sidebar, text="Dashboard / Queue", command=self.show_dashboard).pack(fill="x", padx=10, pady=2)
        SidebarButton(self.sidebar, text="Installation Logs", command=self.show_logs).pack(fill="x", padx=10, pady=2)
        
        # Bottom Version
        ctk.CTkLabel(self.sidebar, text="v2.0.0", font=("Segoe UI", 10), text_color=COLOR_TEXT_DIM).pack(side="bottom", pady=20)

        # --- Content Area ---
        self.content_area = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.content_area.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        
        # Frames
        self.frame_dashboard = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.frame_logs = ctk.CTkFrame(self.content_area, fg_color="transparent")
        
        self.build_dashboard()
        self.build_logs()
        
        self.show_dashboard()

    def build_dashboard(self):
        # Card 1: Add Project
        card_add = ctk.CTkFrame(self.frame_dashboard, fg_color=COLOR_CARD, corner_radius=15)
        card_add.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(card_add, text="Add New Project", font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=20, pady=(20, 15))
        
        grid = ctk.CTkFrame(card_add, fg_color="transparent")
        grid.pack(fill="x", padx=20, pady=(0, 20))
        
        ctk.CTkLabel(grid, text="Project Name", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, sticky="w", padx=5)
        self.entry_name = ctk.CTkEntry(grid, placeholder_text="e.g. ecommerce-api", width=250, border_width=0, fg_color="#3E3E3E", height=35)
        self.entry_name.grid(row=1, column=0, padx=5, pady=(5, 0))

        ctk.CTkLabel(grid, text="Git Repository URL", font=("Segoe UI", 12, "bold")).grid(row=0, column=1, sticky="w", padx=15)
        self.entry_repo = ctk.CTkEntry(grid, placeholder_text="git@github.com...", width=350, border_width=0, fg_color="#3E3E3E", height=35)
        self.entry_repo.grid(row=1, column=1, padx=15, pady=(5, 0))
        
        ctk.CTkButton(grid, text="+ Add to Queue", fg_color=COLOR_PRIMARY, height=35, font=("Segoe UI", 13, "bold"), command=self.add_project).grid(row=1, column=2, padx=15, pady=(5, 0), sticky="s")

        # Card 2: Queue
        card_queue = ctk.CTkFrame(self.frame_dashboard, fg_color=COLOR_CARD, corner_radius=15)
        card_queue.pack(fill="both", expand=True)

        header = ctk.CTkFrame(card_queue, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=20)
        ctk.CTkLabel(header, text="Installation Queue", font=("Segoe UI", 16, "bold")).pack(side="left")
        
        self.lbl_count = ctk.CTkLabel(header, text="0 Projects", font=("Segoe UI", 13), text_color=COLOR_TEXT_DIM)
        self.lbl_count.pack(side="left", padx=10)

        self.queue_container = ctk.CTkScrollableFrame(card_queue, fg_color="transparent", height=300)
        self.queue_container.pack(fill="both", expand=True, padx=10, pady=(0, 20))
        
        # Action Bar
        action_bar = ctk.CTkFrame(self.frame_dashboard, fg_color="transparent")
        action_bar.pack(fill="x", pady=20)
        
        self.btn_run = ctk.CTkButton(action_bar, text="START INSTALLATION", font=("Segoe UI", 14, "bold"), 
                                     height=50, fg_color=COLOR_SUCCESS, hover_color="#059669", command=self.start_thread)
        self.btn_run.pack(fill="x")

    def build_logs(self):
        self.log_textbox = ctk.CTkTextbox(self.frame_logs, font=("Consolas", 12), fg_color="#111111", text_color="#eeeeee", corner_radius=10)
        self.log_textbox.pack(fill="both", expand=True)
        self.log_textbox.tag_config("error", foreground="#ef4444")
        self.log_textbox.tag_config("success", foreground="#10b981")
        self.log_textbox.tag_config("cmd", foreground="#3b8ed0")

    def show_dashboard(self):
        self.frame_logs.pack_forget()
        self.frame_dashboard.pack(fill="both", expand=True)

    def show_logs(self):
        self.frame_dashboard.pack_forget()
        self.frame_logs.pack(fill="both", expand=True)

    def log(self, msg, level="info"):
        self.log_queue.put((msg, level))

    def process_queues(self):
        # Log consumer
        try:
            while True:
                msg, level = self.log_queue.get_nowait()
                self.log_textbox.configure(state="normal")
                ts = time.strftime('%H:%M:%S')
                self.log_textbox.insert("end", f"[{ts}] {msg}\n", level)
                self.log_textbox.see("end")
                self.log_textbox.configure(state="disabled")
        except queue.Empty:
            pass
            
        # Interaction consumer
        try:
            while True:
                atype, payload, event, result = self.interaction_queue.get_nowait()
                if atype == "ask_password":
                    result['val'] = ctk.CTkInputDialog(text="Enter Sudo Password:", title="Auth").get_input()
                elif atype == "ask_dep":
                    result['val'] = messagebox.askyesno("Dependency Missing", f"Install '{payload}' automatically?")
                elif atype == "ask_php":
                    self.popup_php_select(payload, result)
                event.set()
        except queue.Empty:
            pass
            
        self.after(100, self.process_queues)

    def popup_php_select(self, versions, result_ref):
        top = ctk.CTkToplevel(self)
        top.title("Select PHP")
        top.geometry("300x400")
        top.grab_set()
        
        ctk.CTkLabel(top, text="Installation failed.\nSelect a PHP version to retry:", font=("Segoe UI", 13)).pack(pady=20)
        
        selection = ctk.StringVar()
        
        def pick(v):
            selection.set(v)
            top.destroy()
            
        for v in versions:
            ctk.CTkButton(top, text=f"PHP {v}", command=lambda x=v: pick(x), fg_color=COLOR_CARD, border_width=1, border_color="#555").pack(pady=5, padx=20, fill="x")
            
        self.wait_window(top)
        result_ref['val'] = selection.get()

    def add_project(self):
        name = self.entry_name.get().strip()
        repo = self.entry_repo.get().strip()
        
        if not name or not repo: return
        
        self.projects.append({'name': name, 'repo': repo})
        self.refresh_queue_ui()
        self.entry_name.delete(0, "end")
        self.entry_repo.delete(0, "end")

    def refresh_queue_ui(self):
        # Clear
        for widget in self.queue_container.winfo_children(): widget.destroy()
        
        self.lbl_count.configure(text=f"{len(self.projects)} Projects")
        
        for idx, p in enumerate(self.projects):
            row = ctk.CTkFrame(self.queue_container, fg_color="#333", height=50)
            row.pack(fill="x", pady=2)
            
            ctk.CTkLabel(row, text=p['name'], font=("Segoe UI", 13, "bold")).pack(side="left", padx=15)
            ctk.CTkLabel(row, text=p['repo'], font=("Segoe UI", 12), text_color="#aaa").pack(side="left", padx=5)
            
            ctk.CTkButton(row, text="Remove", width=60, height=25, fg_color=COLOR_DANGER, 
                          command=lambda i=idx: self.remove_project(i)).pack(side="right", padx=10, pady=10)

    def remove_project(self, idx):
        self.projects.pop(idx)
        self.refresh_queue_ui()

    def start_thread(self):
        if not self.projects or self.is_running: return
        self.is_running = True
        self.btn_run.configure(state="disabled", text="Running...")
        self.show_logs()
        threading.Thread(target=self.run_install).start()

    # --- Worker Thread ---
    def request(self, atype, payload=None):
        evt = threading.Event()
        res = {}
        self.interaction_queue.put((atype, payload, evt, res))
        evt.wait()
        return res.get('val')

    def run_install(self):
        self.log("--- Starting Bulk Installation ---", "info")
        pwd = self.request("ask_password")
        if not pwd:
            self.log("Cancelled: Password required.", "error")
            self.reset_state()
            return
            
        for proj in self.projects:
            try:
                self.install_project(proj, pwd)
            except Exception as e:
                self.log(f"FAILED {proj['name']}: {e}", "error")
                
        self.log("All operations finished.", "success")
        messagebox.showinfo("Done", "Queue completed.")
        self.reset_state()

    def reset_state(self):
        self.is_running = False
        self.btn_run.configure(state="normal", text="START INSTALLATION")

    def cmd(self, args, pwd=None, check=True):
        cmd_str = " ".join(args)
        self.log(f"EXEC: {cmd_str}", "cmd")
        
        proc = subprocess.run(
            args, 
            input=(pwd+"\n").encode() if pwd else None, 
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        
        if proc.stdout:
            for l in proc.stdout.decode().split("\n"):
                if l.strip(): self.log(f"  {l}")
                
        if proc.returncode != 0:
            err = proc.stderr.decode().strip()
            self.log(f"  ERR: {err}", "error")
            
            # Heuristics
            if "command not found" in err:
                pkg = args[0]
                if self.request("ask_dep", pkg):
                    self.log(f"Auto-installing {pkg}...", "info")
                    self.cmd(["sudo", "-S", "apt", "install", "-y", pkg], pwd, check=True)
                    return self.cmd(args, pwd, check) # Retry
                    
            if check: raise Exception(err)
            
        return proc

    def install_project(self, p, pwd):
        self.log(f"Installing {p['name']}...", "info")
        path = f"/var/www/{p['name']}"
        html = f"/var/www/html/{p['name']}"
        
        # Git
        if not os.path.exists(path): self.cmd(["git", "clone", p['repo'], path])
        else: self.cmd(["git", "-C", path, "pull"])
        
        # Env
        if os.path.exists(f"{path}/.env.example") and not os.path.exists(f"{path}/.env"):
            shutil.copy(f"{path}/.env.example", f"{path}/.env")
            
        # PHP Detect
        php_ver = "8.2"
        if os.path.exists(f"{path}/composer.json"):
            with open(f"{path}/composer.json") as f:
                parsed = json.load(f)
                req = parsed.get("require", {}).get("php", "")
                m = re.search(r"(\d+\.\d+)", req)
                if m: php_ver = m.group(1)
        
        self.log(f"PHP Required: {php_ver}", "info")
        
        # Extensions
        exts = ["curl", "dom", "gd", "mbstring", "zip", "pdo", "mysql"]
        for e in exts:
            self.cmd(["sudo", "-S", "apt", "install", "-y", f"php{php_ver}-{e}"], pwd, check=False)
            
        # Composer
        php_bin = f"/usr/bin/php{php_ver}"
        comp_bin = shutil.which("composer") or "/usr/local/bin/composer"
        
        try:
            self.cmd([php_bin, comp_bin, "install", "-d", path], None, check=True)
        except:
             # Retry logic
             bins = [re.search(r"php(\d+\.\d+)", b).group(1) for b in self.get_php_bins()]
             sel = self.request("ask_php", sorted(list(set(bins))))
             if sel:
                 self.cmd([f"/usr/bin/php{sel}", comp_bin, "install", "-d", path], None)
        
        # Symlink & Perms
        if os.path.islink(html) or os.path.exists(html):
            self.cmd(["sudo", "-S", "rm", "-rf", html], pwd)
        self.cmd(["sudo", "-S", "ln", "-s", f"{path}/public", html], pwd)
        self.cmd(["sudo", "-S", "chmod", "-R", "775", path], pwd)
        self.cmd(["sudo", "-S", "chown", "-R", f"www-data:{os.getlogin()}", path], pwd)
        
        # VHost
        vhost = self.get_vhost_template(p['name'], html, php_ver)
        tmp = f"/tmp/{p['name']}.conf"
        with open(tmp, "w") as f: f.write(vhost)
        
        self.cmd(["sudo", "-S", "mv", tmp, f"/etc/apache2/sites-available/{p['name']}.conf"], pwd)
        self.cmd(["sudo", "-S", "a2ensite", f"{p['name']}.conf"], pwd)
        self.cmd(["sudo", "-S", "systemctl", "reload", "apache2"], pwd)
        
        # Hosts
        self.cmd(["sudo", "-S", "bash", "-c", f"grep -q '{p['name']}.test' /etc/hosts || echo '127.0.0.1 {p['name']}.test' >> /etc/hosts"], pwd)

    def get_php_bins(self):
        import glob
        return glob.glob("/usr/bin/php[0-9]*.[0-9]*")

    def get_vhost_template(self, name, root, php):
        return f"""<VirtualHost *:80>
    ServerName {name}.test
    DocumentRoot {root}
    <Directory {root}>
        AllowOverride All
        Require all granted
    </Directory>
    ErrorLog ${{APACHE_LOG_DIR}}/{name}-error.log
    CustomLog ${{APACHE_LOG_DIR}}/{name}-access.log combined
    <FilesMatch \.php$>
        SetHandler "proxy:unix:/var/run/php/php{php}-fpm.sock|fcgi://localhost/"
    </FilesMatch>
</VirtualHost>"""

if __name__ == "__main__":
    app = ProjectInstallerApp()
    app.mainloop()
