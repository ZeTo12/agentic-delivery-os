# Implementierungsplan: Portable Install-/Uninstall-Skripte (Python)

> **Status:** Entwurf  
> **Datum:** 2026-04-30  
> **Basis:** [Konzept: Portable Install-/Uninstall-Skripte](./portable-install-scripts-concept.md) — Option 2 (Python)  
> **Abhängigkeit:** Python 3.8+, git CLI  
> **Geschätzter Aufwand:** 4–5 Tage

---

## Context and Goals

Dieses Plan portiert die bestehenden Bash-Skripte `scripts/install.sh` (~760 Zeilen) und `scripts/uninstall.sh` (~429 Zeilen) nach Python 3 (ausschließlich Standardbibliothek). Die Python-Version muss **funktional identisch** zur Bash-Version sein und nativ auf Windows, Linux und macOS laufen.

### Design-Entscheidungen

1. **Nur Python-Standardbibliothek** — kein `pip install`, keine externen Pakete
2. **Minimale Python-Version: 3.8** — wegen Walrus-Operator (`:=`) und `shutil.copytree(dirs_exist_ok=True)`
3. **Shared Library** — gemeinsamer Code in `scripts/ados_lib/` (file ops, git ops, logging, platform paths, manifest)
4. **1:1 Funktionsparität** — gleiche CLI-Flags, gleiche Umgebungsvariablen, gleiche Exit-Codes
5. **Bash-Skripte bleiben vorerst** — parallele Existenz, bis Python-Version vollständig getestet
6. **Forward-slash Pfade intern** — `pathlib.Path` normalisiert automatisch; Manifest-Listen verwenden `/` (wie Bash-Version)

## Scope

### In Scope

- Portierung aller Funktionen aus `install.sh` und `uninstall.sh`
- Shared Library `ados_lib/` mit plattformunabhängigen Primitiven
- Plattform-spezifische Pfade (XDG auf Linux, `~/.config` auf macOS, `%APPDATA%` auf Windows)
- Unit-Tests mit `unittest` (stdlib) — kein pytest erforderlich
- One-Liner-Install Wrapper (`curl | python3 -`)

> **Hinweis:** Automatisierte CI (GitHub Actions) ist ein separates Vorhaben und nicht Teil dieses Plans. Das Projekt verwendet aktuell keine GitHub Actions. Die Einführung von CI-Infrastruktur sollte als eigenständiges Ticket behandelt werden, das auch die bestehenden Bash-Tests unter `scripts/.tests/` und `tools/.tests/` abdeckt.

### Out of Scope

- Entfernung der Bash-Skripte (separater Schritt nach Validierung)
- GUI oder TUI
- PyInstaller / Binary-Distribution
- Python-Paketierung (setup.py / pyproject.toml)

### Constraints

- Keine externen Python-Pakete
- `git` CLI muss weiterhin installiert sein
- Python ≥ 3.8 (macOS Monterey+, Ubuntu 20.04+, Windows Store/python.org)
- Farbige Diff-Ausgabe ist optional (Terminal-Capability-Check statt `--color=auto`)

### Risks

- **RSK-1**: `python` vs `python3` Alias-Problematik auf verschiedenen Systemen. **Mitigation:** Shebang `#!/usr/bin/env python3`, Dokumentation für Windows (`py -3` oder `python`).
- **RSK-2**: Windows-Pfade mit Leerzeichen / Unicode. **Mitigation:** Durchgängig `pathlib.Path` verwenden, nie String-Konkatenation.
- **RSK-3**: Unterschiedliches Verhalten von `subprocess.run` auf Windows (kein `sh`). **Mitigation:** Git-Befehle als Liste übergeben (`["git", "clone", ...]`), nie als Shell-String.

---

## Dateistruktur (Ziel)

