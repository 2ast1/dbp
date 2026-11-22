"""
Portable Mode GUI for DBP Cleaner.
"""

import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .cleaner import (
    is_dangerous_source_dir,
    is_same_or_subpath,
    perform_cleanup_detailed,
)
from .config import load_config, save_config
from .constants import DBP_DIR
from .i18n import set_language, t
from .system import resource_path, uninstall_application


def _browse_dir(var):
    """Öffnet den Ordner-Dialog und behält den bisherigen Wert bei Abbruch."""
    current = var.get().strip()
    if current and os.path.isdir(current):
        selected = filedialog.askdirectory(initialdir=current)
    else:
        selected = filedialog.askdirectory()
    if selected:
        var.set(selected)


def _run_portable_window(initial_values=None):
    """Erstellt das Portable-Modus-Fenster und gibt ggf. einen Modus-/Sprachwechsel zurück."""
    cfg = load_config()
    root = tk.Tk()
    root.title(t("title_portable"))

    try:
        root.iconbitmap(resource_path("besen.ico"))
    except Exception:
        pass

    root.geometry("580x600")
    root.minsize(520, 520)

    next_action = {"action": None}
    is_running = {"active": False}

    # Initialwerte bestimmen
    vals_src = initial_values or {}
    init_src = vals_src.get("source_dir", cfg.get("source_dir", ""))
    init_tgt = vals_src.get("target_dir", cfg.get("target_dir", ""))
    init_ext = vals_src.get("extensions", cfg.get("extensions", ".pdf, .docx, .xlsx, .jpg, .png, .zip"))
    init_smart = vals_src.get("smart_trash", cfg.get("smart_trash", True))
    init_sub = vals_src.get("include_subfolders", cfg.get("include_subfolders", True))
    init_clean_empty = vals_src.get("clean_empty_folders", cfg.get("clean_empty_folders", True))

    # Formular-Elemente
    ttk.Label(root, text=t("lbl_source")).pack(pady=(10, 0), padx=10, anchor="w")
    src_var = tk.StringVar(value=init_src)
    src_frame = ttk.Frame(root)
    src_frame.pack(fill="x", padx=10)
    ttk.Entry(src_frame, textvariable=src_var).pack(side="left", fill="x", expand=True)
    ttk.Button(src_frame, text=t("btn_browse"), command=lambda: _browse_dir(src_var)).pack(side="right", padx=(5, 0))

    ttk.Label(root, text=t("lbl_target")).pack(pady=(10, 0), padx=10, anchor="w")
    tgt_var = tk.StringVar(value=init_tgt)
    tgt_frame = ttk.Frame(root)
    tgt_frame.pack(fill="x", padx=10)
    ttk.Entry(tgt_frame, textvariable=tgt_var).pack(side="left", fill="x", expand=True)
    ttk.Button(tgt_frame, text=t("btn_browse"), command=lambda: _browse_dir(tgt_var)).pack(side="right", padx=(5, 0))

    ttk.Label(root, text=t("lbl_exts")).pack(pady=(10, 0), padx=10, anchor="w")
    ext_var = tk.StringVar(value=init_ext)
    ttk.Entry(root, textvariable=ext_var).pack(fill="x", padx=10)

    # Optionen: Smart Trash, Unterordner & Leere Ordner
    opt_frame = ttk.Frame(root)
    opt_frame.pack(fill="x", padx=10, pady=5)
    smart_trash_var = tk.BooleanVar(value=init_smart)
    ttk.Checkbutton(opt_frame, text=t("chk_smart_trash"), variable=smart_trash_var).pack(anchor="w")
    subfolders_var = tk.BooleanVar(value=init_sub)
    ttk.Checkbutton(opt_frame, text=t("chk_subfolders"), variable=subfolders_var).pack(anchor="w")
    clean_empty_var = tk.BooleanVar(value=init_clean_empty)
    ttk.Checkbutton(opt_frame, text=t("chk_clean_empty_folders"), variable=clean_empty_var).pack(anchor="w")

    # Log-Ausgabebereich (schreibgeschützt) mit Scrollbar
    log_frame = ttk.Frame(root)
    log_frame.pack(fill="both", expand=True, padx=10, pady=5)
    scrollbar = ttk.Scrollbar(log_frame)
    scrollbar.pack(side="right", fill="y")
    log_text = tk.Text(log_frame, height=12, yscrollcommand=scrollbar.set, state="disabled")
    log_text.pack(side="left", fill="both", expand=True)
    scrollbar.config(command=log_text.yview)

    run_status_var = tk.StringVar(value="")
    ttk.Label(root, textvariable=run_status_var, foreground="#0055aa").pack(pady=(2, 0))

    # Menüleiste
    menubar = tk.Menu(root)
    optmenu = tk.Menu(menubar, tearoff=0)

    def switch_to_config():
        if is_running["active"]:
            return
        next_action["action"] = ("config", None)
        root.destroy()

    def change_lang(new_lang):
        if is_running["active"]:
            return
        cfg["language"] = new_lang
        set_language(new_lang)
        try:
            save_config(cfg)
        except Exception:
            pass
        current_vals = {
            "source_dir": src_var.get().strip(),
            "target_dir": tgt_var.get().strip(),
            "extensions": ext_var.get().strip(),
            "smart_trash": smart_trash_var.get(),
            "include_subfolders": subfolders_var.get(),
            "clean_empty_folders": clean_empty_var.get(),
        }
        next_action["action"] = ("portable", current_vals)
        root.destroy()

    optmenu.add_command(label=t("menu_config"), command=switch_to_config)

    lang_menu = tk.Menu(optmenu, tearoff=0)
    lang_menu.add_command(label="English", command=lambda: change_lang("English"))
    lang_menu.add_command(label="Deutsch", command=lambda: change_lang("Deutsch"))

    optmenu.add_cascade(label=t("menu_language"), menu=lang_menu)
    optmenu.add_separator()
    optmenu.add_command(label=t("menu_uninstall"), command=lambda: uninstall_application(root, lambda: cfg))
    menubar.add_cascade(label=t("menu_options"), menu=optmenu)
    root.config(menu=menubar)

    def set_log_lines(lines):
        log_text.configure(state="normal")
        log_text.delete(1.0, tk.END)
        for line in lines:
            log_text.insert(tk.END, line + "\n")
        log_text.see(tk.END)
        log_text.configure(state="disabled")

    exec_btn = ttk.Button(root, text=t("btn_execute"))

    def set_busy(busy):
        is_running["active"] = busy
        exec_btn.configure(state="disabled" if busy else "normal")
        run_status_var.set(t("status_running") if busy else "")

    def execute():
        if is_running["active"]:
            return

        src = src_var.get().strip()
        tgt = tgt_var.get().strip()

        set_log_lines([])
        if not src or not tgt:
            messagebox.showwarning(t("msg_error_title"), t("msg_error_dirs"))
            return

        if not os.path.exists(src) or not os.path.isdir(src):
            messagebox.showerror(t("msg_error_title"), t("err_src_missing", path=src))
            return

        if is_dangerous_source_dir(src) or is_same_or_subpath(src, DBP_DIR):
            messagebox.showerror(t("msg_error_title"), t("err_src_dangerous", path=src))
            return

        norm_src = os.path.normcase(os.path.realpath(os.path.abspath(src)))
        norm_tgt = os.path.normcase(os.path.realpath(os.path.abspath(tgt)))
        if norm_src == norm_tgt:
            messagebox.showerror(t("msg_error_title"), t("msg_error_same_dirs"))
            return

        if os.path.exists(tgt) and not os.path.isdir(tgt):
            messagebox.showerror(t("msg_error_title"), t("err_tgt_not_dir", path=tgt))
            return

        confirmed = messagebox.askyesno(
            t("confirm_portable_title"),
            t("confirm_portable_text"),
            icon="warning",
        )
        if not confirmed:
            return

        temp_config = {
            "source_dir": src,
            "target_dir": tgt,
            "extensions": ext_var.get().strip(),
            "smart_trash": smart_trash_var.get(),
            "include_subfolders": subfolders_var.get(),
            "clean_empty_folders": clean_empty_var.get(),
            "protect_recent_hours": cfg.get("protect_recent_hours", 24),
        }

        set_busy(True)

        def worker():
            res = perform_cleanup_detailed(temp_config, is_portable=True)

            def finish():
                if not root.winfo_exists():
                    return
                set_busy(False)
                lines = res.get("logs", [])
                set_log_lines(lines)
                if res.get("fatal_error"):
                    messagebox.showerror(t("msg_execute_error_title"), lines[-1] if lines else "")

            root.after(0, finish)

        threading.Thread(target=worker, daemon=True).start()

    exec_btn.configure(command=execute)
    exec_btn.pack(pady=10)
    root.mainloop()
    return next_action["action"]


def run_portable_gui(initial_values=None, _return_action=False):
    """Startet die Portable-GUI (iterativ ohne mainloop-Verschachtelung)."""
    if _return_action:
        return _run_portable_window(initial_values)

    from .gui_config import _run_config_window

    mode = "portable"
    vals = initial_values
    while mode:
        if mode == "config":
            res = _run_config_window(vals)
        else:
            res = _run_portable_window(vals)
        if isinstance(res, tuple) and len(res) == 2:
            mode, vals = res
        else:
            mode = None
