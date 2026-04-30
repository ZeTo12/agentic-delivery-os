# Konzept: Portable Install-/Uninstall-Skripte

> **Status:** Entwurf  
> **Datum:** 2026-04-30  
> **Kontext:** `scripts/install.sh` und `scripts/uninstall.sh` sind aktuell reine Bash-Skripte (bash≥4). Sie laufen auf macOS und Linux, **nicht** auf Windows (außer via WSL/Git Bash). Ziel ist native Plattformunterstützung für Windows, Linux und macOS.

---

## Ist-Zustand

| Aspekt | install.sh | uninstall.sh |
|--------|-----------|-------------|
| Zeilen | ~760 | ~429 |
| Abhängigkeiten | bash≥4, git, diff, cp, mkdir | bash≥4, rm, grep |
| Kernfunktionalität | Dateien kopieren (mit Diff-Check), Verzeichnisse anlegen, Git-Operationen (clone/pull/checkout), .gitignore-Manipulation, interaktive Prompts, Argument-Parsing, Logging | Dateien löschen, Verzeichnisse entfernen (safety checks), Bestätigungsprompts, Argument-Parsing, Logging |
| Modi | `--global` / `--local` | `--global` / `--local` |
| One-Liner-Install | `curl \| bash -s --` | – |
| Testbarkeit | Mockable Wrappers (`_git`, `_cp`, etc.) | Mockable Wrappers (`_rm`) |

### Verwendete OS-spezifische Features

- `set -Eeuo pipefail`, `shopt -s inherit_errexit` (Bash-spezifisch)
- `BASH_SOURCE[0]` zur Skript-Lokalisierung
- `realpath -m` / `readlink -m` (Linux-spezifisch, macOS braucht `greadlink`)
- `tr -cd '/' | wc -c` für Pfadtiefenprüfung
- `diff --color=auto -u` für interaktiven Modus
- `ls -A` für leere Verzeichnisse
- Unix-Pfadkonventionen (`~/.ados`, `~/.config/opencode`)

---

## Anforderungen an die portable Lösung

1. **Native Ausführung** auf Windows (ohne WSL), Linux und macOS
2. **Gleiche Funktionalität** wie die bestehenden Bash-Skripte
3. **One-Liner-Install** muss weiterhin möglich sein (mindestens für Linux/macOS)
4. **Testbarkeit** muss erhalten bleiben oder verbessert werden
5. **Minimale externe Abhängigkeiten** — idealerweise nur eine Runtime
6. **XDG-konforme Pfade** auf Linux, AppData auf Windows, `~/Library` auf macOS
7. **Git-Interaktion** bleibt erforderlich (clone, pull, checkout)
8. **Idempotenz** — erneutes Ausführen ist sicher
9. **Wartbarkeit** — das Team muss die Sprache beherrschen oder schnell lernen können

---

## Option 1: Node.js (JavaScript/TypeScript)

### Beschreibung

Umschreiben der Skripte als Node.js-CLI-Tools. Node.js ist auf allen drei Plattformen verfügbar und bietet mit dem `fs`-, `path`- und `child_process`-Modul alle nötigen Primitiven.

### Architektur

```
scripts/
├── install.mjs          # Einstiegspunkt (oder .ts kompiliert)
├── uninstall.mjs
├── lib/
│   ├── platform.mjs     # OS-abhängige Pfade (XDG, AppData, ~/Library)
│   ├── files.mjs        # copy_file_with_diff, ensure_dir, remove_file
│   ├── git.mjs          # clone_or_update_repo, auto_fetch_source
│   ├── logger.mjs       # log_info, log_warn, log_err, log_debug
│   ├── cli.mjs          # Argument-Parsing
│   └── manifest.mjs     # ADOS_UPDATABLE_FILES, ADOS_LOCAL_DIRS, etc.
├── package.json
└── __tests__/
    ├── files.test.mjs
    ├── git.test.mjs
    └── install.test.mjs
```

### Plattform-spezifische Pfade

```javascript
import { homedir, platform } from 'os';
import { join } from 'path';

function getAdosHome() {
  return process.env.ADOS_HOME || join(homedir(), '.ados');
}

function getOpencodeGlobalDir() {
  if (process.env.OPENCODE_GLOBAL_DIR) return process.env.OPENCODE_GLOBAL_DIR;
  switch (platform()) {
    case 'win32':  return join(process.env.APPDATA || join(homedir(), 'AppData', 'Roaming'), 'opencode');
    case 'darwin': return join(homedir(), '.config', 'opencode');
    default:       return join(process.env.XDG_CONFIG_HOME || join(homedir(), '.config'), 'opencode');
  }
}
```