```
scripts/
├── install.sh              # bestehend (bleibt vorerst)
├── uninstall.sh            # bestehend (bleibt vorerst)
├── install.py              # NEU — Python-Einstiegspunkt
├── uninstall.py            # NEU — Python-Einstiegspunkt
├── ados_lib/               # NEU — Shared Library
│   ├── __init__.py
│   ├── platform_paths.py   # OS-abhängige Pfadauflösung
│   ├── file_ops.py         # copy_file_with_diff, ensure_dir, remove_file, etc.
│   ├── git_ops.py          # clone_or_update_repo, auto_fetch_source
│   ├── gitignore.py        # ensure_gitignore_entry, file_contains_line
│   ├── logger.py           # log_info, log_warn, log_err, log_debug
│   ├── cli.py              # argparse-basiertes Argument-Parsing
│   ├── manifest.py         # UPDATABLE_FILES, LOCAL_DIRS, AGENT_FILES, etc.
│   ├── safety.py           # validate_paths, safe_rmdir (Pfadtiefenprüfung)
│   └── types.py            # Dataclasses / TypedDicts für Config
└── tests/                  # NEU — Unit-Tests
    ├── __init__.py
    ├── test_platform_paths.py
    ├── test_file_ops.py
    ├── test_git_ops.py
    ├── test_gitignore.py
    ├── test_safety.py
    ├── test_install_local.py
    ├── test_install_global.py
    ├── test_uninstall_local.py
    └── test_uninstall_global.py
```

---

## Mapping: Bash → Python Standardbibliothek

| Bash-Feature | Python-Äquivalent |
|---|---|
| `cp file1 file2` | `shutil.copy2(src, dest)` |
| `mkdir -p dir` | `Path(dir).mkdir(parents=True, exist_ok=True)` |
| `rm -f file` | `Path(file).unlink(missing_ok=True)` |
| `rm -rf dir` | `shutil.rmtree(dir)` |
| `diff -q file1 file2` | `filecmp.cmp(file1, file2, shallow=False)` |
| `diff -u file1 file2` | `difflib.unified_diff(...)` |
| `ls -A dir` | `any(Path(dir).iterdir())` |
| `realpath -m path` | `Path(path).resolve()` |
| `basename file` | `Path(file).name` |
| `dirname file` | `Path(file).parent` |
| `command -v git` | `shutil.which("git")` |
| `git clone ...` | `subprocess.run(["git", "clone", ...])` |
| `read -r answer` | `input("prompt")` |
| `grep -qF pattern file` | `pattern in Path(file).read_text()` |
| `BASH_SOURCE[0]` | `Path(__file__).resolve().parent` |
| `$HOME` | `Path.home()` |
| `set -e` (exit on error) | Exceptions + try/except |
| `trap INT` | `signal.signal(signal.SIGINT, handler)` |
| Argument-Parsing (`case`) | `argparse.ArgumentParser` |
| Exit-Codes | `sys.exit(code)` |
| Farbige Ausgabe | `\033[...m` mit `os.isatty()` Check |

---

## Phasen

### Phase 1: Shared Library — Grundlagen

**Goal**: Die plattformunabhängigen Grundbausteine implementieren, die beide Skripte benötigen.

**Tasks**:

- [ ] **1.1** `ados_lib/__init__.py` — Package-Init mit Version (`__version__ = "2.0.0"`)
- [ ] **1.2** `ados_lib/types.py` — Dataclasses für Konfiguration:
  - `InstallConfig(mode, branch, dry_run, verbose, force, interactive, no_fetch, allow_non_root)`
  - `UninstallConfig(mode, dry_run, verbose, force)`
  - `Counters(added, updated, unchanged)` / `Counters(removed, skipped)`
- [ ] **1.3** `ados_lib/logger.py` — Logger-Modul:
  - `log_info(tag, msg)`, `log_warn(tag, msg)`, `log_err(tag, msg)`, `log_debug(tag, msg, verbose)`
  - Farbige Ausgabe wenn `sys.stderr.isatty()` / `sys.stdout.isatty()`
  - Gleiche Formatierung wie Bash: `[INFO]  (ados-install) message`
- [ ] **1.4** `ados_lib/platform_paths.py` — Plattform-spezifische Pfade:
  - `get_ados_home() -> Path` — `ADOS_HOME` oder `~/.ados`
  - `get_ados_repo_dir() -> Path` — `ADOS_REPO_DIR` oder `~/.ados/repo`
  - `get_opencode_global_dir() -> Path` — Plattformabhängig (Win: `%APPDATA%/opencode`, Linux: XDG, macOS: `~/.config/opencode`)
  - `get_ados_repo_url() -> str`, `get_ados_raw_url() -> str`
