"""Cancellable local runtime preparation. No GUI or database dependencies."""
import json
import ssl
import certifi
from pathlib import Path
import os
import plistlib
import re
import shutil
import subprocess
import tempfile
import threading
import time
from urllib.request import Request, urlopen

DEFAULT_MODEL = 'qwen3-vl:4b-instruct'
OLLAMA_URL = 'https://ollama.com/download/Ollama.dmg'
OLLAMA_REQUIREMENT = '=anchor apple generic and certificate leaf[subject.OU] = "3MU9H2V9Y9"'


def macos_version():
    """Read the product version explicitly so PyInstaller collects plistlib.

    The project's dynamically loaded stdlib platform module can hide imports
    from the freezer. Never interpret a failed version lookup as macOS 0.
    """
    def parse(value):
        if isinstance(value, str) and re.fullmatch(r"[0-9]+(?:\.[0-9]+){0,2}", value.strip()):
            return tuple(int(part) for part in value.strip().split('.'))
        return None

    try:
        with open('/System/Library/CoreServices/SystemVersion.plist', 'rb') as source:
            version = parse(plistlib.load(source).get('ProductVersion'))
            if version:
                return version
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    try:
        result = subprocess.run(['/usr/bin/sw_vers', '-productVersion'], capture_output=True,
                                text=True, check=True, timeout=5,
                                env={**os.environ, 'SYSTEM_VERSION_COMPAT': '0'})
        version = parse(result.stdout)
        if version:
            return version
    except (OSError, subprocess.SubprocessError):
        pass
    raise RuntimeError('macOS 버전을 확인하지 못했습니다. 앱을 다시 실행하고 재시도해주세요.')


def check_macos_support():
    version = macos_version()
    if version[0] < 14:
        label = '.'.join(map(str, version))
        raise RuntimeError(f'현재 macOS {label}입니다. 로컬 모델 설치에는 macOS 14 이상이 필요합니다. API 모드를 이용할 수 있습니다.')
    return version


class Cancelled(Exception):
    pass


