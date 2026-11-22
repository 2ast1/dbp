"""
System integration, shortcuts, registry and uninstaller for DBP Cleaner.
"""

import base64
import os
import shlex
import shutil
import stat
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox

if sys.platform == "win32":
    import winreg

from . import __author__, __version__
from .constants import (
    AUTOSTART_APPROVED_REG_KEY,
    AUTOSTART_REG_KEY,
    AUTOSTART_VALUE_NAME,
    AUTOSTART_VBS,
    DBP_DIR,
    INSTALLED_EXE,
    INSTALLED_ICO,
    STARTMENU_LNK,
    UNINSTALL_REG_KEY,
)
from .i18n import t


def resource_path(relative_path):
    """Holt den absoluten Pfad zur Ressource, kompatibel mit PyInstaller."""
    if hasattr(sys, "_MEIPASS"):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


def _is_link_or_junction(path):
    """Prüft auf symbolische Links und NTFS-Junctions."""
    is_junc = hasattr(os.path, "isjunction") and os.path.isjunction(path)
    return os.path.islink(path) or is_junc


def safe_remove_file(file_path):
    """Löscht eine Datei (oder einen Link/Junction) sicher, auch bei Schreibschutz."""
    is_dir_link = _is_link_or_junction(file_path) and os.path.isdir(file_path)
    remove_fn = os.rmdir if is_dir_link else os.remove
    try:
        remove_fn(file_path)
    except PermissionError:
        os.chmod(file_path, stat.S_IWRITE)
        remove_fn(file_path)


def on_rmtree_error(func, path, _exc_info=None):
    """Fehlerbehandlung für shutil.rmtree bei schreibgeschützten Dateien auf Windows."""
    os.chmod(path, stat.S_IWRITE)
    func(path)


def safe_rmtree(dir_path):
    """Löscht ein Verzeichnis mitsamt Inhalt, auch bei Schreibschutz (ohne Links zu folgen)."""
    if not os.path.exists(dir_path) and not _is_link_or_junction(dir_path):
        return
    if _is_link_or_junction(dir_path):
        os.rmdir(dir_path)
        return
    if sys.version_info >= (3, 12):
        shutil.rmtree(dir_path, onexc=on_rmtree_error)
    else:
        shutil.rmtree(dir_path, onerror=on_rmtree_error)


def _ps_single_quote(text):
    """Bereitet Text sicher für ein PowerShell-Single-Quoted-Literal vor."""
    return str(text).replace("\r", " ").replace("\n", " ").replace("'", "''")


def send_windows_notification(title, message):
    """Zeigt bei Fehlern eine native Benachrichtigung in Windows an."""
    if sys.platform != "win32":
        return

    safe_title = _ps_single_quote(title)
    safe_msg = _ps_single_quote(message)

    ps_script = (
        "$shown = $false\n"
        "try {\n"
        "    [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null\n"
        "    [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null\n"
        "    $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)\n"
        "    $textNodes = $template.GetElementsByTagName('text')\n"
        f"    $textNodes.Item(0).AppendChild($template.CreateTextNode('{safe_title}')) | Out-Null\n"
        f"    $textNodes.Item(1).AppendChild($template.CreateTextNode('{safe_msg}')) | Out-Null\n"
        "    $toast = [Windows.UI.Notifications.ToastNotification]::new($template)\n"
        "    $notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('DBP Cleaner')\n"
        "    $notifier.Show($toast)\n"
        "    $shown = $true\n"
        "} catch {\n"
        "    $shown = $false\n"
        "}\n"
        "if (-not $shown) {\n"
        "    try {\n"
        "        Add-Type -AssemblyName System.Windows.Forms\n"
        "        Add-Type -AssemblyName System.Drawing\n"
        "        $notify = New-Object System.Windows.Forms.NotifyIcon\n"
        "        $notify.Icon = [System.Drawing.SystemIcons]::Error\n"
        "        $notify.Visible = $true\n"
        f"        $notify.ShowBalloonTip(7000, '{safe_title}', '{safe_msg}', [System.Windows.Forms.ToolTipIcon]::Error)\n"
        "        Start-Sleep -Seconds 7\n"
        "        $notify.Dispose()\n"
        "    } catch {}\n"
        "}\n"
    )
    encoded = base64.b64encode(ps_script.encode("utf-16-le")).decode("ascii")
    try:
        subprocess.Popen(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-EncodedCommand", encoded],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
        )
    except Exception:
        pass