- [ ] **1.5** `ados_lib/manifest.py` — Datei-Listen (1:1 Kopie aus Bash):
  - `UPDATABLE_FILES: list[str]`
  - `TEMPLATE_DIR: str`
  - `PROJECT_FILES: list[str]`
  - `LOCAL_DIRS: list[str]`
  - `AGENT_FILES: list[str]` (für uninstall)
  - `COMMAND_FILES: list[str]` (für uninstall)
  - `LOCAL_UPDATABLE_FILES: list[str]` (für uninstall)
  - `LOCAL_TEMPLATE_FILES: list[str]` (für uninstall)

**Acceptance Criteria**:

- Alle Module importierbar ohne externe Deps
- `platform_paths` gibt korrekte Pfade auf Windows, Linux, macOS zurück
- Logger-Ausgabe identisch zum Bash-Format

**Files and modules**:

- `scripts/ados_lib/__init__.py` (new)
- `scripts/ados_lib/types.py` (new)
- `scripts/ados_lib/logger.py` (new)
- `scripts/ados_lib/platform_paths.py` (new)
- `scripts/ados_lib/manifest.py` (new)

**Tests**:

- `tests/test_platform_paths.py` — Pfade pro Plattform mit gemocktem `sys.platform` und `os.environ`
- Logger-Ausgabe manuell verifizieren (Formatierung, Farben)

**Completion signal**: `feat: add ados_lib shared library (types, logger, platform_paths, manifest)`

---

### Phase 2: Shared Library — Dateioperationen & Sicherheit

**Goal**: Dateioperationen (Copy-with-Diff, Verzeichniserstellung, Löschung) und Sicherheitsprüfungen implementieren.

**Tasks**:

- [ ] **2.1** `ados_lib/file_ops.py` — Dateioperationen:
  - `copy_file_with_diff(src, dest, label, config, counters, updatable=False) -> None`
    - Symlink-Erkennung (`Path.is_symlink()`) → ersetzen durch Kopie
    - Inhaltsvergleich (`filecmp.cmp(shallow=False)`)
    - Force-Mode / Interactive-Mode / Updatable-Mode / Global-Mode Logik
    - `prompt_diff_overwrite(src, dest, label)` mit `difflib.unified_diff()`
  - `copy_updatable_file(src, dest, label, config, counters)` — Wrapper
  - `ensure_dir(dir_path, label, config) -> None`
  - `remove_file(path, label, config, counters) -> None`
- [ ] **2.2** `ados_lib/gitignore.py` — .gitignore-Manipulation:
  - `file_contains_line(file_path, pattern) -> bool`
  - `ensure_gitignore_entry(gitignore_path, entry, config) -> None`
- [ ] **2.3** `ados_lib/safety.py` — Sicherheitsprüfungen:
  - `validate_paths(config) -> None` — Warnung wenn ADOS_HOME/OPENCODE_GLOBAL_DIR außerhalb `$HOME`
  - `safe_rmdir(dir_path, label, config) -> None` — Pfadtiefenprüfung:
    - Leerer Pfad → Fehler
    - Root / Home → Fehler
    - Minimale Pfadtiefe (≥3 Komponenten auf Unix, ≥3 auf Windows z.B. `C:\Users\user\dir`)
    - Plattformunabhängige Tiefenmessung: `len(Path(dir).resolve().parts)`

**Acceptance Criteria**:

- `copy_file_with_diff` verhält sich identisch zur Bash-Version in allen 6 Fällen (neu, identisch, diff+force, diff+interactive, diff+updatable, diff+project)
- `safe_rmdir` blockiert gefährliche Pfade auf allen Plattformen
- Interactive Mode zeigt unified diff und fragt nach Bestätigung

**Files and modules**:

- `scripts/ados_lib/file_ops.py` (new)
- `scripts/ados_lib/gitignore.py` (new)
- `scripts/ados_lib/safety.py` (new)

**Tests**:

- `tests/test_file_ops.py` — tempfile-basierte Tests für alle Copy-Szenarien
- `tests/test_safety.py` — safe_rmdir mit gefährlichen und sicheren Pfaden
- `tests/test_gitignore.py` — Einträge hinzufügen, Duplikaterkennung

**Completion signal**: `feat: add file_ops, gitignore, safety modules to ados_lib`

---

### Phase 3: Shared Library — Git-Operationen

