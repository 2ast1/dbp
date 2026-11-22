"""
Main Configuration GUI for DBP Cleaner.
"""

import os
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .cleaner import (
    enforce_log_size,
    is_dangerous_source_dir,
    is_same_or_subpath,
    perform_cleanup_detailed,
)
from .config import load_config, save_config
from .constants import DBP_DIR, LOG_FILE, RECENT_HOURS_OPTIONS
from .i18n import set_language, t
from .system import (
    get_autostart_status,
    register_system_integration,
    resource_path,
    setup_autostart,
    uninstall_application,
)


def open_logs():
    """Öffnet die Logdatei im Standard-Texteditor."""
    if not os.path.exists(LOG_FILE):
        messagebox.showinfo(t("title_logs"), t("msg_no_logs"))
        return

    try:
        if sys.platform == "win32":
            os.startfile(LOG_FILE)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", LOG_FILE])
        else:
            subprocess.Popen(["xdg-open", LOG_FILE])
    except Exception as e:
        messagebox.showerror(t("msg_error_title"), t("msg_open_log_error", error=str(e)))


def _browse_dir(var):
    """Öffnet den Ordner-Dialog und behält den bisherigen Wert bei Abbruch."""
    current = var.get().strip()
    if current and os.path.isdir(current):
        selected = filedialog.askdirectory(initialdir=current)
    else:
        selected = filedialog.askdirectory()
    if selected:
        var.set(selected)