def _needs_file_update(src, dst):
    """Prüft, ob eine Zieldatei fehlt oder sich in Größe/Zeitstempel von src unterscheidet."""
    if not os.path.exists(dst):
        return True
    try:
        s_src = os.stat(src)
        s_dst = os.stat(dst)
        return s_src.st_size != s_dst.st_size or abs(s_src.st_mtime - s_dst.st_mtime) > 1.0
    except OSError:
        return True


def get_app_paths():
    """Gibt Zielpfade für Startmenü, Autostart und Uninstaller zurück und sichert ggf. die EXE in DBP_DIR."""
    if not os.path.exists(DBP_DIR):
        os.makedirs(DBP_DIR, exist_ok=True)

    ico_src = resource_path("besen.ico")
    if os.path.exists(ico_src) and _needs_file_update(ico_src, INSTALLED_ICO):
        try:
            shutil.copy2(ico_src, INSTALLED_ICO)
        except Exception:
            pass

    if getattr(sys, "frozen", False):
        current_exe = os.path.abspath(sys.executable)
        if current_exe.lower() != os.path.abspath(INSTALLED_EXE).lower() and _needs_file_update(current_exe, INSTALLED_EXE):
            try:
                shutil.copy2(current_exe, INSTALLED_EXE)
            except Exception:
                pass
        target_exe = INSTALLED_EXE if os.path.exists(INSTALLED_EXE) else current_exe
        icon_path = INSTALLED_ICO if os.path.exists(INSTALLED_ICO) else f"{target_exe},0"
        return {
            "target_bin": target_exe,
            "args_gui": "",
            "args_autostart": "-autostart",
            "autostart_cmd": f'"{target_exe}" -autostart',
            "uninstall_cmd": f'"{target_exe}" -uninstall',
            "icon_path": icon_path,
        }

    python_dir = os.path.dirname(sys.executable)
    pythonw_exe = os.path.join(python_dir, "pythonw.exe")
    if not os.path.exists(pythonw_exe):
        pythonw_exe = sys.executable

    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    script_path = os.path.join(root_dir, "dbp_cleaner.py")
    if not os.path.exists(script_path):
        script_path = os.path.abspath(sys.argv[0])

    icon_path = INSTALLED_ICO if os.path.exists(INSTALLED_ICO) else f"{pythonw_exe},0"
    return {
        "target_bin": pythonw_exe,
        "args_gui": f'"{script_path}"',
        "args_autostart": f'"{script_path}" -autostart',
        "autostart_cmd": f'"{pythonw_exe}" "{script_path}" -autostart',
        "uninstall_cmd": f'"{pythonw_exe}" "{script_path}" -uninstall',
        "icon_path": icon_path,
    }


def _vbs_escape(value):
    """Escaped doppelte Anführungszeichen für VBScript-String-Literale."""
    return str(value).replace('"', '""')


def setup_startmenu_shortcut(enable=True, force=True):
    """Erstellt oder entfernt den Startmenü-Eintrag 'DBP Cleaner'."""
    if sys.platform != "win32" or not STARTMENU_LNK:
        return

    if not enable:
        if os.path.exists(STARTMENU_LNK):
            try:
                os.remove(STARTMENU_LNK)
            except Exception:
                pass
        return

    if not force and os.path.exists(STARTMENU_LNK):
        return

    paths = get_app_paths()
    temp_vbs = os.path.join(DBP_DIR, "_create_shortcut.vbs")

    vbs_lines = [
        'Set oWS = WScript.CreateObject("WScript.Shell")',
        f'Set oLink = oWS.CreateShortcut("{_vbs_escape(STARTMENU_LNK)}")',
        f'oLink.TargetPath = "{_vbs_escape(paths["target_bin"])}"',
        f'oLink.Arguments = "{_vbs_escape(paths["args_gui"])}"',
        f'oLink.WorkingDirectory = "{_vbs_escape(DBP_DIR)}"',
        'oLink.Description = "DBP Cleaner"',
        f'oLink.IconLocation = "{_vbs_escape(paths["icon_path"])}"',
        'oLink.Save',
    ]
    try:
        with open(temp_vbs, "w", encoding="utf-16", errors="replace") as f:
            f.write("\r\n".join(vbs_lines))
        subprocess.run(
            ["cscript", "//NoLogo", temp_vbs],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
            timeout=5,
        )
    except Exception:
        pass
    finally:
        if os.path.exists(temp_vbs):
            try:
                os.remove(temp_vbs)
            except Exception:
                pass


