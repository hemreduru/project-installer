from __future__ import annotations

import queue
import threading
from tkinter import messagebox

import customtkinter as ctk

from .config import ConfigStore
from .constants import (
    APP_NAME,
    APP_VERSION,
    COLOR_BG,
    COLOR_CARD,
    COLOR_DANGER,
    COLOR_PRIMARY,
    COLOR_SIDEBAR,
    COLOR_SUCCESS,
    COLOR_TEXT_DIM,
    COLOR_WARNING,
)
from .installer import InstallerService
from .models import AppConfig, ProjectConfig, ProjectExecution

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class SidebarButton(ctk.CTkButton):
    def __init__(self, master, text, command, **kwargs):
        super().__init__(
            master,
            text=text,
            command=command,
            fg_color="transparent",
            hover_color="#333333",
            anchor="w",
            height=40,
            font=("Segoe UI", 13),
            **kwargs,
        )


class LaravelInstallerApp(ctk.CTk):
    def __init__(self, store: ConfigStore | None = None, installer: InstallerService | None = None):
        super().__init__()
        self.store = store or ConfigStore()
        self.installer = installer or InstallerService()
        self.config_state = self.store.load()

        self.title(APP_NAME)
        self.geometry("1160x860")
        self.configure(fg_color=COLOR_BG)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.log_queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self.project_runs: list[ProjectExecution] = []
        self.is_running = False

        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=COLOR_SIDEBAR)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        self.content_area = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.content_area.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

        self.frame_dashboard = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.frame_logs = ctk.CTkFrame(self.content_area, fg_color="transparent")

        self._build_sidebar()
        self._build_dashboard()
        self._build_logs()
        self._load_projects()
        self.show_dashboard()

        self.after(100, self._process_log_queue)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_sidebar(self) -> None:
        ctk.CTkLabel(self.sidebar, text="LARAVEL", font=("Segoe UI", 20, "bold"), text_color=COLOR_PRIMARY).pack(
            pady=(30, 10), padx=20, anchor="w"
        )
        ctk.CTkLabel(self.sidebar, text="Desktop Installer", font=("Segoe UI", 12), text_color=COLOR_TEXT_DIM).pack(
            padx=20, anchor="w"
        )
        ctk.CTkLabel(self.sidebar, text="MENU", font=("Segoe UI", 11, "bold"), text_color=COLOR_TEXT_DIM).pack(
            pady=(24, 5), padx=20, anchor="w"
        )
        SidebarButton(self.sidebar, text="Dashboard", command=self.show_dashboard).pack(fill="x", padx=10, pady=2)
        SidebarButton(self.sidebar, text="Logs", command=self.show_logs).pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(self.sidebar, text=f"v{APP_VERSION}", font=("Segoe UI", 10), text_color=COLOR_TEXT_DIM).pack(
            side="bottom", pady=20
        )

    def _build_dashboard(self) -> None:
        card_add = ctk.CTkFrame(self.frame_dashboard, fg_color=COLOR_CARD, corner_radius=15)
        card_add.pack(fill="x", pady=(0, 20))
        ctk.CTkLabel(card_add, text="Add Project", font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=20, pady=(20, 15))

        grid = ctk.CTkFrame(card_add, fg_color="transparent")
        grid.pack(fill="x", padx=20, pady=(0, 20))

        self.entry_name = self._add_labeled_entry(grid, "Project Name", "e.g. shop-admin", 0, 0, width=220)
        self.entry_repo = self._add_labeled_entry(grid, "Repository URL", "git@github.com:org/repo.git", 0, 1, width=320)
        self.entry_host = self._add_labeled_entry(grid, "Host (optional)", "shop-admin.test", 0, 2, width=220)
        self.entry_target = self._add_labeled_entry(grid, "Target Dir (optional)", "/var/www/shop-admin", 2, 0, width=420)

        ctk.CTkLabel(grid, text="Default Base Dir", font=("Segoe UI", 12, "bold")).grid(row=2, column=1, sticky="w", padx=15)
        self.entry_base_dir = ctk.CTkEntry(
            grid,
            width=220,
            height=35,
            border_width=0,
            fg_color="#3E3E3E",
        )
        self.entry_base_dir.insert(0, self.config_state.default_base_dir)
        self.entry_base_dir.grid(row=3, column=1, padx=15, pady=(5, 0), sticky="w")

        ctk.CTkButton(
            grid,
            text="+ Add to Queue",
            fg_color=COLOR_PRIMARY,
            height=35,
            font=("Segoe UI", 13, "bold"),
            command=self.add_project,
        ).grid(row=3, column=2, padx=15, pady=(5, 0), sticky="e")

        summary_card = ctk.CTkFrame(self.frame_dashboard, fg_color=COLOR_CARD, corner_radius=15)
        summary_card.pack(fill="x", pady=(0, 20))
        header = ctk.CTkFrame(summary_card, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 8))
        ctk.CTkLabel(header, text="Preparation Summary", font=("Segoe UI", 16, "bold")).pack(side="left")
        ctk.CTkButton(header, text="Refresh", width=90, command=self.refresh_summary).pack(side="right")
        self.summary_textbox = ctk.CTkTextbox(summary_card, height=150, font=("Consolas", 12), fg_color="#111111")
        self.summary_textbox.pack(fill="x", padx=20, pady=(0, 20))
        self.summary_textbox.configure(state="disabled")

        action_bar = ctk.CTkFrame(self.frame_dashboard, fg_color="transparent")
        action_bar.pack(fill="x", pady=20)
        self.btn_run = ctk.CTkButton(
            action_bar,
            text="START INSTALLATION",
            font=("Segoe UI", 14, "bold"),
            height=48,
            fg_color=COLOR_SUCCESS,
            hover_color="#059669",
            command=self.start_installation,
        )
        self.btn_run.pack(fill="x")

        self.btn_retry = ctk.CTkButton(
            action_bar,
            text="RETRY FAILED PROJECTS",
            font=("Segoe UI", 14, "bold"),
            height=48,
            fg_color=COLOR_WARNING,
            hover_color="#d97706",
            command=self.retry_failed_projects,
        )
        self.btn_retry.pack(fill="x", pady=(12, 0))
        self.btn_retry.configure(state="disabled")

        queue_card = ctk.CTkFrame(self.frame_dashboard, fg_color=COLOR_CARD, corner_radius=15)
        queue_card.pack(fill="both", expand=True)
        queue_header = ctk.CTkFrame(queue_card, fg_color="transparent")
        queue_header.pack(fill="x", padx=20, pady=20)
        ctk.CTkLabel(queue_header, text="Project Queue", font=("Segoe UI", 16, "bold")).pack(side="left")
        self.lbl_count = ctk.CTkLabel(queue_header, text="0 Projects", font=("Segoe UI", 13), text_color=COLOR_TEXT_DIM)
        self.lbl_count.pack(side="left", padx=10)
        self.queue_container = ctk.CTkScrollableFrame(queue_card, fg_color="transparent", height=300)
        self.queue_container.pack(fill="both", expand=True, padx=10, pady=(0, 20))

    def _build_logs(self) -> None:
        self.log_textbox = ctk.CTkTextbox(self.frame_logs, font=("Consolas", 12), fg_color="#111111", text_color="#eeeeee", corner_radius=10)
        self.log_textbox.pack(fill="both", expand=True)
        self.log_textbox.tag_config("error", foreground="#ef4444")
        self.log_textbox.tag_config("success", foreground="#10b981")
        self.log_textbox.tag_config("cmd", foreground="#3b8ed0")
        self.log_textbox.tag_config("info", foreground="#e5e7eb")

    def _add_labeled_entry(self, parent, label: str, placeholder: str, row: int, column: int, width: int = 220):
        ctk.CTkLabel(parent, text=label, font=("Segoe UI", 12, "bold")).grid(row=row, column=column, sticky="w", padx=5 if column == 0 else 15)
        entry = ctk.CTkEntry(parent, placeholder_text=placeholder, width=width, border_width=0, fg_color="#3E3E3E", height=35)
        entry.grid(row=row + 1, column=column, padx=5 if column == 0 else 15, pady=(5, 0), sticky="w")
        return entry

    def _load_projects(self) -> None:
        self.refresh_queue_ui()
        self.refresh_summary()

    def _current_projects(self) -> list[ProjectConfig]:
        return self.config_state.projects

    def show_dashboard(self) -> None:
        self.frame_logs.pack_forget()
        self.frame_dashboard.pack(fill="both", expand=True)

    def show_logs(self) -> None:
        self.frame_dashboard.pack_forget()
        self.frame_logs.pack(fill="both", expand=True)

    def log(self, message: str, level: str = "info") -> None:
        self.log_queue.put((message, level))

    def _process_log_queue(self) -> None:
        try:
            while True:
                message, level = self.log_queue.get_nowait()
                self.log_textbox.configure(state="normal")
                self.log_textbox.insert("end", f"{message}\n", level)
                self.log_textbox.see("end")
                self.log_textbox.configure(state="disabled")
        except queue.Empty:
            pass
        self.after(100, self._process_log_queue)

    def add_project(self) -> None:
        project = ProjectConfig(
            name=self.entry_name.get().strip(),
            repo_url=self.entry_repo.get().strip(),
            hostname=self.entry_host.get().strip(),
            target_dir=self.entry_target.get().strip(),
            enabled=True,
        )
        try:
            validated = self.installer.validate_project(project, self.entry_base_dir.get().strip() or self.config_state.default_base_dir)
        except ValueError as exc:
            messagebox.showerror("Invalid project", str(exc))
            return
        self.config_state.default_base_dir = self.entry_base_dir.get().strip() or self.config_state.default_base_dir
        self.config_state.projects.append(validated)
        self._clear_inputs()
        self.persist_config()
        self.refresh_queue_ui()
        self.refresh_summary()

    def remove_project(self, index: int) -> None:
        self.config_state.projects.pop(index)
        self.persist_config()
        self.refresh_queue_ui()
        self.refresh_summary()

    def refresh_queue_ui(self) -> None:
        for widget in self.queue_container.winfo_children():
            widget.destroy()
        self.lbl_count.configure(text=f"{len(self._current_projects())} Projects")
        for idx, project in enumerate(self._current_projects()):
            row = ctk.CTkFrame(self.queue_container, fg_color="#333333", height=56)
            row.pack(fill="x", pady=2)
            text = f"{project.name}  |  {project.hostname}  |  {project.target_dir}"
            ctk.CTkLabel(row, text=text, font=("Segoe UI", 13, "bold")).pack(side="left", padx=15)
            ctk.CTkButton(
                row,
                text="Remove",
                width=80,
                height=28,
                fg_color=COLOR_DANGER,
                command=lambda i=idx: self.remove_project(i),
            ).pack(side="right", padx=10, pady=12)

    def refresh_summary(self) -> None:
        self.config_state.default_base_dir = self.entry_base_dir.get().strip() or self.config_state.default_base_dir
        try:
            summary = self.installer.build_preflight_summary(self._current_projects(), self.config_state.default_base_dir)
        except Exception as exc:
            summary = f"Could not build summary: {exc}"
        self.summary_textbox.configure(state="normal")
        self.summary_textbox.delete("1.0", "end")
        self.summary_textbox.insert("1.0", summary)
        self.summary_textbox.configure(state="disabled")

    def start_installation(self) -> None:
        if not self._current_projects() or self.is_running:
            return
        self.show_logs()
        self.is_running = True
        self.btn_run.configure(state="disabled", text="RUNNING...")
        self.btn_retry.configure(state="disabled")
        self.persist_config()
        threading.Thread(target=self._run_installation, daemon=True).start()

    def _run_installation(self) -> None:
        try:
            self.project_runs = self.installer.execute_projects(
                self._current_projects(),
                self.config_state.default_base_dir,
                self.log,
            )
            failed = [run.project.name for run in self.project_runs if run.failed]
            self.after(0, lambda: self._finish_installation(failed))
        except Exception as exc:
            self.log(str(exc), "error")
            self.after(0, lambda: self._finish_installation(["*"]))

    def _finish_installation(self, failed: list[str]) -> None:
        self.is_running = False
        self.btn_run.configure(state="normal", text="START INSTALLATION")
        if failed:
            self.btn_retry.configure(state="normal")
            messagebox.showwarning("Installation completed with errors", "\n".join(failed))
        else:
            self.btn_retry.configure(state="disabled")
            messagebox.showinfo("Installation completed", "All projects finished successfully.")
        self.refresh_summary()

    def retry_failed_projects(self) -> None:
        failed = [run.project for run in self.project_runs if run.failed]
        if not failed or self.is_running:
            return
        self.show_logs()
        self.is_running = True
        self.btn_run.configure(state="disabled", text="RUNNING...")
        self.btn_retry.configure(state="disabled")

        def worker() -> None:
            try:
                reruns = self.installer.execute_projects(failed, self.config_state.default_base_dir, self.log)
                self.project_runs = reruns
                failed_names = [run.project.name for run in reruns if run.failed]
                self.after(0, lambda: self._finish_installation(failed_names))
            except Exception as exc:
                self.log(str(exc), "error")
                self.after(0, lambda: self._finish_installation(["*"]))

        threading.Thread(target=worker, daemon=True).start()

    def persist_config(self) -> None:
        self.store.save(self.config_state)

    def _clear_inputs(self) -> None:
        for entry in (self.entry_name, self.entry_repo, self.entry_host, self.entry_target):
            entry.delete(0, "end")

    def on_close(self) -> None:
        self.persist_config()
        self.destroy()


def run_app() -> None:
    app = LaravelInstallerApp()
    app.mainloop()
