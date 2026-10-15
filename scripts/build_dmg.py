"""Build an architecture-specific, ad-hoc signed test DMG on macOS."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def run(*args):
    subprocess.run(args, check=True, cwd=ROOT)


def main():
    iconset = ROOT / 'build/Myorii.iconset'
    iconset.mkdir(parents=True, exist_ok=True)
    # Preserve existing artwork; only resize for native icon representations.
    for size in (16, 32, 128, 256, 512):
        for scale in (1, 2):
            name = f'icon_{size}x{size}' + ('@2x' if scale == 2 else '') + '.png'
            run('sips', '-z', str(size * scale), str(size * scale),
                str(ROOT / 'assets/characters/myorii_profile.png'), '--out', str(iconset / name))
    run('iconutil', '-c', 'icns', str(iconset), '-o', str(ROOT / 'build/Myorii.icns'))
    run(sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', 'packaging/macos/Myorii.spec')
    app = ROOT / 'dist/Myorii.app'
    run('codesign', '--verify', '--deep', '--strict', str(app))
    # Exercise OS detection inside the frozen app, not the development Python.
    report = json.loads(subprocess.check_output(
        [str(app / 'Contents/MacOS/Myorii'), '--check-install-environment'], text=True))
    actual = subprocess.check_output(['/usr/bin/sw_vers', '-productVersion'], text=True).strip()
    if report['macos'] != actual or not report['local_install_supported']:
        raise RuntimeError(f'Frozen app OS detection failed: {report}, actual={actual}')
    print('Frozen app installation environment:', report)
    arch = subprocess.check_output(['uname', '-m'], text=True).strip()
    dmg = ROOT / f'dist/Myorii-macOS-{arch}.dmg'
    with tempfile.TemporaryDirectory(prefix='myorii-dmg-') as folder:
        stage = Path(folder)
        run('ditto', str(app), str(stage / app.name))
        (stage / 'Applications').symlink_to('/Applications')
        shutil.copyfile(ROOT / 'output/pdf/Myorii-install-guide.pdf', stage / '설치 안내.pdf')
        run('hdiutil', 'create', '-volname', 'Myorii', '-srcfolder', str(stage),
            '-ov', '-format', 'UDZO', str(dmg))
    run('hdiutil', 'verify', str(dmg))
    digest = hashlib.file_digest(dmg.open('rb'), 'sha256').hexdigest()
    dmg.with_suffix('.dmg.sha256').write_text(f'{digest}  {dmg.name}\n')
    print(dmg)


if __name__ == '__main__':
    main()
