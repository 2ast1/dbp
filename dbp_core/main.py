"""
Command-Line Interface and Main Entry Point for DBP Cleaner.
"""

import argparse
import os
import time

from .cleaner import check_interval, perform_cleanup, write_log
from .config import load_config
from .gui_config import run_config_gui
from .gui_portable import run_portable_gui
from .i18n import t
from .system import send_windows_notification, uninstall_application


def run_gui_loop(start_mode="config", initial_values=None):
    """Führt den GUI-Moduswechsel iterativ aus, ohne Tkinter-Loops zu verschachteln."""
    mode = start_mode
    vals = initial_values
    while mode:
        if mode == "portable":
            result = run_portable_gui(vals, _return_action=True)
        else:
            result = run_config_gui(vals, _return_action=True)

        if isinstance(result, tuple) and len(result) == 2:
            mode, vals = result
        else:
            mode = None


def _run_autostart(config):
    """Führt die Autostart-Bereinigung mit Boot-Retry und Fehlerprotokollierung aus."""
    try:
        src = config.get("source_dir", "").strip()
        tgt = config.get("target_dir", "").strip()
        if not src or not tgt:
            return

        interval = config.get("interval", "startup")
        last_run = config.get("last_run_cleanup", "")
        if not check_interval(interval, last_run):
            return

        # Bei frühem Windows-Start auf ggf. verzögert gemountete Ordner/Netzlaufwerke warten
        if not os.path.exists(src):
            for _ in range(3):
                time.sleep(5)
                if os.path.exists(src):
                    break

        perform_cleanup(config, is_portable=False)
    except Exception as e:
        msg = t("log_autostart_unhandled", err_type=type(e).__name__, err_msg=str(e))
        write_log([msg], config)
        send_windows_notification(t("notify_fatal_title"), msg)


def main():
    parser = argparse.ArgumentParser(description="Download Bereinigungs Programm (DBP)")
    parser.add_argument("-gui", action="store_true", help="Open Configuration GUI")
    parser.add_argument("-portable", action="store_true", help="Open Portable Mode")
    parser.add_argument("-autostart", action="store_true", help="Run background cleanup via Autostart")
    parser.add_argument("-uninstall", action="store_true", help="Completely uninstall DBP Cleaner")
    parser.add_argument("-quiet", action="store_true", help="Run silently without confirmation dialogs (for -uninstall)")
    args = parser.parse_args()

    config = load_config()

    if args.uninstall:
        uninstall_application(config=config, quiet=args.quiet)
    elif args.portable:
        run_gui_loop("portable")
    elif args.autostart:
        _run_autostart(config)
    else:
        run_gui_loop("config")


if __name__ == "__main__":
    main()