### Vorteile

| Vorteil | Detail |
|---------|--------|
| **Weite Verbreitung** | Node.js ist bei den meisten Entwicklern bereits installiert |
| **Nativer Plattformsupport** | `fs`, `path`, `child_process` abstrahieren OS-Unterschiede |
| **Testbarkeit** | Jest/Vitest mit Mocking von fs und child_process |
| **One-Liner bleibt möglich** | `npx` oder Download + `node install.mjs` |
| **Keine Kompilierung nötig** | `.mjs`-Dateien laufen direkt |
| **TypeScript optional** | Kann schrittweise eingeführt werden für bessere Typsicherheit |
| **npm-Ökosystem** | Libraries wie `commander` (CLI), `chalk` (Farben), `diff` (Diff-Anzeige) verfügbar |

### Nachteile

| Nachteil | Detail |
|----------|--------|
| **Runtime erforderlich** | Node.js muss installiert sein (~100 MB) |
| **Versionsfragmentierung** | Unterschiedliche Node-Versionen auf verschiedenen Systemen |
| **Overhead** | Node.js-Startup ist langsamer als ein Bash-Skript (~200ms vs ~10ms) |
| **Dependency-Management** | `package.json` + `node_modules` muss verwaltet werden (oder zero-dep schreiben) |
| **curl\|bash Paradigma bricht** | One-Liner muss umgeschrieben werden auf `curl \| node` oder zweistufig |

### Aufwand

| Aspekt | Schätzung |
|--------|-----------|
| Initiale Portierung | 3–4 Tage |
| Testabdeckung | 1–2 Tage |
| CI-Integration (3 Plattformen) | 0.5 Tage |
| **Gesamt** | **~5–6 Tage** |

---

## Option 2: Python (nur Standardbibliothek)

### Beschreibung

Umschreiben als Python-Skripte, die ausschließlich die Standardbibliothek verwenden (kein `pip install`). Python 3.8+ ist auf macOS und den meisten Linux-Distributionen vorinstalliert; auf Windows ist es über den Microsoft Store oder python.org leicht installierbar.

### Architektur

```
scripts/
├── install.py            # Einstiegspunkt (chmod +x, Shebang: #!/usr/bin/env python3)
├── uninstall.py
├── ados_lib/
│   ├── __init__.py
│   ├── platform_paths.py # OS-abhängige Pfade
│   ├── file_ops.py       # copy_file_with_diff, ensure_dir, remove_file
│   ├── git_ops.py        # clone_or_update_repo, auto_fetch_source
│   ├── logger.py         # Logging
│   ├── cli.py            # argparse-basiertes Argument-Parsing
│   └── manifest.py       # Datei-Listen und Verzeichnis-Stubs
└── tests/
    ├── test_file_ops.py
    ├── test_git_ops.py
    └── test_install.py
```

### Plattform-spezifische Pfade

```python
import os
import sys
from pathlib import Path

def get_ados_home() -> Path:
    if env := os.environ.get("ADOS_HOME"):
        return Path(env)
    return Path.home() / ".ados"

def get_opencode_global_dir() -> Path:
    if env := os.environ.get("OPENCODE_GLOBAL_DIR"):
        return Path(env)
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / "opencode"
    elif sys.platform == "darwin":
        return Path.home() / ".config" / "opencode"
    else:
        xdg = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
        return Path(xdg) / "opencode"
```

### Vorteile