**Goal**: Alle Git-Interaktionen (clone, pull, branch switch, auto-fetch) als plattformunabhängige Funktionen implementieren.

**Tasks**:

- [ ] **3.1** `ados_lib/git_ops.py` — Git-Operationen:
  - `require_git() -> None` — `shutil.which("git")` prüfen
  - `git_run(args, cwd=None, check=True, capture=True) -> subprocess.CompletedProcess`
    - Wrapper um `subprocess.run(["git"] + args, cwd=cwd, ...)`
    - Korrekte Encoding-Behandlung (`encoding="utf-8"`, `errors="replace"`)
  - `clone_or_update_repo(config) -> None`
    - Prüfen ob `.git` existiert in `ADOS_REPO_DIR`
    - Branch-Switch (`git fetch`, `git checkout`)
    - `git pull --ff-only`
    - Versions-Reporting (before/after SHA)
  - `auto_fetch_source(source_dir, config) -> None`
    - Skip-Bedingungen (no_fetch, ADOS_SOURCE_DIR gesetzt, kein Git-Repo)
    - Branch-Switch falls nötig
    - `git pull --ff-only` mit Fallback-Warnung
  - `resolve_source_dir(config) -> Path`
    - 1. `ADOS_SOURCE_DIR` Umgebungsvariable
    - 2. Skript-eigenes Repo (`Path(__file__).resolve().parent.parent`)
    - 3. Globale Installation (`ADOS_REPO_DIR`)
  - `require_project_root(allow_non_root, config) -> None`
    - `.git` Verzeichnis prüfen
    - `git rev-parse --show-toplevel` für Monorepo-Support
  - `get_short_sha(repo_dir) -> str | None`
  - `get_current_branch(repo_dir) -> str | None`

**Acceptance Criteria**:

- Git-Befehle werden als Listen übergeben (kein `shell=True`)
- `resolve_source_dir` findet Quelle in gleicher Reihenfolge wie Bash-Version
- Fehler bei Git-Operationen werden sauber geloggt, nicht als Exception geworfen (außer bei kritischen Fehlern)

**Files and modules**:

- `scripts/ados_lib/git_ops.py` (new)

**Tests**:

- `tests/test_git_ops.py` — mit `unittest.mock.patch` für `subprocess.run`
- Mocken von `shutil.which` für `require_git`

**Completion signal**: `feat: add git_ops module to ados_lib`

---

### Phase 4: Install-Skript (`install.py`)

**Goal**: Das komplette Install-Skript als Python-Einstiegspunkt implementieren mit identischer CLI-Schnittstelle.

**Tasks**:

- [ ] **4.1** `ados_lib/cli.py` — CLI-Parsing mit argparse:
  - `parse_install_args(argv) -> InstallConfig`
  - `parse_uninstall_args(argv) -> UninstallConfig`
  - Gleiche Flags wie Bash: `-g/--global`, `-l/--local`, `-b/--branch`, `-n/--dry-run`, `-v/--verbose`, `-f/--force`, `-i/--interactive`, `--no-fetch`, `--allow-non-root`, `-h/--help`, `-V/--version`
  - Default-Verhalten: `--local` wenn kein Modus angegeben
- [ ] **4.2** `scripts/install.py` — Hauptskript:
  - Shebang: `#!/usr/bin/env python3`
  - Signal-Handler für `SIGINT` (Interrupt)
  - `do_global_install(config)`:
    - `require_git()`
    - `validate_paths(config)`
    - `clone_or_update_repo(config)`
    - `install_global_files(config, counters)` — Agent/Command `.md`-Dateien kopieren
    - Summary-Ausgabe
  - `do_local_install(config)`:
    - `require_project_root(config)`
    - `validate_paths(config)`
    - `resolve_source_dir(config)`
    - `auto_fetch_source(source_dir, config)`
    - `install_local_files(source_dir, config, counters)`:
      - Project-specific files
      - Updatable files
      - Templates (glob `*.md` aus Template-Dir)
      - Directory stubs
      - .gitignore-Einträge
    - Summary-Ausgabe mit Next-Steps
  - `main(argv=None)` — testbarer Einstiegspunkt
