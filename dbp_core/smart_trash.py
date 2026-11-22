"""
Smart Trash Detection Engine for DBP Cleaner.

Intelligently detects important files that should NOT be blindly trashed,
identifies active in-progress downloads, and categorizes candidate files.
"""

import math
import os
import re
import time

# Dateiendungen aktiver Downloads & temporärer Sperrdateien
IN_PROGRESS_EXTENSIONS = {
    ".crdownload",   # Chromium, Chrome, Edge, Brave, Opera
    ".part",         # Firefox
    ".download",     # Safari, diverse Download-Manager
    ".tmpdownload",
    ".unconfirmed",
    ".opdownload",   # Opera
    ".partial",      # Edge / IE / Download-Manager
    ".filepart",     # WinSCP / diverse Clients
    ".aria2",        # aria2
    ".!qb",          # qBittorrent
    ".!ut",          # uTorrent
    ".bc!",          # BitComet
}

# Zusammengesetzte Schlüsselwörter (auch als Teil deutscher Komposita wie "Steuerbescheid")
COMPOUND_KEYWORDS = [
    "rechnung", "invoice", "kontoauszug", "steuer", "vertrag", "contract",
    "gehalt", "boardingpass", "zertifikat", "certificate", "quittung",
    "receipt", "bestätigung", "bestaetigung", "confirmation", "ausweis",
    "kündigung", "kuendigung", "bestellung", "versicherung",
    "meldebescheinigung", "entgelt", "finanzamt", "abrechnung",
    "rückerstattung", "rueckerstattung", "bescheid", "zeugnis", "urkunde",
]

# Kurze oder mehrdeutige Signalwörter: nur an Wortgrenzen matchen (kein "recorder" -> "order" oder "syntax" -> "tax")
BOUNDARY_KEYWORDS = [
    "beleg", "tax", "salary", "ticket", "police", "statement", "order", "lohn",
]

IMPORTANT_KEYWORDS = COMPOUND_KEYWORDS + BOUNDARY_KEYWORDS

# Kategorien wichtiger Dateiendungen
IMPORTANT_EXTENSIONS = {
    # Dokumente & Texte
    ".pdf", ".doc", ".docx", ".odt", ".rtf", ".txt", ".md", ".pages", ".tex",
    ".epub", ".mobi", ".azw3", ".djvu",
    # Tabellen & Daten
    ".xls", ".xlsx", ".csv", ".tsv", ".ods", ".numbers", ".parquet",
    # Präsentationen
    ".ppt", ".pptx", ".odp", ".key",
    # Kreativ- und Projektdateien
    ".psd", ".ai", ".blend", ".prproj", ".aep", ".svg", ".raw", ".cr2", ".nef", ".dng",
    # Quellcode & Skripte
    ".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".css", ".json", ".sql",
    ".sh", ".ps1", ".c", ".cpp", ".h", ".hpp", ".cs", ".rs", ".go", ".java",
    ".kt", ".swift", ".rb", ".php", ".xml", ".yaml", ".yml",
    # Archive & Backups
    ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".iso", ".bak",
}

# Dateiendungen, die definitiv als Müll/Temp gelten
JUNK_EXTENSIONS = {
    ".tmp", ".temp", ".log", ".chk", ".old", ".dmp", ".crash", ".cache",
}


def is_in_progress_download(file_path):
    """
    Prüft, ob eine Datei ein derzeit laufender Download oder eine temporäre Lock-Datei ist.
    Darf niemals verschoben oder gelöscht werden!
    """
    base_name = os.path.basename(file_path).lower()

    # Office-Lock-Dateien (z.B. ~$Dokument.docx oder .~lock.Dokument.docx#)
    if base_name.startswith("~$") or base_name.startswith(".~lock"):
        return True

    _, ext = os.path.splitext(base_name)
    if ext in IN_PROGRESS_EXTENSIONS:
        return True

    return False


def is_system_metadata_file(file_path):
    """Prüft auf Windows- und macOS-Systemmetadaten."""
    base_name = os.path.basename(file_path).lower()
    return base_name in {"desktop.ini", "thumbs.db", ".ds_store"}


def evaluate_file_importance(file_path, protect_recent_hours=24):
    """
    Bewertet eine Datei anhand intelligenter Kriterien:
    Rückgabe: (is_important: bool, reason: str, is_active: bool)
    """
    if is_in_progress_download(file_path):
        return False, "Active Download", True

    if is_system_metadata_file(file_path):
        return False, "System Metadata", False

    filename = os.path.basename(file_path)
    name_lower = filename.lower()
    stem_lower, ext = os.path.splitext(name_lower)

    # 1. Bekannter temporärer Müll
    if ext in JUNK_EXTENSIONS:
        return False, "Known Junk Extension", False

    # 0-Byte Dateien ohne Inhalt (sofern nicht aktiv)
    try:
        if os.path.getsize(file_path) == 0:
            return False, "Empty File (0 Bytes)", False
    except OSError:
        pass

    # 2. Schlüsselwörter im Dateinamen prüfen
    for kw in COMPOUND_KEYWORDS:
        if kw in stem_lower:
            return True, f"Keyword '{kw}'", False

    for kw in BOUNDARY_KEYWORDS:
        if re.search(r"(?:^|[\W_])" + re.escape(kw) + r"(?:$|[\W_])", stem_lower):
            return True, f"Keyword '{kw}'", False

    # 3. Wichtige Dateitypen / Dokumente / Code / Medien
    if ext in IMPORTANT_EXTENSIONS:
        return True, f"Important Type ({ext})", False

    # 4. Gnadenfrist für sehr neue Dateien -> werden mit ins Archiv verschoben,
    #    damit der Downloads-Ordner vollständig geleert wird.
    hours = 0.0
    if not isinstance(protect_recent_hours, bool) and protect_recent_hours is not None:
        try:
            parsed = float(protect_recent_hours)
            if math.isfinite(parsed) and parsed > 0:
                hours = parsed
        except (TypeError, ValueError):
            hours = 0.0

    if hours > 0:
        try:
            mtime = os.path.getmtime(file_path)
            age_hours = (time.time() - mtime) / 3600.0
            if age_hours < hours:
                display_hours = int(hours) if hours.is_integer() else hours
                return True, f"Recent Download (<{display_hours}h)", False
        except OSError:
            pass

    return False, "Standard Non-matching", False
