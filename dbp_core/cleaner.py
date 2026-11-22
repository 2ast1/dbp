"""
Core Cleanup Engine for DBP Cleaner.

Handles file archiving, smart trash evaluation, recursive subfolder scanning,
folder deletion, and trash retention management.
"""

from contextlib import contextmanager
import ctypes
import datetime
import os
import re
import shutil
import sys
import time

from .config import ensure_dbp_dir, load_config, save_config
from .constants import DBP_DIR, LOG_FILE, LOG_SIZE_BYTES
from .i18n import t
from .smart_trash import evaluate_file_importance, is_in_progress_download
from .system import safe_remove_file, safe_rmtree, send_windows_notification

_CLEANUP_MUTEX_NAME = "Local\\DBP_Cleaner_Cleanup_Mutex"
_ERROR_ALREADY_EXISTS = 183
_WAIT_OBJECT_0 = 0x00000000
_WAIT_ABANDONED = 0x00000080


def _is_link_or_junction(path):
    """Prüft auf symbolische Links und NTFS-Junctions."""
    is_junc = hasattr(os.path, "isjunction") and os.path.isjunction(path)
    return os.path.islink(path) or is_junc


@contextmanager
def _cleanup_lock():
    """Verhindert parallele Bereinigungsläufe via Windows-Mutex."""
    if sys.platform != "win32":
        yield True
        return

    handle = None
    kernel32 = None
    try:
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel32.WaitForSingleObject.restype = wintypes.DWORD
        kernel32.ReleaseMutex.argtypes = [wintypes.HANDLE]
        kernel32.ReleaseMutex.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL

        handle = kernel32.CreateMutexW(None, True, _CLEANUP_MUTEX_NAME)
        last_err = ctypes.get_last_error()
        if not handle:
            yield True
            return

        if last_err == _ERROR_ALREADY_EXISTS:
            wait_res = kernel32.WaitForSingleObject(handle, 0)
            if wait_res not in (_WAIT_OBJECT_0, _WAIT_ABANDONED):
                kernel32.CloseHandle(handle)
                handle = None
                yield False
                return

        yield True
    except Exception:
        yield True
    finally:
        if handle and kernel32 is not None:
            try:
                kernel32.ReleaseMutex(handle)
            except Exception:
                pass
            try:
                kernel32.CloseHandle(handle)
            except Exception:
                pass


def enforce_log_size(max_size_key, log_file=None):
    """Stellt sicher, dass die Logdatei das eingestellte Größenlimit nicht überschreitet."""
    target_log = log_file or LOG_FILE
    max_bytes = LOG_SIZE_BYTES.get(str(max_size_key), LOG_SIZE_BYTES["0.5"])
    if max_bytes is None or not os.path.exists(target_log):
        return

    try:
        current_size = os.path.getsize(target_log)
        if current_size <= max_bytes:
            return

        with open(target_log, "rb") as f:
            f.seek(max(0, current_size - max_bytes))
            data = f.read()

        text = data.decode("utf-8", errors="ignore")
        match = re.search(r"--- (?:Lauf am|Run on) ", text)
        if match:
            text = text[match.start():]
        else:
            newline_pos = text.find("\n")
            if newline_pos != -1:
                text = text[newline_pos + 1:]

        with open(target_log, "w", encoding="utf-8", newline="") as f:
            f.write(text)
    except Exception:
        pass


def write_log(messages, cfg=None, log_file=None):
    """Schreibt Log-Einträge in die Logdatei und führt die Größenbegrenzung durch."""
    target_log = log_file or LOG_FILE
    ensure_dbp_dir()
    parent = os.path.dirname(target_log)
    if parent:
        os.makedirs(parent, exist_ok=True)

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    max_size = (cfg or {}).get("max_log_size", "0.5")
    try:
        with open(target_log, "a", encoding="utf-8") as f:
            f.write(t("log_run_header", timestamp=now) + "\n")
            for msg in messages:
                f.write(msg + "\n")
            f.write("\n")
        enforce_log_size(max_size, log_file=target_log)
    except Exception as e:
        send_windows_notification(t("notify_fatal_title"), t("log_error_logfile", error=str(e)))