- [ ] **4.3** Umgebungsvariablen-Support:
  - `ADOS_REPO_URL`, `ADOS_RAW_URL`, `ADOS_HOME`, `ADOS_REPO_DIR`, `OPENCODE_GLOBAL_DIR`, `ADOS_SOURCE_DIR`
  - `DRY_RUN`, `VERBOSE`, `FORCE`, `INTERACTIVE`, `NO_FETCH`, `ADOS_BRANCH`, `ALLOW_NON_ROOT`
- [ ] **4.4** Exit-Codes identisch zur Bash-Version:
  - `0` = Success, `2` = Usage, `3` = Config, `4` = Runtime, `5` = External

**Acceptance Criteria**:

- `python3 scripts/install.py --help` zeigt identische Hilfe-Ausgabe (inhaltlich, nicht zeichengenau)
- `python3 scripts/install.py --global` führt identische Operationen aus wie `bash scripts/install.sh --global`
- `python3 scripts/install.py --local --dry-run` zeigt gleiche Dateioperationen
- Alle Umgebungsvariablen werden respektiert

**Files and modules**:

- `scripts/ados_lib/cli.py` (new)
- `scripts/install.py` (new)

**Tests**:

- `tests/test_install_local.py` — lokale Installation in TMP-Verzeichnis mit Mock-Source
- `tests/test_install_global.py` — globale Installation mit gemocktem Git und Dateisystem

**Completion signal**: `feat: add portable install.py with full CLI parity`

---

### Phase 5: Uninstall-Skript (`uninstall.py`)

**Goal**: Das komplette Uninstall-Skript als Python-Einstiegspunkt implementieren.

**Tasks**:

- [ ] **5.1** `scripts/uninstall.py` — Hauptskript:
  - Shebang: `#!/usr/bin/env python3`
  - `do_global_uninstall(config)`:
    - Bestätigungsprompt (skip bei `--force` oder `--dry-run`)
    - `remove_global_agents(config, counters)` — Agent-Dateien aus `OPENCODE_GLOBAL_DIR/agent/`
    - `remove_global_commands(config, counters)` — Command-Dateien aus `OPENCODE_GLOBAL_DIR/command/`
    - `safe_rmdir(ADOS_HOME, config)` — ADOS Home-Verzeichnis entfernen
    - Summary-Ausgabe
  - `do_local_uninstall(config)`:
    - `require_project_root(config)` (strikte Variante, kein `--allow-non-root`)
    - Bestätigungsprompt
    - `remove_local_files(config, counters)`:
      - Project-specific files
      - Updatable files
      - Template files
      - Leere Verzeichnisse entfernen (`Path.iterdir()` Check statt `ls -A`)
    - Summary-Ausgabe
  - `confirm_action(message, config) -> bool`
  - `main(argv=None)` — testbarer Einstiegspunkt

**Acceptance Criteria**:

- `python3 scripts/uninstall.py --help` zeigt korrekte Hilfe
- `python3 scripts/uninstall.py --global --dry-run` listet gleiche Dateien wie Bash-Version
- `safe_rmdir` blockiert gefährliche Pfade identisch zur Bash-Version
- Leere-Verzeichnis-Check funktioniert auf allen Plattformen

**Files and modules**:

- `scripts/uninstall.py` (new)

**Tests**:

- `tests/test_uninstall_local.py` — lokale Deinstallation mit Setup/Teardown
- `tests/test_uninstall_global.py` — globale Deinstallation mit Mock-Verzeichnisstruktur

**Completion signal**: `feat: add portable uninstall.py with full CLI parity`

---

### Phase 6: Cross-Platform-Tests & CI

**Goal**: Sicherstellen, dass alle Module auf allen drei Plattformen korrekt funktionieren.

**Tasks**:

- [ ] **6.1** Test-Runner Setup:
  - `scripts/tests/__init__.py` und Test-Helpers (tempdir Fixture, Mock-ADOS-Source Creator)
  - Alle Tests mit `python -m unittest discover -s scripts/tests` ausführbar
