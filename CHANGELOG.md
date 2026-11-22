# Changelog

All notable changes to **DBP Cleaner** (by **2ast1**) are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2026-11-22

**Author:** 2ast1

### Added
- **Windows Registry Autostart (Task Manager Integration):** Replaced the legacy `DBP_Cleaner.vbs` startup script with a direct `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` entry so DBP Cleaner appears natively in Windows Task Manager under **Startup / Autostart**, runs once at login, and exits completely (`0%` idle CPU/RAM).
- **Live Autostart Status Indicator:** The configuration GUI now displays the real system autostart state (active, missing/outdated, disabled in Task Manager, or inactive).
- **Configurable Recent-File Archive Threshold:** Added a setting in the Configuration GUI (`0 / 6 / 12 / 24 / 48` hours) to control which recent downloads are archived automatically so the Downloads folder stays completely empty.
- **Silent Uninstall Option (`-quiet`):** Added `-quiet` CLI flag (also registered under Windows `QuietUninstallString`) for unattended uninstallation.
- **Single-Instance Cleanup Lock:** Added a Windows named mutex (`Local\DBP_Cleaner_Cleanup_Mutex`) so overlapping cleanup runs cannot collide.
- **Dangerous Directory Guard:** Prevents accidentally cleaning drive roots (e.g. `C:\`), Windows system directories, user home root, or `%APPDATA%\DBP_Cleaner`.
- **Automatic Config Backup & Recovery:** Saves a `config.json.bak` backup and retries transient file locks before writing atomically (`flush` + `fsync` + `os.replace`).
- **Expanded Regression Test Suite:** Isolated all cleaner tests from real `%APPDATA%` and added `tests/test_system.py` plus extensive edge-case coverage (31 tests total).

### Changed
- **Author & Versioning:** Updated package author metadata and Windows uninstaller publisher to `2ast1` and bumped version to `1.2.0`.
- **Non-blocking Cleanup UI:** Moved cleanup execution in both Configuration GUI and Portable GUI onto background threads with progress indicator and disabled action buttons during execution.
- **Portable Mode Options:** Inherited saved extensions by default, added a dedicated toggle for removing empty subfolders, and made the log output area read-only.
- **GUI Loop Management:** Replaced recursive `mainloop()` calls during language or mode switches with an iterative GUI loop.
- **Smart Trash Matching:** Enforced strict word boundaries on short/ambiguous English keywords (preventing false positives like `recorder` or `syntax`), added German umlaut variants (`Bestätigung`, `Kündigung`, `Rückerstattung`), expanded in-progress download extensions (`.opdownload`, `.partial`, `.filepart`, `.aria2`, `.!qb`, `.!ut`, `.bc!`), and handled future file timestamps cleanly.
- **Cross-Drive Moves & System Integration:** Improved `safe_move()` with fast same-drive `os.rename()` and duplicate-free rollback on cross-drive copy failures; optimized EXE/icon copy and Start Menu shortcut creation.

### Fixed
- **Critical — Unscanned Subfolder Deletion:** Removed the logic that moved or permanently deleted non-empty subfolders when *Include subfolders* was disabled. Only genuinely empty subfolders are removed.
- **Critical — CLI / Windows Uninstall Crash:** Fixed `TypeError` when invoking `-uninstall` via command line or Windows Installed Apps (`uninstall_application(config=...)`).
- **Critical — Active Download Protection Order:** Moved active download and Office lock file (`~$...`) protection before configured `extensions` and made it run even when Smart Trash is disabled.
- **Critical — Target as Parent of Source:** Fixed `protected_paths` so cleaning works properly even when `source_dir` is a subdirectory of `target_dir`, while protecting ancestors of nested target folders.
- **Autostart Synchronization:** Fixed *Execute Cleanup Now* saving `autostart: true` without updating the Windows autostart registration, and added boot-time source path retry + crash logging for `-autostart`.
- **Trash Retention Order:** Executed 7-day `DBP_Trash` cleanup *before* moving newly trashed items into trash, preventing immediate deletion if `os.utime()` fails on network drives.
- **Windows Maintenance Bugs:** Fixed `safe_rmtree()` Python 3.12+ `onexc` parameter typo and silent error swallowing, fixed `desktop.ini` preservation in the source root, fixed `\r\r\n` log line-ending duplication during log rotation, fixed Browse dialog clearing paths on Cancel, fixed PowerShell Toast notification escaping via `-EncodedCommand`, and replaced broken console-less `timeout /t 2` self-delete with `ping`.

## [1.1.0] - 2026-11-22

### Added
- Modular `dbp_core` package architecture (`constants`, `config`, `i18n`, `smart_trash`, `cleaner`, `system`, `gui_config`, `gui_portable`, `main`).
- Smart Trash detection for important documents, keywords, extensions, active downloads, and 24h recent files.
- Recursive subfolder scanning, empty subfolder cleanup, and nested target path guards.
- Direct cleanup execution from Configuration GUI, Windows Toast notifications, Start Menu shortcut, and Windows/Revo Uninstaller registration.
- Unit tests under `tests/`.

## [1.0.0]

### Added
- Initial release of DBP Cleaner with Configuration GUI, Portable Mode, automatic file archiving, 7-day `DBP_Trash` retention, English/German localization, and background autostart.