def setup_uninstall_registry(enable=True):
    """Registriert oder entfernt das Programm für Windows 'Installierte Apps' & Revo Uninstaller."""
    if sys.platform != "win32":
        return

    if not enable:
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, UNINSTALL_REG_KEY)
        except (FileNotFoundError, OSError):
            pass
        return

    paths = get_app_paths()
    try:
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, UNINSTALL_REG_KEY)
        try:
            winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, "DBP Cleaner")
            winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, __author__)
            winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, __version__)
            winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, DBP_DIR)
            winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, paths["icon_path"])
            winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, paths["uninstall_cmd"])
            winreg.SetValueEx(key, "QuietUninstallString", 0, winreg.REG_SZ, f'{paths["uninstall_cmd"]} -quiet')
            winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)

            total_size_kb = 1024
            try:
                total_bytes = sum(
                    os.path.getsize(os.path.join(DBP_DIR, f))
                    for f in os.listdir(DBP_DIR)
                    if os.path.isfile(os.path.join(DBP_DIR, f))
                )
                if total_bytes > 0:
                    total_size_kb = max(1, total_bytes // 1024)
            except Exception:
                pass
            winreg.SetValueEx(key, "EstimatedSize", 0, winreg.REG_DWORD, int(total_size_kb))
        finally:
            winreg.CloseKey(key)
    except Exception:
        pass


def register_system_integration(force=False):
    """Richtet Startmenü-Eintrag ('DBP Cleaner') und Windows/Revo-Deinstallation ein."""
    if sys.platform == "win32":
        setup_startmenu_shortcut(True, force=force)
        setup_uninstall_registry(True)


def _remove_legacy_vbs_autostart():
    """Entfernt das veraltete Startup-VBScript aus früheren Versionen."""
    if AUTOSTART_VBS and os.path.exists(AUTOSTART_VBS):
        try:
            os.remove(AUTOSTART_VBS)
        except Exception:
            pass


def _is_autostart_command_valid(command):
    """Prüft, ob die hinterlegte Autostart-Befehlszeile auf existierende Dateien zeigt."""
    if not command or "-autostart" not in command:
        return False
    try:
        tokens = [tok.strip('"').strip("'") for tok in shlex.split(command, posix=False)]
    except Exception:
        return False
    if not tokens:
        return False
    exe_path = tokens[0]
    if not os.path.exists(exe_path):
        return False
    if len(tokens) >= 2 and not tokens[1].startswith("-"):
        if not os.path.exists(tokens[1]):
            return False
    return True


def get_autostart_status():
    """Liest den echten Windows-Autostart-Status aus Registry & Task-Manager-Freigabe aus."""
    status = {
        "registered": False,
        "command": "",
        "valid": False,
        "disabled_in_taskmgr": False,
        "legacy_vbs": bool(AUTOSTART_VBS and os.path.exists(AUTOSTART_VBS)),
    }
    if sys.platform != "win32":
        return status

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_REG_KEY, 0, winreg.KEY_READ) as key:
            cmd, _ = winreg.QueryValueEx(key, AUTOSTART_VALUE_NAME)
            status["registered"] = True
            status["command"] = str(cmd)
            status["valid"] = _is_autostart_command_valid(str(cmd))
    except FileNotFoundError:
        pass
    except OSError:
        pass

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_APPROVED_REG_KEY, 0, winreg.KEY_READ) as key:
            data, _ = winreg.QueryValueEx(key, AUTOSTART_VALUE_NAME)
            if isinstance(data, (bytes, bytearray)) and len(data) >= 1:
                if data[0] % 2 == 1:
                    status["disabled_in_taskmgr"] = True
    except FileNotFoundError:
        pass
    except OSError:
        pass

    return status


