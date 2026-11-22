"""
Internationalization (i18n) for DBP Cleaner.
"""

TRANSLATIONS = {
    "English": {
        "title_portable": "DBP - Portable Mode",
        "title_config": "DBP - Configuration",
        "title_logs": "DBP - Logs",
        "menu_options": "Options",
        "menu_portable": "Open Portable Mode",
        "menu_config": "Open Configuration",
        "menu_language": "Language",
        "menu_uninstall": "Uninstall DBP Cleaner",
        "lbl_source": "Source folder (e.g. Downloads):",
        "lbl_target": "Target folder (Archive):",
        "lbl_exts": "Extensions to keep (comma-separated):",
        "lbl_interval": "Interval:",
        "lbl_log_size": "Max. Log Size:",
        "lbl_protect_recent": "Archive recent files (< hours):",
        "chk_smart_trash": "Enable Smart Trash (Detect & archive important files)",
        "chk_subfolders": "Include subfolders (Recursive scan & clean)",
        "chk_clean_empty_folders": "Remove empty subfolders after cleanup",
        "chk_autostart": "Run once on PC startup (Autostart, 0% idle CPU/RAM)",
        "btn_browse": "Browse",
        "btn_execute": "Execute once now",
        "btn_execute_normal": "Execute Cleanup Now (with Trash)",
        "btn_save": "Save Configuration",
        "btn_logs": "View latest logs in text editor",
        "btn_uninstall": "Uninstall Program Completely",
        "msg_error_title": "Error",
        "msg_error_dirs": "Please specify source and target folders.",
        "msg_error_same_dirs": "Source and target folders cannot be identical.",
        "msg_error_nested_dirs": "Target folder cannot be inside the source folder without subfolder exclusions.",
        "msg_saved_title": "Saved",
        "msg_saved_text": "Configuration saved!\nLogs and Config are located at:\n{path}",
        "msg_execute_done_title": "Cleanup Finished",
        "msg_execute_done_text": "Cleanup executed successfully!\n{summary}",
        "msg_execute_error_title": "Cleanup Failed",
        "msg_autostart_error": "Could not configure Windows Autostart:\n{error}",
        "msg_open_log_error": "Could not open log file:\n{error}",
        "msg_save_error": "Could not save configuration:\n{error}",
        "msg_no_logs": "No logs have been written yet.",
        "status_running": "Cleanup in progress...",
        "status_autostart_active": "Autostart: Active in Registry (visible in Task Manager)",
        "status_autostart_disabled_tm": "Autostart: Disabled in Task Manager — click Save to re-enable",
        "status_autostart_needs_save": "Autostart: Enabled in config, not registered yet — click Save",
        "status_autostart_inactive": "Autostart: Inactive",
        "confirm_portable_title": "Confirm Permanent Deletion",
        "confirm_portable_text": (
            "In Portable Mode, the Trash is skipped!\n\n"
            "Files matching your extensions (and Smart Trash important files if enabled) "
            "will be moved to the Archive folder, and ALL OTHER FILES in the source folder "
            "and subfolders will be PERMANENTLY deleted immediately.\n\n"
            "Do you really want to continue?"
        ),
        "confirm_uninstall_title": "Uninstall DBP Cleaner",
        "confirm_uninstall_text": (
            "Do you really want to completely uninstall DBP Cleaner?\n\n"
            "The following will be permanently deleted:\n"
            "- All App Data (Configuration & Logs)\n"
            "- All files inside the DBP_Trash folder\n"
            "- Autostart & Start Menu entries\n"
            "- Windows / Revo Uninstaller registration\n\n"
            "Your archived files in the target folder will NOT be touched."
        ),
        "msg_uninstall_done_title": "Uninstalled",
        "msg_uninstall_done_text": "DBP Cleaner and all associated data have been completely removed.",
        "int_startup": "At every startup",
        "int_daily": "Daily",
        "int_weekly": "Weekly",
        "int_monthly": "Monthly",
        "size_0_5": "0.5 MB (Default)",
        "size_1": "1 MB",
        "size_5": "5 MB",
        "size_10": "10 MB",
        "size_unlimited": "Unlimited",
        "recent_0": "0 hours (Disabled)",
        "recent_6": "6 hours",
        "recent_12": "12 hours",
        "recent_24": "24 hours (Default)",
        "recent_48": "48 hours",
        "log_run_header": "--- Run on {timestamp} ---",
        "log_error_logfile": "Log file error: {error}",
        "trash_action_timestamp": "check timestamp",
        "trash_action_delete": "permanently delete",
        "log_lock_skipped": "SKIPPED: Another cleanup instance is already running.",
        "log_autostart_unhandled": "FATAL ERROR during autostart execution: [{err_type}] {err_msg}",
        "log_archive": "ARCHIVE:",
        "log_smart_archive": "ARCHIVE (Smart Trash - {reason}):",
        "log_trash": "TRASH:",
        "log_deleted_direct": "PERMANENTLY DELETED (Portable):",
        "log_folder_deleted": "FOLDER DELETED (Empty):",
        "log_folder_trash": "FOLDER MOVED TO TRASH:",
        "log_in_progress_skipped": "SKIPPED (Active download):",
        "log_trash_cleaned": "TRASH CLEANED UP: {count} old elements (>= 7 days) permanently deleted.",
        "log_error_arch": "ERROR archiving",
        "log_error_trash": "ERROR moving to trash",
        "log_error_delete": "ERROR permanently deleting",
        "log_error_folder": "ERROR cleaning folder",
        "log_error_trash_item": "TRASH ERROR on item '{item}' ({action}): [{err_type}] {err_msg}",
        "log_summary": "Summary: {moved} to Archive ({smart_count} via Smart Trash), {trashed} to Trash, {folders} folders cleaned.",
        "log_summary_portable": "Summary (Portable): {moved} to Archive, {deleted} permanently deleted, {folders} folders cleaned.",
        "err_src_missing": "FATAL ERROR: Source folder does not exist: {path}",
        "err_src_access": "FATAL ERROR: Cannot read source folder '{path}': [{err_type}] {err_msg}",
        "err_src_dangerous": "FATAL ERROR: Protected system or root directory cannot be cleaned: {path}",
        "err_tgt_create": "FATAL ERROR: Target folder '{path}' could not be created: [{err_type}] {err_msg}",
        "err_tgt_not_dir": "FATAL ERROR: Target path is not a directory: {path}",
        "err_trash_create": "FATAL ERROR: Trash folder '{path}' could not be created: [{err_type}] {err_msg}",
        "err_trash_access": "FATAL ERROR: Trash folder '{path}' cannot be accessed: [{err_type}] {err_msg}",
        "notify_fatal_title": "DBP Cleaner - Fatal Error",
        "info_os_not_win": "This feature is only supported on Windows.",
        "info_title": "Info"
    },
    "Deutsch": {
        "title_portable": "DBP - Portable Modus",
        "title_config": "DBP - Konfiguration",
        "title_logs": "DBP - Protokolle",
        "menu_options": "Optionen",
        "menu_portable": "Portable Modus öffnen",
        "menu_config": "Konfiguration öffnen",
        "menu_language": "Sprache",
        "menu_uninstall": "DBP Cleaner deinstallieren",
        "lbl_source": "Quellordner (z.B. Downloads):",
        "lbl_target": "Zielordner (Archiv):",
        "lbl_exts": "Dateiendungen behalten (kommagetrennt):",
        "lbl_interval": "Intervall:",
        "lbl_log_size": "Max. Log-Größe:",
        "lbl_protect_recent": "Neue Dateien archivieren (< Stunden):",
        "chk_smart_trash": "Smart Trash aktivieren (Wichtige Dateien intelligent erkennen & behalten)",
        "chk_subfolders": "Unterordner einbeziehen (Rekursiv durchsuchen & bereinigen)",
        "chk_clean_empty_folders": "Leere Unterordner nach Bereinigung löschen",
        "chk_autostart": "Beim PC-Start einmalig ausführen (Autostart, 0% CPU/RAM danach)",
        "btn_browse": "Suchen",
        "btn_execute": "Jetzt einmalig Ausführen",
        "btn_execute_normal": "Jetzt bereinigen (mit Papierkorb)",
        "btn_save": "Konfiguration speichern",
        "btn_logs": "Letzte Logs im Texteditor ansehen",
        "btn_uninstall": "Programm restlos deinstallieren",
        "msg_error_title": "Fehler",
        "msg_error_dirs": "Bitte Quell- und Zielordner angeben.",
        "msg_error_same_dirs": "Quell- und Zielordner dürfen nicht identisch sein.",
        "msg_error_nested_dirs": "Der Zielordner darf nicht im Quellordner liegen, ohne dass er ausgeschlossen wird.",
        "msg_saved_title": "Gespeichert",
        "msg_saved_text": "Konfiguration gespeichert!\nLogs und Config liegen in:\n{path}",
        "msg_execute_done_title": "Bereinigung abgeschlossen",
        "msg_execute_done_text": "Bereinigung erfolgreich durchgeführt!\n{summary}",
        "msg_execute_error_title": "Bereinigung fehlgeschlagen",
        "msg_autostart_error": "Windows-Autostart konnte nicht eingerichtet werden:\n{error}",
        "msg_open_log_error": "Logdatei konnte nicht geöffnet werden:\n{error}",
        "msg_save_error": "Konfiguration konnte nicht gespeichert werden:\n{error}",
        "msg_no_logs": "Es wurden noch keine Logs geschrieben.",
        "status_running": "Bereinigung läuft...",
        "status_autostart_active": "Autostart: Aktiv in Registry (im Task-Manager sichtbar)",
        "status_autostart_disabled_tm": "Autostart: Im Task-Manager deaktiviert — 'Speichern' zum Reaktivieren",
        "status_autostart_needs_save": "Autostart: In Config aktiv, noch nicht registriert — bitte 'Speichern' drücken",
        "status_autostart_inactive": "Autostart: Inaktiv",
        "confirm_portable_title": "Endgültiges Löschen bestätigen",
        "confirm_portable_text": (
            "Im Portable-Modus wird der Papierkorb übersprungen!\n\n"
            "Dateien mit den gewünschten Endungen (sowie durch Smart Trash erkannte wichtige Dateien) "
            "werden in das Archiv verschoben. ALLE ANDEREN DATEIEN im Quellordner und seinen Unterordnern "
            "werden SOFORT und ENDGÜLTIG gelöscht.\n\n"
            "Möchten Sie wirklich fortfahren?"
        ),
        "confirm_uninstall_title": "DBP Cleaner deinstallieren",
        "confirm_uninstall_text": (
            "Möchten Sie DBP Cleaner wirklich restlos deinstallieren?\n\n"
            "Folgendes wird unwiderruflich gelöscht:\n"
            "- Alle App-Daten (Konfiguration & Logs)\n"
            "- Alle Dateien im DBP_Trash Papierkorb\n"
            "- Autostart- & Startmenü-Einträge\n"
            "- Windows- / Revo-Uninstaller-Registrierung\n\n"
            "Ihre archivierten Dateien im Zielordner bleiben selbstverständlich erhalten."
        ),
        "msg_uninstall_done_title": "Deinstalliert",
        "msg_uninstall_done_text": "DBP Cleaner und alle zugehörigen Daten wurden restlos entfernt.",
        "int_startup": "Bei jedem Start",
        "int_daily": "Täglich",
        "int_weekly": "Wöchentlich",
        "int_monthly": "Monatlich",
        "size_0_5": "0,5 MB (Standard)",
        "size_1": "1 MB",
        "size_5": "5 MB",
        "size_10": "10 MB",
        "size_unlimited": "Unendlich",
        "recent_0": "0 Stunden (Deaktiviert)",
        "recent_6": "6 Stunden",
        "recent_12": "12 Stunden",
        "recent_24": "24 Stunden (Standard)",
        "recent_48": "48 Stunden",
        "log_run_header": "--- Lauf am {timestamp} ---",
        "log_error_logfile": "Log-Datei Fehler: {error}",
        "trash_action_timestamp": "Zeitstempel prüfen",
        "trash_action_delete": "Endgültig löschen",
        "log_lock_skipped": "ÜBERSPRUNGEN: Eine andere Bereinigung läuft bereits.",
        "log_autostart_unhandled": "FATALER FEHLER beim Autostart-Lauf: [{err_type}] {err_msg}",
        "log_archive": "ARCHIV:",
        "log_smart_archive": "ARCHIV (Smart Trash - {reason}):",
        "log_trash": "PAPIERKORB:",
        "log_deleted_direct": "ENDGÜLTIG GELÖSCHT (Portable):",
        "log_folder_deleted": "ORDNER GELÖSCHT (Leer):",
        "log_folder_trash": "ORDNER IN PAPIERKORB:",
        "log_in_progress_skipped": "ÜBERSPRUNGEN (Laufender Download):",
        "log_trash_cleaned": "PAPIERKORB AUFGERÄUMT: {count} alte Elemente (>= 7 Tage) endgültig gelöscht.",
        "log_error_arch": "FEHLER beim Archivieren von",
        "log_error_trash": "FEHLER beim Verschieben in den Papierkorb von",
        "log_error_delete": "FEHLER beim direkten Löschen von",
        "log_error_folder": "FEHLER beim Bereinigen von Ordner",
        "log_error_trash_item": "PAPIERKORB-FEHLER bei Element '{item}' ({action}): [{err_type}] {err_msg}",
        "log_summary": "Zusammenfassung: {moved} ins Archiv ({smart_count} via Smart Trash), {trashed} in den Papierkorb, {folders} Ordner bereinigt.",
        "log_summary_portable": "Zusammenfassung (Portable): {moved} ins Archiv, {deleted} endgültig gelöscht, {folders} Ordner bereinigt.",
        "err_src_missing": "FATALER FEHLER: Quellordner existiert nicht: {path}",
        "err_src_access": "FATALER FEHLER: Quellordner '{path}' kann nicht gelesen werden: [{err_type}] {err_msg}",
        "err_src_dangerous": "FATALER FEHLER: Geschütztes System- oder Stammverzeichnis darf nicht bereinigt werden: {path}",
        "err_tgt_create": "FATALER FEHLER: Zielordner '{path}' konnte nicht erstellt werden: [{err_type}] {err_msg}",
        "err_tgt_not_dir": "FATALER FEHLER: Zielpfad ist kein Ordner: {path}",
        "err_trash_create": "FATALER FEHLER: Papierkorb-Ordner '{path}' konnte nicht erstellt werden: [{err_type}] {err_msg}",
        "err_trash_access": "FATALER FEHLER: Zugriff auf Papierkorb-Ordner '{path}' fehlgeschlagen: [{err_type}] {err_msg}",
        "notify_fatal_title": "DBP Cleaner - Fataler Fehler",
        "info_os_not_win": "Diese Funktion wird nur unter Windows unterstützt.",
        "info_title": "Info"
    }
}

_current_language = "English"

def set_language(lang):
    global _current_language
    if lang in TRANSLATIONS:
        _current_language = lang

def get_language():
    return _current_language

def t(key, lang=None, **kwargs):
    """Holt die Übersetzung für den angegebenen Schlüssel."""
    target_lang = lang or _current_language
    dictionary = TRANSLATIONS.get(target_lang, TRANSLATIONS["English"])
    text = dictionary.get(key, TRANSLATIONS["English"].get(key, key))
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text