- [ ] **6.2** Integrationstests:
  - `tests/test_install_integration.py` — Vollständiger Install-Roundtrip in TMP-Verzeichnis:
    1. Mock-ADOS-Source anlegen (Fake-Repo mit `.opencode/agent/*.md` etc.)
    2. `install.py --local --no-fetch` ausführen (mit `ADOS_SOURCE_DIR` gesetzt)
    3. Alle erwarteten Dateien/Verzeichnisse prüfen
    4. Erneut ausführen → Idempotenz prüfen (Counters: 0 added, 0 updated, N unchanged)
    5. Datei ändern → Erneut ausführen → Update prüfen
  - `tests/test_uninstall_integration.py` — Vollständiger Uninstall-Roundtrip
- [ ] **6.3** Plattform-spezifische Edge Cases:
  - Windows: Pfade mit Leerzeichen (`C:\Users\John Doe\...`)
  - Windows: Lange Pfade (>260 Zeichen)
  - macOS: Case-insensitive Dateisystem
  - Linux: XDG_CONFIG_HOME Override
- [ ] **6.4** README-Abschnitt aktualisieren — Installationsanweisungen für alle Plattformen

> **Aus Scope entfernt:** GitHub Actions CI-Workflow (`.github/workflows/test-scripts.yml`) wird als separates Vorhaben behandelt. Das Projekt verwendet aktuell keine GitHub Actions. Tests werden bis dahin manuell auf den Zielplattformen ausgeführt.

**Acceptance Criteria**:

- Tests laufen grün auf Windows, Linux und macOS (manuelle Verifikation)
- Tests laufen mit Python 3.8 und Python 3.12
- Kein Test benötigt externe Pakete (nur stdlib `unittest`)

**Files and modules**:

- `scripts/tests/__init__.py` (new)
- `scripts/tests/test_install_integration.py` (new)
- `scripts/tests/test_uninstall_integration.py` (new)

**Tests**:

- Manuelle Verifikation auf allen 3 Plattformen mit 2 Python-Versionen

**Completion signal**: `test: add cross-platform test suite and CI for Python install scripts`

---

### Phase 7: Dokumentation & One-Liner-Install

**Goal**: Dokumentation aktualisieren und den One-Liner-Install für die Python-Version bereitstellen.

**Tasks**:

- [ ] **7.1** One-Liner-Install für Python:
  - Linux/macOS: `curl -fsSL https://raw.githubusercontent.com/.../scripts/install.py | python3 - --global`
  - Windows PowerShell: `irm https://raw.githubusercontent.com/.../scripts/install.py | python - --global`
  - **Herausforderung:** `install.py` importiert `ados_lib/` → Single-File-Bootstrapper nötig:
    - Option A: Kleines `bootstrap.py` das Repo cloned und dann `install.py --global` aufruft
    - Option B: `install.py` fallback auf Single-File-Mode wenn `ados_lib` nicht importierbar
  - Empfehlung: **Option A** — separater `bootstrap.py` (~30 Zeilen) der das Repo klont und `install.py` ausführt
- [ ] **7.2** `scripts/bootstrap.py` — Minimaler One-Liner-Einstiegspunkt:
  - Klont Repo nach `~/.ados/repo` (wie `--global` Phase 1 der Bash-Version)
  - Ruft `install.py --global` auf
  - Enthält kein `import ados_lib` — komplett eigenständig
- [ ] **7.3** `README.md` aktualisieren:
  - Installationsanweisungen für Windows, Linux, macOS
  - Python-Version-Hinweis (≥3.8)
  - Hinweis auf Bash-Variante als Fallback
- [ ] **7.4** `doc/guides/system-dependencies.md` aktualisieren:
  - Python 3.8+ als Abhängigkeit dokumentieren
  - Win/Linux/macOS Installationshinweise für Python
- [ ] **7.5** Bash-Skripte mit Deprecation-Hinweis versehen:
  - Kommentar am Anfang: `# DEPRECATED: Use install.py for cross-platform support`
  - Noch nicht entfernen

**Acceptance Criteria**:

- One-Liner-Install funktioniert auf Linux und macOS
- Windows-Installations-Anleitung ist dokumentiert
- README zeigt beide Varianten (Python empfohlen, Bash als Fallback)

**Files and modules**:

- `scripts/bootstrap.py` (new)
- `README.md` (updated)
- `doc/guides/system-dependencies.md` (updated)
- `scripts/install.sh` (updated — Deprecation-Hinweis)
- `scripts/uninstall.sh` (updated — Deprecation-Hinweis)

**Tests**:

- Manueller One-Liner-Test auf Linux, macOS, Windows

