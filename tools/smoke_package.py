#!/usr/bin/env python3
"""Render a separately installed wheel; deliberately never add the source root."""
import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from pathlib import Path
import sys
import tempfile

from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
import omasteamdeck
from omasteamdeck.app import Shell, TABS
from omasteamdeck.core import State

expected_root = Path(sys.argv[1]).resolve()
assert Path(omasteamdeck.__file__).resolve().is_relative_to(expected_root), 'Imported source checkout instead of installed package'
app = QApplication([])
with tempfile.TemporaryDirectory() as directory:
    shell = Shell(State(Path(directory) / 'state.json'), windowed=True, skip_splash=True)
    try:
        assert not shell._background.isNull(), 'Packaged background is missing or unreadable'
        shell.choose_profile(0)
        for section in TABS:
            shell.set_tab(section)
            QTest.qWait(20)
            assert not shell.grab().isNull(), 'Installed package could not render ' + section
        print('PASS: installed wheel imports independently, loads bundled artwork and renders every section.')
    finally:
        shell.close()
