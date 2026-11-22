"""
Configuration management for DBP Cleaner.
"""

import json
import math
import os
import shutil
import time

from .constants import CONFIG_FILE, DBP_DIR, DEFAULT_CONFIG, LOG_SIZE_BYTES, VALID_INTERVALS
from .i18n import TRANSLATIONS, set_language

_LEGACY_INTERVAL_MAP = {
    "Bei jedem Start": "startup",
    "At every startup": "startup",
    "Täglich": "daily",
    "Daily": "daily",
    "Wöchentlich": "weekly",
    "Weekly": "weekly",
    "Monatlich": "monthly",
    "Monthly": "monthly",
}

_BOOL_KEYS = (
    "autostart",
    "smart_trash",
    "include_subfolders",
    "clean_empty_folders",
)

_STR_KEYS = (
    "source_dir",
    "target_dir",
    "extensions",
    "last_run_cleanup",
)


def ensure_dbp_dir():
    """Stellt sicher, dass das Anwendungsdatenverzeichnis existiert."""
    target_dir = os.path.dirname(CONFIG_FILE) or DBP_DIR
    if not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)
    if not os.path.exists(DBP_DIR):
        os.makedirs(DBP_DIR, exist_ok=True)


def _normalize_config(raw_cfg):
    """Validiert und normalisiert Konfigurationswerte mit sicheren Fallbacks."""
    if not isinstance(raw_cfg, dict):
        raise ValueError("Configuration root must be a JSON object")

    c = DEFAULT_CONFIG.copy()
    c.update(raw_cfg)

    lang = c.get("language")
    if not isinstance(lang, str) or lang not in TRANSLATIONS:
        c["language"] = DEFAULT_CONFIG["language"]

    interval = c.get("interval")
    if interval in _LEGACY_INTERVAL_MAP:
        interval = _LEGACY_INTERVAL_MAP[interval]
    if interval not in VALID_INTERVALS:
        interval = DEFAULT_CONFIG["interval"]
    c["interval"] = interval

    max_log_size = str(c.get("max_log_size", DEFAULT_CONFIG["max_log_size"]))
    if max_log_size not in LOG_SIZE_BYTES:
        max_log_size = DEFAULT_CONFIG["max_log_size"]
    c["max_log_size"] = max_log_size

    raw_hours = c.get("protect_recent_hours", DEFAULT_CONFIG["protect_recent_hours"])
    if isinstance(raw_hours, bool):
        hours = DEFAULT_CONFIG["protect_recent_hours"]
    else:
        try:
            hours_f = float(raw_hours)
            if not math.isfinite(hours_f) or hours_f < 0:
                hours = DEFAULT_CONFIG["protect_recent_hours"]
            elif hours_f.is_integer():
                hours = int(hours_f)
            else:
                hours = hours_f
        except (TypeError, ValueError):
            hours = DEFAULT_CONFIG["protect_recent_hours"]
    c["protect_recent_hours"] = hours

    for key in _BOOL_KEYS:
        val = c.get(key)
        if not isinstance(val, bool):
            c[key] = bool(val) if isinstance(val, (int, float)) else DEFAULT_CONFIG[key]

    for key in _STR_KEYS:
        val = c.get(key)
        if not isinstance(val, str):
            c[key] = DEFAULT_CONFIG[key]

    return c


def _load_json_file(path, retries=3, delay=0.05):
    """Lädt und parst eine JSON-Datei mit kurzen Wiederholungen bei vorübergehenden Sperren."""
    last_err = None
    for attempt in range(retries):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (PermissionError, OSError) as e:
            last_err = e
            if attempt < retries - 1:
                time.sleep(delay)
        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(f"Invalid JSON in {path}: {e}") from e
    raise last_err


def load_config():
    """Lädt die Konfigurationsdatei (mit .bak-Wiederherstellung) oder gibt Standardwerte zurück."""
    backup_file = CONFIG_FILE + ".bak"

    for candidate in (CONFIG_FILE, backup_file):
        if os.path.exists(candidate):
            try:
                raw = _load_json_file(candidate)
                cfg = _normalize_config(raw)
                set_language(cfg.get("language", "English"))
                return cfg
            except Exception:
                continue

    cfg = DEFAULT_CONFIG.copy()
    set_language(cfg.get("language", "English"))
    return cfg


def save_config(cfg):
    """Speichert die Konfiguration atomar ab (inkl. Backup und Windows-Retry-Logik)."""
    parent_dir = os.path.dirname(CONFIG_FILE) or DBP_DIR
    os.makedirs(parent_dir, exist_ok=True)
    ensure_dbp_dir()

    normalized = _normalize_config(cfg)
    set_language(normalized.get("language", "English"))

    backup_file = CONFIG_FILE + ".bak"
    if os.path.exists(CONFIG_FILE):
        try:
            _normalize_config(_load_json_file(CONFIG_FILE, retries=1))
            shutil.copy2(CONFIG_FILE, backup_file)
        except Exception:
            pass

    temp_file = f"{CONFIG_FILE}.tmp.{os.getpid()}"
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(normalized, f, indent=4, ensure_ascii=False)
            f.flush()
            try:
                os.fsync(f.fileno())
            except OSError:
                pass

        last_err = None
        for attempt in range(5):
            try:
                os.replace(temp_file, CONFIG_FILE)
                last_err = None
                break
            except (PermissionError, OSError) as e:
                last_err = e
                if attempt < 4:
                    time.sleep(0.05)

        if last_err is not None:
            raise last_err
    finally:
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception:
                pass