| Vorteil | Detail |
|---------|--------|
| **Oft vorinstalliert** | macOS und Linux haben Python 3; Windows hat Store-Paket |
| **Keine externen Deps** | `pathlib`, `shutil`, `subprocess`, `argparse`, `difflib` — alles in der stdlib |
| **Exzellente Pfadabstraktion** | `pathlib.Path` normalisiert automatisch `/` vs `\` |
| **filecmp für Diffs** | `filecmp.cmp()` ersetzt `diff -q`, `difflib.unified_diff()` ersetzt `diff -u` |
| **Eingebautes argparse** | Mächtiger als manuelles Bash-Parsing |
| **Testbarkeit** | `unittest` / `pytest` mit `unittest.mock` für Dateisystem und subprocess |
| **One-Liner möglich** | `curl -fsSL ... \| python3 -` (mit eingebettetem Bootstrap) |
| **Breite Bekanntheit** | Python ist die am meisten verbreitete Skriptsprache |

### Nachteile

| Nachteil | Detail |
|----------|--------|
| **Python nicht garantiert auf Windows** | Muss ggf. erst installiert werden |
| **Versionsproblematik** | `python` vs `python3` Aliase variieren zwischen Systemen |
| **Single-File-Delivery schwierig** | Multi-Modul-Struktur erfordert Download des ganzen `scripts/`-Ordners |
| **Kein natives shutil.copytree overwrite** | Vor Python 3.8 fehlt `dirs_exist_ok=True` |
| **Git-Interaktion** | Muss über `subprocess.run(["git", ...])` laufen — git muss installiert sein |

### Aufwand

| Aspekt | Schätzung |
|--------|-----------|
| Initiale Portierung | 2–3 Tage |
| Testabdeckung | 1–2 Tage |
| CI-Integration (3 Plattformen) | 0.5 Tage |
| **Gesamt** | **~4–5 Tage** |

---

## Option 3: Go (kompilierte Binaries)

### Beschreibung

Umschreiben als Go-Programm, das zu nativen Binaries für alle drei Plattformen kompiliert wird. Go hat exzellente Cross-Compilation-Unterstützung und erzeugt statisch gelinkte Executables ohne Runtime-Abhängigkeiten.

### Architektur

```
scripts/
├── cmd/
│   ├── ados-install/
│   │   └── main.go        # Einstiegspunkt install
│   └── ados-uninstall/
│       └── main.go        # Einstiegspunkt uninstall
├── internal/
│   ├── platform/
│   │   └── paths.go       # OS-abhängige Pfade (build tags)
│   ├── fileops/
│   │   └── copy.go        # copy_file_with_diff, ensure_dir, remove
│   ├── gitops/
│   │   └── repo.go        # clone_or_update_repo (exec oder go-git)
│   ├── logger/
│   │   └── logger.go      # Logging
│   ├── cli/
│   │   └── flags.go       # Argument-Parsing (flag oder cobra)
│   └── manifest/
│       └── manifest.go    # Datei-Listen
├── go.mod
├── go.sum
└── Makefile                # Cross-Compile-Targets
```

### Cross-Compilation

```makefile
# Makefile
build-all:
	GOOS=linux   GOARCH=amd64 go build -o dist/ados-install-linux-amd64   ./cmd/ados-install
	GOOS=darwin  GOARCH=amd64 go build -o dist/ados-install-darwin-amd64  ./cmd/ados-install
	GOOS=darwin  GOARCH=arm64 go build -o dist/ados-install-darwin-arm64  ./cmd/ados-install
	GOOS=windows GOARCH=amd64 go build -o dist/ados-install-windows.exe  ./cmd/ados-install
```

### Plattform-spezifische Pfade

```go
package platform

import (
    "os"
    "path/filepath"
    "runtime"
)

func AdosHome() string {
    if v := os.Getenv("ADOS_HOME"); v != "" {
        return v
    }
    home, _ := os.UserHomeDir()
    return filepath.Join(home, ".ados")
}

