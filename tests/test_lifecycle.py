"""Exercise the real application entry point in a separate, isolated process."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest


class ProcessLifecycleTests(unittest.TestCase):
    def test_single_instance_guard_and_stale_lock_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / 'state.json'
            env = dict(os.environ, QT_QPA_PLATFORM='offscreen')
            env.pop('HYPRLAND_INSTANCE_SIGNATURE', None)
            command = [sys.executable, '-m', 'omasteamdeck.app', '--windowed',
                       '--skip-splash', '--config', str(config)]

            def start():
                process = subprocess.Popen(command, env=env, stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE, text=True)
                self.addCleanup(self.stop, process)
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    self.assertIsNone(process.poll(), 'Native app exited during startup')
                    try:
                        if config.with_suffix('.lock').read_text().splitlines()[0] == str(process.pid):
                            return process
                    except (OSError, IndexError):
                        pass
                    time.sleep(.05)
                self.fail('Native app did not acquire its profile lock')

            first = start()
            second = subprocess.run(command, env=env, capture_output=True, text=True, timeout=15)
            self.assertEqual(second.returncode, 1)
            self.assertIn('already running', second.stderr)
            self.assertIsNone(first.poll())
            # Simulate an interrupted session: a dead process must not block restart.
            self.stop(first)
            restarted = start()
            time.sleep(.25)
            self.assertIsNone(restarted.poll())
            self.stop(restarted)

    @staticmethod
    def stop(process):
        if process.poll() is None:
            process.terminate()
        try:
            process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate(timeout=5)


if __name__ == '__main__':
    unittest.main()
