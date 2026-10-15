"""Build the native, separately launchable Myorii removal tool."""
from pathlib import Path
import platform
import plistlib
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def build():
    app = ROOT / 'dist/묘리 제거.app'
    if app.exists():
        shutil.rmtree(app)
    contents = app / 'Contents'
    (contents / 'MacOS').mkdir(parents=True)
    (contents / 'Resources').mkdir()
    executable = contents / 'MacOS/MyoriiUninstaller'
    subprocess.run([
        'swiftc', '-O', '-module-cache-path', str(ROOT / 'build/swift-module-cache'), '-target', f'{platform.machine()}-apple-macos14.0',
        '-framework', 'AppKit', '-framework', 'Security',
        str(ROOT / 'packaging/macos/uninstaller/Removal.swift'),
        str(ROOT / 'packaging/macos/uninstaller/main.swift'), '-o', str(executable),
    ], check=True)
    shutil.copyfile(ROOT / 'build/Myorii.icns', contents / 'Resources/Myorii.icns')
    with (contents / 'Info.plist').open('wb') as stream:
        plistlib.dump({
            'CFBundleIdentifier': 'app.myorii.uninstaller',
            'CFBundleName': '묘리 제거', 'CFBundleDisplayName': '묘리 제거',
            'CFBundleExecutable': 'MyoriiUninstaller', 'CFBundlePackageType': 'APPL',
            'CFBundleIconFile': 'Myorii.icns',
            'CFBundleShortVersionString': '1.0.0', 'CFBundleVersion': '2',
            'LSMinimumSystemVersion': '14.0', 'NSHighResolutionCapable': True,
        }, stream)
    subprocess.run(['codesign', '--force', '--sign', '-', str(app)], check=True)
    subprocess.run(['codesign', '--verify', '--deep', '--strict', str(app)], check=True)
    subprocess.run([str(executable), '--check-package'], check=True)
    return app


if __name__ == '__main__':
    print(build())
