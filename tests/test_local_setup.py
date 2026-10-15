import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch, Mock
from core.setup.local_setup import LocalSetup, Cancelled


class SetupTests(unittest.TestCase):
    def service(self):
        service = LocalSetup(Mock())
        service.api = Mock(return_value={'done': True})
        service.pull = Mock()
        service.start_server = Mock()
        return service

    def test_existing_runtime_and_model_reused(self):
        s = self.service()
        s.available = Mock(return_value=[{'name': s.model}])
        s.run()
        s.start_server.assert_not_called()
        s.pull.assert_not_called()
        self.assertEqual(s.api.call_args.args[0], '/api/generate')

    def test_absent_runtime_and_model_prepared(self):
        s = self.service()
        s.available = Mock(side_effect=[None, [], [{'name': s.model}]])
        s.run()
        s.start_server.assert_called_once()
        s.pull.assert_called_once()

    def test_download_failure_never_signals_success(self):
        s = self.service()
        s.available = Mock(return_value=[])
        s.pull.side_effect = OSError('offline')
        with self.assertRaises(OSError):
            s.run()
        s.api.assert_not_called()

    def test_cancel_before_start_does_nothing(self):
        s = self.service()
        s.cancelled.set()
        with self.assertRaises(Cancelled):
            s.run()
        s.api.assert_not_called()

    def test_missing_after_download_is_not_ready(self):
        s = self.service()
        s.available = Mock(return_value=[])
        with self.assertRaisesRegex(RuntimeError, '찾지 못'):
            s.run()

    def test_load_error_is_not_ready(self):
        s = self.service()
        s.available = Mock(return_value=[{'name': s.model}])
        s.api.return_value = {'error': 'out of memory'}
        with self.assertRaisesRegex(RuntimeError, '실행하지 못'):
            s.run()

    def test_stream_requires_success_and_propagates_errors(self):
        import io
        for events, expected in [([{'status': 'pulling', 'completed': 12, 'total': 24}], '중단'),
                                 ([{'error': 'not found'}], 'not found')]:
            response = io.BytesIO(b'\n'.join(json.dumps(e).encode() for e in events))
            with patch('core.setup.local_setup.urlopen', return_value=response), patch('core.setup.local_setup.shutil.disk_usage', return_value=Mock(free=10**11)):
                with self.assertRaisesRegex(RuntimeError, expected):
                    LocalSetup(Mock()).pull()

    def test_stream_reports_progress(self):
        import io
        progress = Mock()
        response = io.BytesIO(b'{"completed":12,"total":24}\n{"status":"success"}\n')
        with patch('core.setup.local_setup.urlopen', return_value=response), patch('core.setup.local_setup.shutil.disk_usage', return_value=Mock(free=10**11)):
            LocalSetup(progress).pull()
        progress.assert_any_call('Qwen 모델 다운로드 중', 12, 24)

    def test_invalid_signature_does_not_install_and_unmounts(self):
        import io
        response = io.BytesIO(b'dmg')
        response.headers = {'Content-Length': '3'}
        with tempfile.TemporaryDirectory() as folder, patch('core.setup.local_setup.Path.home', return_value=Path(folder)), patch('core.setup.local_setup.macos_version', return_value=(14, 0)), patch('core.setup.local_setup.urlopen', return_value=response), patch('core.setup.local_setup.shutil.disk_usage', return_value=Mock(free=10**11)), patch('core.setup.local_setup.subprocess.run') as cleanup:
            s = LocalSetup(Mock())
            s.command = Mock(side_effect=[b'', RuntimeError('bad signature')])
            with self.assertRaisesRegex(RuntimeError, 'signature'):
                s.install()
            self.assertFalse((Path(folder) / 'Applications/Ollama.app').exists())
            self.assertIn('detach', cleanup.call_args.args[0])

    def test_cancelled_subprocess_is_reaped(self):
        s = LocalSetup(Mock())
        timer = threading.Timer(.1, s.cancelled.set)
        timer.start()
        import sys
        with self.assertRaises(Cancelled):
            s.command([sys.executable, '-c', 'import time; time.sleep(20)'])
        timer.join()


class SetupDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_progress_handles_multi_gigabyte_values(self):
        from ui.setup_dialog import SetupDialog
        d = SetupDialog()
        d.update_progress('다운로드', 3 * 1024**3, 4 * 1024**3)
        self.assertEqual(d.bar.value(), 75)
        self.assertIn('3.00 / 4.00 GB', d.status.text())
        d.close()

    def test_failure_reenables_retry_and_skip(self):
        from ui.setup_dialog import SetupDialog
        d = SetupDialog()
        d.start.setEnabled(False)
        d.skip.setEnabled(False)
        d.result_ready('연결 실패')
        d.finished_work()
        self.assertTrue(d.start.isEnabled())
        self.assertTrue(d.skip.isEnabled())
        self.assertEqual(d.status.text(), '연결 실패')
        d.close()

    def test_close_cancels_without_destroying_worker(self):
        from ui.setup_dialog import SetupDialog
        d = SetupDialog()
        worker = Mock()
        worker.cancelled = threading.Event()
        worker.isRunning.return_value = True
        d.worker = worker
        d.reject()
        self.assertTrue(worker.cancelled.is_set())
        self.assertFalse(d.cancel.isEnabled())
        d.worker = None
        d.close()


class MacOSVersionTests(unittest.TestCase):
    def test_supported_versions_including_27(self):
        from core.setup.local_setup import check_macos_support
        from unittest.mock import mock_open
        for value in ('14.0', '15.7', '26.1', '27.0.1'):
            with patch('builtins.open', mock_open()), patch('core.setup.local_setup.plistlib.load', return_value={'ProductVersion': value}):
                self.assertEqual(check_macos_support()[0], int(value.split('.')[0]))

    def test_real_old_version_explains_detected_version(self):
        from core.setup.local_setup import check_macos_support
        with patch('core.setup.local_setup.macos_version', return_value=(13, 7)):
            with self.assertRaisesRegex(RuntimeError, '현재 macOS 13.7'):
                check_macos_support()

    def test_unreadable_plist_falls_back_to_system_command(self):
        from core.setup.local_setup import macos_version
        with patch('builtins.open', side_effect=OSError), patch('core.setup.local_setup.subprocess.run', return_value=Mock(stdout='27.0.1\n')) as run:
            self.assertEqual(macos_version(), (27, 0, 1))
            self.assertEqual(run.call_args.kwargs['env']['SYSTEM_VERSION_COMPAT'], '0')

    def test_unknown_version_does_not_claim_old_os(self):
        from core.setup.local_setup import check_macos_support
        with patch('builtins.open', side_effect=OSError), patch('core.setup.local_setup.subprocess.run', return_value=Mock(stdout='')):
            with self.assertRaisesRegex(RuntimeError, '버전을 확인하지 못'):
                check_macos_support()