func OpencodeGlobalDir() string {
    if v := os.Getenv("OPENCODE_GLOBAL_DIR"); v != "" {
        return v
    }
    home, _ := os.UserHomeDir()
    switch runtime.GOOS {
    case "windows":
        appdata := os.Getenv("APPDATA")
        if appdata == "" {
            appdata = filepath.Join(home, "AppData", "Roaming")
        }
        return filepath.Join(appdata, "opencode")
    default:
        xdg := os.Getenv("XDG_CONFIG_HOME")
        if xdg == "" {
            xdg = filepath.Join(home, ".config")
        }
        return filepath.Join(xdg, "opencode")
    }
}
```

### Vorteile

| Vorteil | Detail |
|---------|--------|
| **Keine Runtime nötig** | Statische Binaries — kein Node, kein Python, kein Bash |
| **Schnellster Start** | ~5ms Startup vs ~200ms (Node) oder ~100ms (Python) |
| **Echte Cross-Compilation** | `GOOS`/`GOARCH` in CI erzeugt alle Binaries in einem Schritt |
| **Starke Typsicherheit** | Compile-Time-Checks verhindern viele Fehlerklassen |
| **Single-Binary-Distribution** | Ein Download, keine `node_modules` oder Python-Venv |
| **go-git Library** | Native Git-Implementierung ohne `git`-CLI-Abhängigkeit möglich |
| **Testbarkeit** | Go hat eingebautes Test-Framework (`testing`) mit Mocking-Support |
| **GitHub Releases** | Binaries können als Release-Assets bereitgestellt werden |

### Nachteile

| Nachteil | Detail |
|----------|--------|
| **Go-Kenntnisse erforderlich** | Team muss Go beherrschen |
| **Höherer initialer Aufwand** | Kompilierter Code braucht mehr Boilerplate als Skripte |
| **Build-Schritt nötig** | Änderungen erfordern Kompilierung vor dem Testen |
| **Binary-Größe** | ~10–15 MB pro ausführbare Datei |
| **curl\|bash Paradigma bricht** | Muss durch plattformspezifischen Download-Link ersetzt werden |
| **Overengineering-Risiko** | Für ~1200 Zeilen Bash könnte Go überdimensioniert sein |
| **Zwei Sprachen im Repo** | Go für Skripte + Bash für alles andere (tools/, tests) |

### Aufwand

| Aspekt | Schätzung |
|--------|-----------|
| Initiale Portierung | 4–6 Tage |
| Testabdeckung | 2–3 Tage |
| CI-Integration (Cross-Compile + 3 Plattformen) | 1 Tag |
| Release-Automation (GitHub Releases) | 0.5 Tage |
| **Gesamt** | **~8–10 Tage** |

---

## Vergleichsmatrix

| Kriterium | Option 1: Node.js | Option 2: Python | Option 3: Go |
|-----------|:-:|:-:|:-:|
| **Windows-Support** | ✅ Nativ | ✅ Nativ | ✅ Nativ |
| **Linux-Support** | ✅ Nativ | ✅ Nativ | ✅ Nativ |
| **macOS-Support** | ✅ Nativ | ✅ Nativ | ✅ Nativ |
| **Runtime erforderlich** | ⚠️ Node.js | ⚠️ Python 3.8+ | ✅ Keine |
| **Vorinstalliert-Wahrscheinlichkeit** | 🟡 Hoch (Devs) | 🟢 Sehr hoch | 🔴 Niedrig |
| **Externe Dependencies** | ⚠️ Optional (npm) | ✅ Keine (stdlib) | ✅ Keine (oder go-git) |
| **One-Liner-Install** | 🟡 `curl\|node` | 🟢 `curl\|python3` | 🟡 Download-Script |
| **Startup-Performance** | 🟡 ~200ms | 🟢 ~100ms | ✅ ~5ms |
| **Testbarkeit** | ✅ Jest/Vitest | ✅ pytest/unittest | ✅ go test |
| **Wartungsaufwand** | 🟢 Niedrig | 🟢 Niedrig | 🟡 Mittel |
| **Portierungsaufwand** | 🟡 5–6 Tage | 🟢 4–5 Tage | 🔴 8–10 Tage |
| **Typsicherheit** | 🟡 Optional (TS) | 🟡 Type Hints | ✅ Nativ |
| **Binary-Distribution** | ❌ Nein | ❌ Nein (pyinstaller möglich) | ✅ Ja |
| **Code-Komplexität** | 🟢 Niedrig | 🟢 Niedrig | 🟡 Mittel |

---

## Empfehlung

**Option 2 (Python)** bietet das beste Verhältnis aus Portabilität, Aufwand und Wartbarkeit:

1. **Geringster Aufwand** — `pathlib`, `shutil`, `difflib`, `argparse` decken alle Anforderungen ab, ohne externe Pakete.
2. **Breiteste Verfügbarkeit** — Python 3 ist auf macOS/Linux vorinstalliert; Windows-Nutzer können es über den Microsoft Store mit einem Klick installieren.
3. **Kein Build-Schritt** — Skripte laufen direkt, genau wie die aktuellen Bash-Skripte.
4. **One-Liner bleibt möglich** — `curl -fsSL ... | python3 -` funktioniert analog zu `curl | bash`.
5. **pathlib abstrahiert Pfade** — `/` vs `\` wird transparent gehandhabt.
6. **Team-Kompetenz** — Python ist die am weitesten verbreitete Skriptsprache unter Entwicklern.

### Empfohlene Migrationsstrategie

1. **Phase 1:** Shared Library (`ados_lib/`) mit plattformunabhängigen Primitiven (file ops, git ops, logger, manifest)
2. **Phase 2:** `install.py` portieren — erst `--local`, dann `--global`
3. **Phase 3:** `uninstall.py` portieren
4. **Phase 4:** Tests mit `pytest` auf allen drei Plattformen (GitHub Actions Matrix)
5. **Phase 5:** Alte Bash-Skripte als deprecated markieren, dann entfernen

### Fallback-Überlegung

Falls Go-Kenntnisse im Team vorhanden sind und Binary-Distribution wichtig wird (z.B. für Nutzer ohne Python), ist **Option 3 (Go)** die langfristig robusteste Lösung — allerdings mit signifikant höherem Initialaufwand.