def _run_config_window(initial_values=None):
    """Erstellt das Konfigurationsfenster und gibt ggf. einen Modus-/Sprachwechsel zurück."""
    cfg = load_config()
    if initial_values is None:
        register_system_integration(force=False)

    root = tk.Tk()
    root.title(t("title_config"))

    try:
        root.iconbitmap(resource_path("besen.ico"))
    except Exception:
        pass

    root.geometry("600x660")
    root.minsize(540, 620)
    root.columnconfigure(1, weight=1)

    next_action = {"action": None}
    is_running = {"active": False}

    # Initialwerte bestimmen
    vals_src = initial_values or {}
    init_src = vals_src.get("source_dir", cfg.get("source_dir", ""))
    init_tgt = vals_src.get("target_dir", cfg.get("target_dir", ""))
    init_ext = vals_src.get("extensions", cfg.get("extensions", ".pdf, .docx, .xlsx, .jpg, .png, .zip"))
    init_interval = vals_src.get("interval", cfg.get("interval", "startup"))
    init_size = str(vals_src.get("max_log_size", cfg.get("max_log_size", "0.5")))
    init_recent = vals_src.get("protect_recent_hours", cfg.get("protect_recent_hours", 24))
    init_autostart = vals_src.get("autostart", cfg.get("autostart", False))
    init_smart = vals_src.get("smart_trash", cfg.get("smart_trash", True))
    init_sub = vals_src.get("include_subfolders", cfg.get("include_subfolders", True))
    init_clean_empty = vals_src.get("clean_empty_folders", cfg.get("clean_empty_folders", True))

    try:
        init_recent = int(init_recent)
    except (TypeError, ValueError):
        init_recent = 24

    # Grid Layout
    current_row = 0

    # 1. Quellordner
    ttk.Label(root, text=t("lbl_source")).grid(row=current_row, column=0, padx=12, pady=6, sticky="w")
    src_var = tk.StringVar(value=init_src)
    ttk.Entry(root, textvariable=src_var, width=32).grid(row=current_row, column=1, padx=5, sticky="we")
    ttk.Button(root, text=t("btn_browse"), command=lambda: _browse_dir(src_var)).grid(row=current_row, column=2, padx=10, pady=6)
    current_row += 1

    # 2. Zielordner
    ttk.Label(root, text=t("lbl_target")).grid(row=current_row, column=0, padx=12, pady=6, sticky="w")
    tgt_var = tk.StringVar(value=init_tgt)
    ttk.Entry(root, textvariable=tgt_var, width=32).grid(row=current_row, column=1, padx=5, sticky="we")
    ttk.Button(root, text=t("btn_browse"), command=lambda: _browse_dir(tgt_var)).grid(row=current_row, column=2, padx=10, pady=6)
    current_row += 1

    # 3. Dateiendungen
    ttk.Label(root, text=t("lbl_exts")).grid(row=current_row, column=0, padx=12, pady=6, sticky="w")
    ext_var = tk.StringVar(value=init_ext)
    ttk.Entry(root, textvariable=ext_var, width=32).grid(row=current_row, column=1, columnspan=2, padx=5, sticky="we")
    current_row += 1

    # 4. Intervall
    ttk.Label(root, text=t("lbl_interval")).grid(row=current_row, column=0, padx=12, pady=6, sticky="w")
    interval_map = {
        "startup": t("int_startup"),
        "daily": t("int_daily"),
        "weekly": t("int_weekly"),
        "monthly": t("int_monthly"),
    }
    inverse_interval_map = {v: k for k, v in interval_map.items()}
    interval_var = tk.StringVar(value=interval_map.get(init_interval, interval_map["startup"]))
    ttk.Combobox(
        root,
        textvariable=interval_var,
        values=list(interval_map.values()),
        state="readonly",
        width=30,
    ).grid(row=current_row, column=1, columnspan=2, padx=5, sticky="w")
    current_row += 1

    # 5. Maximale Log-Größe
    ttk.Label(root, text=t("lbl_log_size")).grid(row=current_row, column=0, padx=12, pady=6, sticky="w")
    log_size_map = {
        "0.5": t("size_0_5"),
        "1": t("size_1"),
        "5": t("size_5"),
        "10": t("size_10"),
        "unlimited": t("size_unlimited"),
    }
    inverse_log_size_map = {v: k for k, v in log_size_map.items()}
    log_size_var = tk.StringVar(value=log_size_map.get(init_size, log_size_map["0.5"]))
    ttk.Combobox(
        root,
        textvariable=log_size_var,
        values=list(log_size_map.values()),
        state="readonly",
        width=30,
    ).grid(row=current_row, column=1, columnspan=2, padx=5, sticky="w")
    current_row += 1

    # 6. Neue Dateien ins Archiv (< Stunden)
    ttk.Label(root, text=t("lbl_protect_recent")).grid(row=current_row, column=0, padx=12, pady=6, sticky="w")
    recent_map = {
        0: t("recent_0"),
        6: t("recent_6"),
        12: t("recent_12"),
        24: t("recent_24"),
        48: t("recent_48"),
    }
    if init_recent not in recent_map and init_recent >= 0:
        recent_map[init_recent] = f"{init_recent} h"
    ordered_recent_keys = [h for h in RECENT_HOURS_OPTIONS if h in recent_map]
    if init_recent not in ordered_recent_keys and init_recent in recent_map:
        ordered_recent_keys.append(init_recent)
    inverse_recent_map = {v: k for k, v in recent_map.items()}
    recent_var = tk.StringVar(value=recent_map.get(init_recent, recent_map[24]))
    ttk.Combobox(
        root,
        textvariable=recent_var,
        values=[recent_map[k] for k in ordered_recent_keys],
        state="readonly",
        width=30,
    ).grid(row=current_row, column=1, columnspan=2, padx=5, sticky="w")
    current_row += 1

    # Trennlinie
    ttk.Separator(root, orient="horizontal").grid(row=current_row, column=0, columnspan=3, sticky="we", padx=10, pady=8)
    current_row += 1

    # 7. Checkboxen für Optionen
    smart_trash_var = tk.BooleanVar(value=init_smart)
    ttk.Checkbutton(
        root,
        text=t("chk_smart_trash"),
        variable=smart_trash_var,
    ).grid(row=current_row, column=0, columnspan=3, padx=12, pady=4, sticky="w")
    current_row += 1

    subfolders_var = tk.BooleanVar(value=init_sub)
    ttk.Checkbutton(
        root,
        text=t("chk_subfolders"),
        variable=subfolders_var,
    ).grid(row=current_row, column=0, columnspan=3, padx=12, pady=4, sticky="w")
    current_row += 1

    clean_empty_var = tk.BooleanVar(value=init_clean_empty)
    ttk.Checkbutton(
        root,
        text=t("chk_clean_empty_folders"),
        variable=clean_empty_var,
    ).grid(row=current_row, column=0, columnspan=3, padx=12, pady=4, sticky="w")
    current_row += 1

    autostart_var = tk.BooleanVar(value=init_autostart)
    autostart_status_var = tk.StringVar(value="")
    autostart_status_lbl = ttk.Label(root, textvariable=autostart_status_var)

    def refresh_autostart_status(*_args):
        st = get_autostart_status()
        if st["disabled_in_taskmgr"]:
            autostart_status_var.set(t("status_autostart_disabled_tm"))
            autostart_status_lbl.configure(foreground="#b36b00")
        elif st["registered"] and st["valid"] and autostart_var.get():
            autostart_status_var.set(t("status_autostart_active"))
            autostart_status_lbl.configure(foreground="#1b7f37")
        elif autostart_var.get():
            autostart_status_var.set(t("status_autostart_needs_save"))
            autostart_status_lbl.configure(foreground="#b36b00")
        else:
            autostart_status_var.set(t("status_autostart_inactive"))
            autostart_status_lbl.configure(foreground="#555555")

    ttk.Checkbutton(
        root,
        text=t("chk_autostart"),
        variable=autostart_var,
        command=refresh_autostart_status,
    ).grid(row=current_row, column=0, columnspan=3, padx=12, pady=4, sticky="w")
    current_row += 1

    autostart_status_lbl.grid(row=current_row, column=0, columnspan=3, padx=32, pady=(0, 4), sticky="w")
    refresh_autostart_status()
    current_row += 1

    # Trennlinie
    ttk.Separator(root, orient="horizontal").grid(row=current_row, column=0, columnspan=3, sticky="we", padx=10, pady=8)
    current_row += 1

    def collect_current_values():
        return {
            "source_dir": src_var.get().strip(),
            "target_dir": tgt_var.get().strip(),
            "extensions": ext_var.get().strip(),
            "interval": inverse_interval_map.get(interval_var.get(), "startup"),
            "max_log_size": inverse_log_size_map.get(log_size_var.get(), "0.5"),
            "protect_recent_hours": inverse_recent_map.get(recent_var.get(), 24),
            "autostart": autostart_var.get(),
            "smart_trash": smart_trash_var.get(),
            "include_subfolders": subfolders_var.get(),
            "clean_empty_folders": clean_empty_var.get(),
        }

    def apply_inputs():
        cfg.update(collect_current_values())

    def validate_paths(require_source_exists=False):
        src = cfg["source_dir"]
        tgt = cfg["target_dir"]

        if not src or not tgt:
            messagebox.showwarning(t("msg_error_title"), t("msg_error_dirs"))
            return False

        if require_source_exists and (not os.path.exists(src) or not os.path.isdir(src)):
            messagebox.showerror(t("msg_error_title"), t("err_src_missing", path=src))
            return False

        if is_dangerous_source_dir(src) or is_same_or_subpath(src, DBP_DIR):
            messagebox.showerror(t("msg_error_title"), t("err_src_dangerous", path=src))
            return False

        norm_src = os.path.normcase(os.path.realpath(os.path.abspath(src)))
        norm_tgt = os.path.normcase(os.path.realpath(os.path.abspath(tgt)))
        if norm_src == norm_tgt:
            messagebox.showerror(t("msg_error_title"), t("msg_error_same_dirs"))
            return False

        if os.path.exists(tgt) and not os.path.isdir(tgt):
            messagebox.showerror(t("msg_error_title"), t("err_tgt_not_dir", path=tgt))
            return False

        return True

    # Menüleiste
    menubar = tk.Menu(root)
    filemenu = tk.Menu(menubar, tearoff=0)

    def switch_to_portable():
        if is_running["active"]:
            return
        next_action["action"] = ("portable", None)
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
        next_action["action"] = ("config", collect_current_values())
        root.destroy()

    filemenu.add_command(label=t("menu_portable"), command=switch_to_portable)

    lang_menu = tk.Menu(filemenu, tearoff=0)
    lang_menu.add_command(label="English", command=lambda: change_lang("English"))
    lang_menu.add_command(label="Deutsch", command=lambda: change_lang("Deutsch"))

    filemenu.add_cascade(label=t("menu_language"), menu=lang_menu)
    filemenu.add_separator()
    filemenu.add_command(label=t("menu_uninstall"), command=lambda: uninstall_application(root, lambda: cfg))
    menubar.add_cascade(label=t("menu_options"), menu=filemenu)
    root.config(menu=menubar)

    run_status_var = tk.StringVar(value="")
    ttk.Label(root, textvariable=run_status_var, foreground="#0055aa").grid(
        row=current_row, column=0, columnspan=3, padx=12, pady=(0, 2)
    )
    current_row += 1

    # Buttons
    btn_frame = ttk.Frame(root)
    btn_frame.grid(row=current_row, column=0, columnspan=3, pady=8)

    btn_exec = ttk.Button(btn_frame, text=t("btn_execute_normal"))
    btn_save = ttk.Button(btn_frame, text=t("btn_save"))
    btn_logs = ttk.Button(btn_frame, text=t("btn_logs"), command=open_logs)
    btn_uninst = ttk.Button(btn_frame, text=t("btn_uninstall"), command=lambda: uninstall_application(root, lambda: cfg))

    def set_busy(busy):
        is_running["active"] = busy
        state = "disabled" if busy else "normal"
        for b in (btn_exec, btn_save, btn_logs, btn_uninst):
            b.configure(state=state)
        run_status_var.set(t("status_running") if busy else "")

    def execute_normal():
        if is_running["active"]:
            return
        apply_inputs()
        if not validate_paths(require_source_exists=True):
            return

        try:
            save_config(cfg)
        except Exception as e:
            messagebox.showerror(t("msg_error_title"), t("msg_save_error", error=str(e)))
            return

        if sys.platform == "win32":
            setup_autostart(cfg["autostart"], show_errors=False)
        refresh_autostart_status()

        set_busy(True)
        cfg_snapshot = dict(cfg)

        def worker():
            res = perform_cleanup_detailed(cfg_snapshot, is_portable=False)

            def finish():
                if not root.winfo_exists():
                    return
                set_busy(False)
                if "last_run_cleanup" in cfg_snapshot:
                    cfg["last_run_cleanup"] = cfg_snapshot["last_run_cleanup"]
                logs = res.get("logs", [])
                summary = logs[-1] if logs else ""
                if res.get("fatal_error"):
                    messagebox.showerror(t("msg_execute_error_title"), summary)
                else:
                    messagebox.showinfo(
                        t("msg_execute_done_title"),
                        t("msg_execute_done_text", summary=summary),
                    )

            root.after(0, finish)

        threading.Thread(target=worker, daemon=True).start()

    def save_and_close():
        if is_running["active"]:
            return
        apply_inputs()
        if not validate_paths(require_source_exists=False):
            return

        try:
            save_config(cfg)
        except Exception as e:
            messagebox.showerror(t("msg_error_title"), t("msg_save_error", error=str(e)))
            return

        register_system_integration(force=True)
        enforce_log_size(cfg["max_log_size"])
        setup_autostart(autostart_var.get())

        messagebox.showinfo(t("msg_saved_title"), t("msg_saved_text", path=DBP_DIR))
        root.destroy()

    btn_exec.configure(command=execute_normal)
    btn_save.configure(command=save_and_close)

    btn_exec.pack(fill="x", pady=3)
    btn_save.pack(fill="x", pady=3)
    btn_logs.pack(fill="x", pady=3)
    btn_uninst.pack(fill="x", pady=(8, 3))

    root.mainloop()
    return next_action["action"]


def run_config_gui(initial_values=None, _return_action=False):
    """Startet die Konfigurations-GUI (iterativ ohne mainloop-Verschachtelung)."""
    if _return_action:
        return _run_config_window(initial_values)

    from .gui_portable import _run_portable_window

    mode = "config"
    vals = initial_values
    while mode:
        if mode == "portable":
            res = _run_portable_window(vals)
        else:
            res = _run_config_window(vals)
        if isinstance(res, tuple) and len(res) == 2:
            mode, vals = res
        else:
            mode = None