def setup_autostart(enable, show_errors=True):
    """Registriert oder entfernt den Autostart über HKCU\\...\\Run (sichtbar im Task-Manager)."""
    if sys.platform != "win32":
        if enable and show_errors:
            messagebox.showinfo(t("info_title"), t("info_os_not_win"))
        return False

    _remove_legacy_vbs_autostart()

    if enable:
        paths = get_app_paths()
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, AUTOSTART_REG_KEY) as key:
                winreg.SetValueEx(key, AUTOSTART_VALUE_NAME, 0, winreg.REG_SZ, paths["autostart_cmd"])

            # Falls der Eintrag im Task-Manager manuell deaktiviert war, wieder aktivieren
            try:
                with winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    AUTOSTART_APPROVED_REG_KEY,
                    0,
                    winreg.KEY_READ | winreg.KEY_SET_VALUE,
                ) as app_key:
                    data, reg_type = winreg.QueryValueEx(app_key, AUTOSTART_VALUE_NAME)
                    if isinstance(data, (bytes, bytearray)) and len(data) >= 1 and (data[0] % 2 == 1):
                        winreg.SetValueEx(
                            app_key,
                            AUTOSTART_VALUE_NAME,
                            0,
                            reg_type or winreg.REG_BINARY,
                            b"\x02" + b"\x00" * 11,
                        )
            except (FileNotFoundError, OSError):
                pass

            return True
        except Exception as e:
            if show_errors:
                messagebox.showwarning(t("msg_error_title"), t("msg_autostart_error", error=str(e)))
            return False

    # Autostart deaktivieren: Registry-Einträge sauber entfernen
    for reg_key in (AUTOSTART_REG_KEY, AUTOSTART_APPROVED_REG_KEY):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_key, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, AUTOSTART_VALUE_NAME)
        except (FileNotFoundError, OSError):
            pass
    return True


def uninstall_application(parent_window=None, cfg_getter=None, config=None, quiet=False):
    """Entfernt restlos alle App-Daten, den DBP_Trash-Ordner, Autostart, Startmenü und Registry-Einträge."""
    own_root = None
    if not quiet and parent_window is None:
        own_root = tk.Tk()
        own_root.withdraw()
        try:
            own_root.iconbitmap(resource_path("besen.ico"))
        except Exception:
            pass

    if not quiet:
        confirmed = messagebox.askyesno(
            t("confirm_uninstall_title"),
            t("confirm_uninstall_text"),
            icon="warning",
            parent=parent_window if parent_window else own_root,
        )
        if not confirmed:
            if own_root:
                own_root.destroy()
            return

    from .config import load_config

    if cfg_getter is not None:
        current_cfg = cfg_getter()
    elif config is not None:
        current_cfg = config
    else:
        current_cfg = load_config()

    target_dir = (current_cfg or {}).get("target_dir", "").strip()
    if target_dir:
        trash_dir = os.path.join(target_dir, "DBP_Trash")
        if os.path.exists(trash_dir):
            try:
                safe_rmtree(trash_dir)
            except Exception:
                pass

    setup_autostart(False, show_errors=False)
    setup_startmenu_shortcut(False)
    setup_uninstall_registry(False)

    if os.path.exists(DBP_DIR):
        try:
            safe_rmtree(DBP_DIR)
        except Exception:
            pass

    if not quiet:
        messagebox.showinfo(
            t("msg_uninstall_done_title"),
            t("msg_uninstall_done_text"),
            parent=parent_window if parent_window else own_root,
        )

    if parent_window:
        parent_window.destroy()
    if own_root:
        own_root.destroy()

    if sys.platform == "win32" and os.path.exists(DBP_DIR):
        try:
            subprocess.Popen(
                f'cmd.exe /c ping -n 3 127.0.0.1 > NUL & rmdir /s /q "{DBP_DIR}"',
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
            )
        except Exception:
            pass

    sys.exit(0)