class LocalSetup:
    def __init__(self, progress, cancelled=None, model=DEFAULT_MODEL):
        self.progress = progress
        self.cancelled = cancelled or threading.Event()
        self.model = model
        self.base = 'http://127.0.0.1:11434'

    def check(self):
        if self.cancelled.is_set():
            raise Cancelled()

    def api(self, path, data=None, timeout=5):
        request = Request(self.base + path, data=json.dumps(data).encode() if data is not None else None,
                          headers={'Content-Type': 'application/json'})
        with urlopen(request, timeout=timeout) as response:
            return json.load(response)

    def available(self):
        try:
            return self.api('/api/tags').get('models', [])
        except (OSError, ValueError):
            return None

    def has_model(self, models):
        return any(item.get('name') == self.model for item in models or [])

    def command(self, args):
        # Bound every subprocess; cancellation never leaves a child running.
        with subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
            try:
                deadline = time.monotonic() + 180
                while True:
                    self.check()
                    try:
                        out, err = process.communicate(timeout=.2)
                        break
                    except subprocess.TimeoutExpired:
                        if time.monotonic() > deadline:
                            raise RuntimeError('설치 작업 시간이 초과되었습니다. 다시 시도해주세요.')
                if process.returncode:
                    raise RuntimeError(err.decode(errors='replace')[-500:] or '설치 작업에 실패했습니다.')
                return out
            except BaseException:
                process.kill()
                process.communicate()
                raise

    def installed_app(self):
        for path in (Path('/Applications/Ollama.app'), Path.home() / 'Applications/Ollama.app'):
            if (path / 'Contents/Resources/ollama').is_file():
                return path
        return None

    def install(self):
        check_macos_support()
        destination = Path.home() / 'Applications/Ollama.app'
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise RuntimeError('기존 Ollama 앱을 확인해주세요. 기존 설치를 덮어쓰지 않았습니다.')
        if shutil.disk_usage(destination.parent).free < 6 * 1024**3:
            raise RuntimeError('Ollama 설치를 위해 여유 공간 6GB 이상이 필요합니다.')
        with tempfile.TemporaryDirectory(prefix='myorii-ollama-') as folder:
            folder = Path(folder)
            dmg, mount = folder / 'Ollama.dmg', folder / 'mount'
            self.progress('Ollama 다운로드 중', 0, 0)
            with urlopen(OLLAMA_URL, timeout=15, context=ssl.create_default_context(cafile=certifi.where())) as response, dmg.open('wb') as output:
                total = int(response.headers.get('Content-Length', 0))
                completed = 0
                while True:
                    self.check()
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    output.write(chunk)
                    completed += len(chunk)
                    self.progress('Ollama 다운로드 중', completed, total)
                if total and completed != total:
                    raise RuntimeError('다운로드가 중단되었습니다. 다시 시도해주세요.')
            mount.mkdir()
            try:
                self.progress('Ollama 설치 확인 중', 0, 0)
                self.command(['/usr/bin/hdiutil', 'attach', str(dmg), '-readonly', '-nobrowse', '-mountpoint', str(mount)])
                source = mount / 'Ollama.app'
                self.command(['/usr/bin/codesign', '--verify', '--deep', '--strict', '-R', OLLAMA_REQUIREMENT, str(source)])
                # Copy to a staging directory on the destination volume, then rename atomically.
                with tempfile.TemporaryDirectory(prefix='.myorii-', dir=destination.parent) as stage:
                    candidate = Path(stage) / 'Ollama.app'
                    self.command(['/usr/bin/ditto', str(source), str(candidate)])
                    self.check()
                    if destination.exists():
                        raise RuntimeError('Ollama가 다른 작업에서 설치되었습니다. 다시 시도해주세요.')
                    candidate.rename(destination)
            finally:
                subprocess.run(['/usr/bin/hdiutil', 'detach', str(mount)], capture_output=True, timeout=30)
        return destination

    def start_server(self):
        app = self.installed_app()
        binary = shutil.which('ollama')
        if not app and not binary:
            app = self.install()
        self.check()
        self.progress('Ollama 실행 중 · 권한 창이 나타나면 확인해주세요', 0, 0)
        if app:
            self.command(['/usr/bin/open', '-g', str(app)])
        else:
            # CLI-only installations have no GUI app to launch.
            subprocess.Popen([binary, 'serve'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             start_new_session=True)
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            self.check()
            if self.available() is not None:
                return
            self.cancelled.wait(.5)
        raise RuntimeError('Ollama가 응답하지 않습니다. macOS 실행 허용 창이나 Ollama 앱을 확인하고 재시도해주세요.')

    def pull(self):
        if shutil.disk_usage(Path.home()).free < 5 * 1024**3:
            raise RuntimeError('모델 준비를 위해 여유 공간 5GB 이상이 필요합니다.')
        request = Request(self.base + '/api/pull', data=json.dumps({'model': self.model, 'stream': True}).encode(),
                          headers={'Content-Type': 'application/json'})
        succeeded = False
        with urlopen(request, timeout=30) as response:
            for line in response:
                self.check()
                event = json.loads(line)
                if event.get('error'):
                    raise RuntimeError(event['error'])
                self.progress('Qwen 모델 다운로드 중', event.get('completed', 0), event.get('total', 0))
                if event.get('status') == 'success':
                    succeeded = True
        if not succeeded:
            raise RuntimeError('모델 다운로드가 중단되었습니다. 다시 시도하면 받은 부분을 재사용합니다.')

    def run(self):
        self.check()
        self.progress('Ollama와 모델 확인 중', 0, 0)
        models = self.available()
        if models is None:
            self.start_server()
            models = self.available()
        self.check()
        if not self.has_model(models):
            self.pull()
        self.check()
        if not self.has_model(self.available()):
            raise RuntimeError('다운로드한 모델을 찾지 못했습니다. 다시 시도해주세요.')
        self.progress('모델 실행 확인 중 · 처음에는 잠시 걸릴 수 있어요', 0, 0)
        result = self.api('/api/generate', {'model': self.model, 'prompt': '', 'stream': False, 'keep_alive': '30m'}, timeout=120)
        self.check()
        if result.get('error') or not result.get('done'):
            raise RuntimeError('모델을 실행하지 못했습니다. 메모리 여유 공간을 확인해주세요.')
        self.progress('준비가 완료되었습니다', 1, 1)