**Completion signal**: `docs: add cross-platform install documentation and one-liner bootstrap`

---

## Test-Szenarien

| ID | Szenario | Phase | Verifiziert |
|----|----------|-------|-------------|
| T1 | `platform_paths` gibt korrekte Pfade auf Win/Linux/macOS | 1 | Plattform-Mock |
| T2 | Logger-Format identisch zu Bash-Ausgabe | 1 | String-Vergleich |
| T3 | `copy_file_with_diff` — neue Datei anlegen | 2 | tempdir |
| T4 | `copy_file_with_diff` — identische Datei überspringen | 2 | tempdir |
| T5 | `copy_file_with_diff` — Force-Update bei Diff | 2 | tempdir |
| T6 | `copy_file_with_diff` — Interactive-Mode Prompt | 2 | Mock input() |
| T7 | `copy_file_with_diff` — Updatable Auto-Update | 2 | tempdir |
| T8 | `copy_file_with_diff` — Project-specific preserve | 2 | tempdir |
| T9 | `copy_file_with_diff` — Symlink ersetzen | 2 | tempdir (Unix only) |
| T10 | `safe_rmdir` — Root-Pfad blockieren | 2 | Assert RuntimeError |
| T11 | `safe_rmdir` — Home-Pfad blockieren | 2 | Assert RuntimeError |
| T12 | `safe_rmdir` — flacher Pfad blockieren | 2 | Assert RuntimeError |
| T13 | `safe_rmdir` — normaler Pfad entfernen | 2 | tempdir |
| T14 | `gitignore_entry` — Eintrag hinzufügen | 2 | tempdir |
| T15 | `gitignore_entry` — Duplikat überspringen | 2 | tempdir |
| T16 | Git clone neues Repo | 3 | Mock subprocess |
| T17 | Git pull bestehendes Repo | 3 | Mock subprocess |
| T18 | Git Branch-Switch | 3 | Mock subprocess |
| T19 | `resolve_source_dir` — ADOS_SOURCE_DIR Override | 3 | Mock environ |
| T20 | `resolve_source_dir` — Skript-eigenes Repo | 3 | tempdir |
| T21 | Install --local vollständiger Roundtrip | 4 | Integration |
| T22 | Install --global vollständiger Roundtrip | 4 | Integration |
| T23 | Install Idempotenz (zweiter Lauf) | 4 | Integration |
| T24 | Install --dry-run keine Änderungen | 4 | Integration |
| T25 | Uninstall --local vollständig | 5 | Integration |
| T26 | Uninstall --global vollständig | 5 | Integration |
| T27 | Uninstall --force ohne Prompt | 5 | Mock input() |
| T28 | Windows-Pfade mit Leerzeichen | 6 | Plattform-Test |
| T29 | XDG_CONFIG_HOME Override auf Linux | 6 | Env-Mock |
| T30 | One-Liner bootstrap.py | 7 | Manuell |

---

## Artifacts and Links

| Artifact | Location | Type |
|----------|----------|------|
| Konzeptdokument | `doc/planning/portable-install-scripts-concept.md` | Konzept |
| Implementierungsplan (dieses Dokument) | `doc/planning/portable-install-scripts-plan.md` | Plan |
| Shared Library | `scripts/ados_lib/` | Code |
| Install-Skript (Python) | `scripts/install.py` | Code |
| Uninstall-Skript (Python) | `scripts/uninstall.py` | Code |
| Bootstrap-Skript | `scripts/bootstrap.py` | Code |
| Unit-Tests | `scripts/tests/` | Tests |

---

## Plan Revision Log

| Version | Datum | Autor | Änderungen |
|---------|-------|-------|------------|
| 1.0 | 2026-04-30 | — | Initialer Plan |
| 1.1 | 2026-04-30 | — | GitHub Actions CI (6.4) als separates Vorhaben ausgelagert; Task-Nummerierung in Phase 6 angepasst |

## Execution Log

| Phase | Status | Started | Completed | Commit | Notes |
|-------|--------|---------|-----------|--------|-------|
| 1 | — | | | | |
| 2 | — | | | | |
| 3 | — | | | | |
| 4 | — | | | | |
| 5 | — | | | | |
| 6 | — | | | | |
| 7 | — | | | | |







