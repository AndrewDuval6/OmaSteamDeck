"""Read-only runtime preflight; imports dependencies without starting a GUI."""
from importlib import import_module
import os
from pathlib import Path
import sys


def check_runtime(require_webengine=True):
    """Return actionable errors. Import success does not establish WebGL support."""
    errors = []
    try:
        import_module('PySide6.QtWidgets').QApplication
    except (ImportError, OSError, AttributeError) as exc:
        return ['Qt Widgets is unavailable: ' + str(exc)]
    if not require_webengine:
        return errors
    for module, symbol in (
        ('PySide6.QtWebEngineWidgets', 'QWebEngineView'),
        ('PySide6.QtWebChannel', 'QWebChannel'),
    ):
        try:
            getattr(import_module(module), symbol)
        except (ImportError, OSError, AttributeError) as exc:
            errors.append(module + ' is unavailable: ' + str(exc))
    if errors:
        return errors
    try:
        info = import_module('PySide6.QtCore').QLibraryInfo
        override = os.environ.get('QTWEBENGINEPROCESS_PATH')
        helper = Path(override) if override else Path(
            info.path(info.LibraryPath.LibraryExecutablesPath)
        ) / 'QtWebEngineProcess'
        if not helper.is_file() or not os.access(helper, os.X_OK):
            errors.append('Qt WebEngine helper is missing or not executable: ' + str(helper))
    except (ImportError, OSError, AttributeError) as exc:
        errors.append('Could not locate Qt WebEngine helper: ' + str(exc))
    return errors


def main(args=None):
    args = sys.argv[1:] if args is None else args
    require_webengine = not any(arg in ('--skip-splash', '--help', '-h') for arg in args)
    errors = check_runtime(require_webengine)
    if not errors:
        return 0
    print('OmaFlow cannot start with this Python runtime:', file=sys.stderr)
    for error in errors:
        print('  ' + error, file=sys.stderr)
    print(
        '\nUse a complete user-local PySide6 installation from the repository:\n'
        '  python3 -m venv .venv\n'
        '  .venv/bin/python -m pip install --upgrade -e .\n'
        '  ./run.sh\n'
        '\nFor native-only diagnostics, use ./run.sh --skip-splash.\n'
        'No system packages or settings have been changed.\n'
        'WebGL rendering is checked separately when the startup view opens.',
        file=sys.stderr,
    )
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
