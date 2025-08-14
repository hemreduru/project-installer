import os
import subprocess
import shutil
import json
import re
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

projects = []  # List of tuples: (app_name, git_repo)

def get_php_version_for_composer(project_path):
    """Read PHP version requirement from composer.json, return default 8.2 if not found"""
    composer_file = os.path.join(project_path, "composer.json")
    if not os.path.exists(composer_file):
        return "8.2"
    with open(composer_file, "r") as f:
        data = json.load(f)
    php_requirement = data.get("require", {}).get("php", "")
    match = re.search(r"(\d+\.\d+)", php_requirement)
    if match:
        return match.group(1)
    return "8.2"

def install_php_extensions(php_version, sudo_password):
    """Install common PHP extensions needed for Laravel projects"""
    extensions = ["curl", "dom", "gd", "xml", "mbstring", "zip", "pdo", "xmlwriter", "xmlreader", "xsl"]
    for ext in extensions:
        try:
            run_sudo_command(["apt-get", "install", "-y", f"php{php_version}-{ext}"], sudo_password)
        except Exception as e:
            messagebox.showwarning("Warning", f"Could not install php{php_version}-{ext}:\n{e}")

def composer_install_with_php(project_path):
    """Run composer install with the PHP version from composer.json (no sudo needed)"""
    php_version = get_php_version_for_composer(project_path)
    php_binary = f"/usr/bin/php{php_version}"
    composer_bin = shutil.which("composer") or "/usr/local/bin/composer"
    subprocess.run([php_binary, composer_bin, "install", "-d", project_path], check=True)

def run_sudo_command(command_list, sudo_password):
    proc = subprocess.run(
        ["sudo", "-S"] + command_list,
        input=(sudo_password + "\n").encode(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        raise Exception(f"Command {' '.join(command_list)} failed:\n{proc.stderr.decode()}")
    return proc.stdout.decode()

def add_project():
    """Add a project to the listbox and internal list"""
    app_name = entry_name.get().strip()
    git_repo = entry_link.get().strip()
    if not app_name or not git_repo:
        messagebox.showerror("Error", "Please fill in both fields.")
        return
    projects.append((app_name, git_repo))
    listbox_projects.insert(tk.END, f"{app_name} -> {git_repo}")
    entry_name.delete(0, tk.END)
    entry_link.delete(0, tk.END)

def setup_projects_bulk():
    """Setup all projects in bulk"""
    if not projects:
        messagebox.showerror("Error", "No projects added.")
        return

    sudo_password = simpledialog.askstring("Sudo Password", "Enter your sudo password:", show='*')
    if not sudo_password:
        messagebox.showerror("Error", "Sudo password is required for system changes.")
        return

    total = len(projects)
    for idx, (app_name, git_repo) in enumerate(projects, 1):
        progress_var.set((idx-1)/total*100)
        root.update_idletasks()
        try:
            setup_single_project(app_name, git_repo, sudo_password)
        except Exception as e:
            messagebox.showerror("Error", f"Project {app_name} failed:\n{e}")

    progress_var.set(100)
    messagebox.showinfo("Success", "All projects processed!")

def setup_single_project(app_name, git_repo, sudo_password):
    """Setup a single Laravel project"""
    project_path = f"/var/www/{app_name}"
    html_symlink = f"/var/www/html/{app_name}"

    # 1. Clone or pull the repository (normal user)
    if not os.path.exists(project_path):
        subprocess.run(["git", "clone", git_repo, project_path], check=True)
    else:
        subprocess.run(["git", "-C", project_path, "pull"], check=True)

    # 2. Copy .env file
    env_example = os.path.join(project_path, ".env.example")
    env_file = os.path.join(project_path, ".env")
    if os.path.exists(env_example) and not os.path.exists(env_file):
        shutil.copy(env_example, env_file)

    # 3. Install PHP extensions before composer
    php_version = get_php_version_for_composer(project_path)
    install_php_extensions(php_version, sudo_password)

    # 4. Composer install
    composer_install_with_php(project_path)

    # 5. Create symbolic link
    if os.path.islink(html_symlink) or os.path.exists(html_symlink):
        run_sudo_command(["rm", "-rf", html_symlink], sudo_password)
    run_sudo_command(["ln", "-s", os.path.join(project_path, "public"), html_symlink], sudo_password)

    # 6. Add to /etc/hosts
    hosts_entry = f"127.0.0.1 {app_name}.test"
    with open("/etc/hosts", "r") as hosts_file:
        hosts_content = hosts_file.read()
    if hosts_entry not in hosts_content:
        run_sudo_command(["bash", "-c", f"echo '{hosts_entry}' >> /etc/hosts"], sudo_password)

    # 7. Set permissions
    run_sudo_command(["chmod", "-R", "775", project_path], sudo_password)
    run_sudo_command(["chown", "-R", f"www-data:{os.getlogin()}", project_path], sudo_password)
    subprocess.run(["git", "config", "--global", "--add", "safe.directory", project_path], check=True)

    # 8. Apache VirtualHost
    vhost_conf = f"""
<VirtualHost *:80>
    ServerName {app_name}.test
    DocumentRoot {html_symlink}

    <Directory {html_symlink}>
        AllowOverride All
        Require all granted
    </Directory>

    ErrorLog ${{APACHE_LOG_DIR}}/{app_name}-error.log
    CustomLog ${{APACHE_LOG_DIR}}/{app_name}-access.log combined

    <FilesMatch \.php$>
        SetHandler "proxy:unix:/var/run/php/php{php_version}-fpm.sock|fcgi://localhost/"
    </FilesMatch>
</VirtualHost>
"""
    conf_tmp = f"/tmp/{app_name}.conf"
    with open(conf_tmp, "w") as conf_file:
        conf_file.write(vhost_conf)

    run_sudo_command(["mv", conf_tmp, f"/etc/apache2/sites-available/{app_name}.conf"], sudo_password)
    run_sudo_command(["a2ensite", f"{app_name}.conf"], sudo_password)
    run_sudo_command(["systemctl", "reload", "apache2"], sudo_password)

# ===== Tkinter UI =====
root = tk.Tk()
root.title("Laravel Bulk Project Setup")
root.geometry("650x450")
root.resizable(False, False)

frame_top = tk.Frame(root)
frame_top.pack(pady=10)

tk.Label(frame_top, text="Application Name:").grid(row=0, column=0, padx=5)
entry_name = tk.Entry(frame_top, width=40)
entry_name.grid(row=0, column=1, padx=5)

tk.Label(frame_top, text="Git Repository URL:").grid(row=1, column=0, padx=5)
entry_link = tk.Entry(frame_top, width=40)
entry_link.grid(row=1, column=1, padx=5)

tk.Button(frame_top, text="Add Project", command=add_project).grid(row=0, column=2, rowspan=2, padx=10)

listbox_projects = tk.Listbox(root, width=90)
listbox_projects.pack(pady=10)

progress_var = tk.DoubleVar()
progress_bar = ttk.Progressbar(root, length=600, variable=progress_var, mode='determinate')
progress_bar.pack(pady=20)

ttk.Button(root, text="Setup All Projects", command=setup_projects_bulk).pack(pady=10)

root.mainloop()