def check_interval(interval, last_run_str):
    """Prüft, ob basierend auf dem konfigurierten Intervall eine Bereinigung fällig ist."""
    if interval == "startup":
        return True
    if not last_run_str:
        return True

    try:
        last_run = datetime.datetime.strptime(last_run_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return True

    today = datetime.date.today()
    if last_run > today:
        return True

    if interval == "daily":
        return today > last_run
    if interval == "weekly":
        return (today - last_run).days >= 7
    if interval == "monthly":
        return today.month != last_run.month or today.year != last_run.year
    return True


def get_unique_path(directory, filename, is_dir=False):
    """Erzeugt einen kollisionsfreien Zielpfad im Zielverzeichnis."""
    counter = 1
    new_path = os.path.join(directory, filename)
    if is_dir:
        while os.path.exists(new_path):
            new_path = os.path.join(directory, f"{filename}_{counter}")
            counter += 1
        return new_path

    base, ext = os.path.splitext(filename)
    while os.path.exists(new_path):
        new_path = os.path.join(directory, f"{base}_{counter}{ext}")
        counter += 1
    return new_path


def is_same_or_subpath(child_path, parent_path):
    """Prüft sicher, ob child_path identisch mit parent_path oder darin enthalten ist."""
    if not child_path or not parent_path:
        return False
    try:
        norm_child = os.path.normcase(os.path.realpath(os.path.abspath(child_path)))
        norm_parent = os.path.normcase(os.path.realpath(os.path.abspath(parent_path)))
        return os.path.commonpath([norm_child, norm_parent]) == norm_parent
    except (ValueError, OSError):
        return False


def is_dangerous_source_dir(path):
    """Verhindert das Bereinigen von Laufwerkswurzeln, Systemordnern oder dem User-Stammordner."""
    if not path or not path.strip():
        return True
    try:
        norm_path = os.path.normcase(os.path.realpath(os.path.abspath(path)))
    except OSError:
        return True

    # Laufwerkswurzel (z.B. C:\ oder /)
    if os.path.dirname(norm_path) == norm_path:
        return True

    # Exaktes Benutzer-Stammverzeichnis schützen (Unterordner wie Downloads bleiben erlaubt)
    home_dir = os.path.expanduser("~")
    if home_dir:
        norm_home = os.path.normcase(os.path.realpath(os.path.abspath(home_dir)))
        if norm_path == norm_home:
            return True

    if sys.platform == "win32":
        system_env_vars = ("WINDIR", "SYSTEMROOT", "PROGRAMFILES", "PROGRAMFILES(X86)", "PROGRAMW6432", "PROGRAMDATA")
        for var in system_env_vars:
            val = os.environ.get(var)
            if val and is_same_or_subpath(norm_path, val):
                return True

        drive = os.path.splitdrive(norm_path)[0] or "C:"
        for fixed_sys in ("Windows", "Program Files", "Program Files (x86)", "ProgramData"):
            if is_same_or_subpath(norm_path, os.path.join(drive + os.sep, fixed_sys)):
                return True
    else:
        for unix_sys in ("/bin", "/boot", "/dev", "/etc", "/lib", "/proc", "/root", "/sbin", "/sys", "/usr"):
            if is_same_or_subpath(norm_path, unix_sys):
                return True

    return False


def safe_move(src, dst):
    """
    Verschiebt eine Datei sicher: nutzt schnelles os.rename auf demselben Laufwerk
    und bereinigt bei laufwerksübergreifenden Kopierfehlern ohne Duplikate zu hinterlassen.
    """
    try:
        os.rename(src, dst)
        return
    except OSError:
        pass

    shutil.copy2(src, dst)
    try:
        safe_remove_file(src)
    except Exception:
        if os.path.exists(dst):
            try:
                safe_remove_file(dst)
            except Exception:
                pass
        raise


def process_trash(trash_dir):
    """Löscht Elemente im DBP_Trash-Ordner, die 7 Tage oder älter sind."""
    deleted_count = 0
    now = time.time()
    trash_logs = []

    try:
        items = os.listdir(trash_dir)
    except Exception as e:
        fatal_msg = t("err_trash_access", path=trash_dir, err_type=type(e).__name__, err_msg=str(e))
        send_windows_notification(t("notify_fatal_title"), fatal_msg)
        return [fatal_msg]

    for item in items:
        item_path = os.path.join(trash_dir, item)
        try:
            mtime = os.lstat(item_path).st_mtime if _is_link_or_junction(item_path) else os.path.getmtime(item_path)
            file_age_seconds = now - mtime
            file_age_days = file_age_seconds / (24 * 3600)
        except Exception as e:
            trash_logs.append(
                t(
                    "log_error_trash_item",
                    item=item,
                    action=t("trash_action_timestamp"),
                    err_type=type(e).__name__,
                    err_msg=str(e),
                )
            )
            continue

        if file_age_days >= 7:
            try:
                if _is_link_or_junction(item_path):
                    if os.path.isdir(item_path):
                        os.rmdir(item_path)
                    else:
                        safe_remove_file(item_path)
                elif os.path.isfile(item_path):
                    safe_remove_file(item_path)
                elif os.path.isdir(item_path):
                    safe_rmtree(item_path)
                deleted_count += 1
            except Exception as e:
                trash_logs.append(
                    t(
                        "log_error_trash_item",
                        item=item,
                        action=t("trash_action_delete"),
                        err_type=type(e).__name__,
                        err_msg=str(e),
                    )
                )

    if deleted_count > 0:
        trash_logs.append(t("log_trash_cleaned", count=deleted_count))
    return trash_logs


def handle_fatal_error(msg, cfg, is_portable, persist_state=True):
    """Dokumentiert fatale Fehler im Log und sendet eine Benachrichtigung."""
    if not is_portable and persist_state:
        write_log([msg], cfg)
    send_windows_notification(t("notify_fatal_title"), msg)
    return [msg]


def perform_cleanup_detailed(cfg, is_portable=False, persist_state=True):
    """
    Führt die Bereinigung durch und gibt ein strukturiertes Ergebnis-Dict zurück.
    - Erkennt aktive Downloads vor allen anderen Regeln
    - Verschiebt Treffer und Smart-Trash-Dokumente (inkl. neuer Dateien) ins Archiv
    - Befördert Rest in den Papierkorb (oder löscht direkt im Portable-Modus)
    - Entfernt nur wirklich leer gewordene Unterordner (keine ungescannten Ordner)
    """
    empty_stats = {
        "moved": 0,
        "smart": 0,
        "trashed": 0,
        "deleted": 0,
        "folders": 0,
        "errors": 0,
    }

    with _cleanup_lock() as acquired:
        if not acquired:
            msg = t("log_lock_skipped")
            return {
                "success": False,
                "fatal_error": False,
                "logs": [msg],
                "stats": empty_stats,
            }

        source = (cfg or {}).get("source_dir", "").strip()
        target = (cfg or {}).get("target_dir", "").strip()
        extensions_str = (cfg or {}).get("extensions", "")
        include_subfolders = bool((cfg or {}).get("include_subfolders", True))
        clean_empty_folders = bool((cfg or {}).get("clean_empty_folders", True))
        smart_trash_enabled = bool((cfg or {}).get("smart_trash", True))
        protect_recent_hours = (cfg or {}).get("protect_recent_hours", 24)

        def fail_with(msg):
            return {
                "success": False,
                "fatal_error": True,
                "logs": handle_fatal_error(msg, cfg, is_portable, persist_state=persist_state),
                "stats": empty_stats,
            }

        if not source or not target:
            return fail_with(t("msg_error_dirs"))

        if not os.path.exists(source) or not os.path.isdir(source):
            return fail_with(t("err_src_missing", path=source))

        if is_dangerous_source_dir(source) or is_same_or_subpath(source, DBP_DIR):
            return fail_with(t("err_src_dangerous", path=source))

        norm_src = os.path.normcase(os.path.realpath(os.path.abspath(source)))
        norm_tgt = os.path.normcase(os.path.realpath(os.path.abspath(target)))

        if norm_src == norm_tgt:
            return fail_with(t("msg_error_same_dirs"))

        if os.path.exists(target) and not os.path.isdir(target):
            return fail_with(t("err_tgt_not_dir", path=target))

        if not os.path.exists(target):
            try:
                os.makedirs(target, exist_ok=True)
            except Exception as e:
                return fail_with(
                    t("err_tgt_create", path=target, err_type=type(e).__name__, err_msg=str(e))
                )

        trash_dir = None
        if not is_portable:
            trash_dir = os.path.join(target, "DBP_Trash")
            if os.path.exists(trash_dir) and not os.path.isdir(trash_dir):
                return fail_with(t("err_trash_create", path=trash_dir, err_type="NotADirectoryError", err_msg="Not a directory"))
            if not os.path.exists(trash_dir):
                try:
                    os.makedirs(trash_dir, exist_ok=True)
                except Exception as e:
                    return fail_with(
                        t("err_trash_create", path=trash_dir, err_type=type(e).__name__, err_msg=str(e))
                    )
            if is_same_or_subpath(source, trash_dir):
                return fail_with(t("err_src_dangerous", path=source))

        # Alten Papierkorb (>= 7 Tage) ZUERST aufräumen, damit frisch verschobene Dateien
        # mit altem Zeitstempel bei fehlschlagendem os.utime nicht sofort gelöscht werden.
        trash_logs = []
        if not is_portable and trash_dir:
            trash_logs = process_trash(trash_dir)

        # Nur geschützte Pfade aufnehmen, die tatsächlich innerhalb von source liegen
        protected_paths = []
        norm_dbp = os.path.normcase(os.path.realpath(os.path.abspath(DBP_DIR)))
        if is_same_or_subpath(norm_dbp, norm_src):
            protected_paths.append(norm_dbp)
        if is_same_or_subpath(norm_tgt, norm_src):
            protected_paths.append(norm_tgt)
        if trash_dir:
            norm_trash = os.path.normcase(os.path.realpath(os.path.abspath(trash_dir)))
            if is_same_or_subpath(norm_trash, norm_src):
                protected_paths.append(norm_trash)

        def is_inside_protected(path):
            return any(is_same_or_subpath(path, p) for p in protected_paths)

        def is_protected_or_ancestor(dir_path):
            return any(
                is_same_or_subpath(dir_path, p) or is_same_or_subpath(p, dir_path)
                for p in protected_paths
            )

        ext_list = []
        for e in extensions_str.split(","):
            e = e.strip().lower()
            if e:
                if not e.startswith("."):
                    e = "." + e
                if e not in ext_list:
                    ext_list.append(e)

        log = []
        moved_count = 0
        smart_count = 0
        trashed_count = 0
        deleted_count = 0
        folders_cleaned = 0
        error_count = 0

        own_exe = os.path.normcase(
            os.path.abspath(sys.executable if getattr(sys, "frozen", False) else sys.argv[0])
        )

        # 1. Dateisammlung (Rekursiv oder flach, ohne Symlinks/Junctions zu verfolgen)
        files_to_process = []
        subdirs_encountered = []

        try:
            if include_subfolders:
                for root, dirs, files in os.walk(source, topdown=True, followlinks=False):
                    dirs[:] = [
                        d for d in dirs
                        if not _is_link_or_junction(os.path.join(root, d))
                        and not is_inside_protected(os.path.join(root, d))
                    ]

                    norm_root = os.path.normcase(os.path.realpath(os.path.abspath(root)))
                    if norm_root != norm_src:
                        subdirs_encountered.append(root)

                    for f in files:
                        full_p = os.path.join(root, f)
                        if os.path.normcase(os.path.abspath(full_p)) == own_exe:
                            continue
                        files_to_process.append(full_p)
            else:
                for item in os.listdir(source):
                    full_p = os.path.join(source, item)
                    if os.path.normcase(os.path.abspath(full_p)) == own_exe:
                        continue
                    if is_inside_protected(full_p):
                        continue
                    if os.path.isfile(full_p) or (_is_link_or_junction(full_p) and not os.path.isdir(full_p)):
                        files_to_process.append(full_p)
                    elif os.path.isdir(full_p) and not _is_link_or_junction(full_p):
                        subdirs_encountered.append(full_p)
        except Exception as e:
            return fail_with(
                t("err_src_access", path=source, err_type=type(e).__name__, err_msg=str(e))
            )

        # 2. Dateien verarbeiten
        for file_path in files_to_process:
            filename = os.path.basename(file_path)
            norm_parent = os.path.normcase(os.path.realpath(os.path.abspath(os.path.dirname(file_path))))

            # System-desktop.ini direkt im Quellordner-Root schützen (Icon/Anzeigename von "Downloads")
            if norm_parent == norm_src and filename.lower() == "desktop.ini":
                continue

            # A) Aktive Downloads & Office-Lock-Dateien IMMER zuerst schützen (vor ext_list & Smart Trash)
            if is_in_progress_download(file_path):
                log.append(f"{t('log_in_progress_skipped')} {filename}")
                continue

            _, ext = os.path.splitext(filename)
            ext = ext.lower()

            # B) Treffer bei den konfigurierten Dateiendungen
            if ext in ext_list:
                try:
                    target_path = get_unique_path(target, filename)
                    safe_move(file_path, target_path)
                    log.append(f"{t('log_archive')} {filename} -> {os.path.basename(target_path)}")
                    moved_count += 1
                except Exception as e:
                    log.append(f"{t('log_error_arch')} '{filename}': [{type(e).__name__}] {e}")
                    error_count += 1
                continue

            # C) Smart Trash Prüfung (falls aktiviert)
            if smart_trash_enabled:
                is_important, reason, is_active = evaluate_file_importance(file_path, protect_recent_hours)

                if is_active:
                    log.append(f"{t('log_in_progress_skipped')} {filename}")
                    continue

                if is_important:
                    try:
                        target_path = get_unique_path(target, filename)
                        safe_move(file_path, target_path)
                        log.append(f"{t('log_smart_archive', reason=reason)} {filename} -> {os.path.basename(target_path)}")
                        moved_count += 1
                        smart_count += 1
                    except Exception as e:
                        log.append(f"{t('log_error_arch')} '{filename}': [{type(e).__name__}] {e}")
                        error_count += 1
                    continue

            # D) Nicht passend -> In Papierkorb oder Portable-Löschung
            if is_portable:
                try:
                    safe_remove_file(file_path)
                    log.append(f"{t('log_deleted_direct')} {filename}")
                    deleted_count += 1
                except Exception as e:
                    log.append(f"{t('log_error_delete')} '{filename}': [{type(e).__name__}] {e}")
                    error_count += 1
            else:
                try:
                    trash_path = get_unique_path(trash_dir, filename)
                    safe_move(file_path, trash_path)
                    try:
                        os.utime(trash_path, None)
                    except Exception:
                        pass
                    log.append(f"{t('log_trash')} {filename} -> {os.path.basename(trash_path)}")
                    trashed_count += 1
                except Exception as e:
                    log.append(f"{t('log_error_trash')} '{filename}' (Ziel: '{trash_dir}'): [{type(e).__name__}] {e}")
                    error_count += 1

        # 3. Nur wirklich leere Unterordner entfernen (niemals ungescannte Ordner mit Inhalt löschen!)
        if clean_empty_folders and subdirs_encountered:
            sorted_subdirs = sorted(
                subdirs_encountered,
                key=lambda p: (p.count(os.sep), len(p)),
                reverse=True,
            )
            for sdir in sorted_subdirs:
                if not os.path.exists(sdir) or not os.path.isdir(sdir) or _is_link_or_junction(sdir):
                    continue
                if is_protected_or_ancestor(sdir):
                    continue

                try:
                    if not os.listdir(sdir):
                        os.rmdir(sdir)
                        log.append(f"{t('log_folder_deleted')} {os.path.relpath(sdir, source)}")
                        folders_cleaned += 1
                except Exception as e:
                    log.append(f"{t('log_error_folder')} '{sdir}': [{type(e).__name__}] {e}")
                    error_count += 1

        # 4. Trash-Bereinigungsprotokoll anhängen
        if trash_logs:
            log.extend(trash_logs)

        # 5. Zusammenfassung protokollieren
        if is_portable:
            summary = t("log_summary_portable", moved=moved_count, deleted=deleted_count, folders=folders_cleaned)
        else:
            summary = t("log_summary", moved=moved_count, smart_count=smart_count, trashed=trashed_count, folders=folders_cleaned)
        log.append(summary)

        if not is_portable and persist_state:
            write_log(log, cfg)
            if error_count == 0 or (moved_count + trashed_count + folders_cleaned) > 0:
                today_str = datetime.date.today().strftime("%Y-%m-%d")
                if isinstance(cfg, dict):
                    cfg["last_run_cleanup"] = today_str
                disk_cfg = load_config()
                if not disk_cfg.get("source_dir") and isinstance(cfg, dict) and cfg.get("source_dir"):
                    disk_cfg.update(cfg)
                disk_cfg["last_run_cleanup"] = today_str
                try:
                    save_config(disk_cfg)
                except Exception:
                    pass

        return {
            "success": error_count == 0,
            "fatal_error": False,
            "logs": log,
            "stats": {
                "moved": moved_count,
                "smart": smart_count,
                "trashed": trashed_count,
                "deleted": deleted_count,
                "folders": folders_cleaned,
                "errors": error_count,
            },
        }


def perform_cleanup(cfg, is_portable=False):
    """Führt die Bereinigung durch und gibt die Log-Zeilen als Liste zurück."""
    return perform_cleanup_detailed(cfg, is_portable=is_portable)["logs"]
