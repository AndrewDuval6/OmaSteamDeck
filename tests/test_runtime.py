import contextlib
import io
import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from omasteamdeck.runtime import check_runtime, main


class RuntimeTests(unittest.TestCase):
    def test_native_mode_does_not_import_webengine(self):
        with patch('omasteamdeck.runtime.import_module', return_value=SimpleNamespace(QApplication=object)) as load:
            self.assertEqual(check_runtime(False), [])
            load.assert_called_once_with('PySide6.QtWidgets')

    def test_missing_engine_reports_original_library_error(self):
        def load(module):
            if module == 'PySide6.QtWidgets':
                return SimpleNamespace(QApplication=object)
            raise ImportError('libQt6WebEngineWidgets.so.6 not found')
        with patch('omasteamdeck.runtime.import_module', side_effect=load):
            errors = check_runtime()
            self.assertTrue(any('libQt6WebEngineWidgets.so.6' in error for error in errors))

    def test_helper_must_be_present_and_executable(self):
        with tempfile.TemporaryDirectory() as temp:
            helper = Path(temp)/'QtWebEngineProcess'
            def load(module):
                if module == 'PySide6.QtWidgets': return SimpleNamespace(QApplication=object)
                if module == 'PySide6.QtWebEngineWidgets': return SimpleNamespace(QWebEngineView=object)
                if module == 'PySide6.QtWebChannel': return SimpleNamespace(QWebChannel=object)
                return SimpleNamespace(QLibraryInfo=SimpleNamespace(LibraryPath=SimpleNamespace(LibraryExecutablesPath=1), path=lambda _: temp))
            with patch('omasteamdeck.runtime.import_module',side_effect=load), patch.dict('os.environ',{'QTWEBENGINEPROCESS_PATH':str(helper)}):
                self.assertTrue(check_runtime())
                helper.write_text('#!/bin/sh\n'); helper.chmod(0o755)
                self.assertEqual(check_runtime(), [])

    def test_failure_is_actionable_and_skip_splash_is_explicit(self):
        with patch('omasteamdeck.runtime.check_runtime', return_value=['WebEngine missing']) as check:
            out=io.StringIO()
            with contextlib.redirect_stderr(out): self.assertEqual(main([]), 1)
            self.assertIn('python3 -m venv .venv',out.getvalue())
            check.assert_called_once_with(True)
        with patch('omasteamdeck.runtime.check_runtime',return_value=[]) as check:
            self.assertEqual(main(['--skip-splash','--windowed']),0)
            check.assert_called_once_with(False)
