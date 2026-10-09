"""Run an isolated OpenMW smoke test without modifying the installed modlist."""
from pathlib import Path
import argparse
import shutil
import subprocess
from build_wayfarer_packs import ROOT, MOD


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--engine-root', required=True, type=Path)
    parser.add_argument('--game-data', required=True, type=Path)
    args = parser.parse_args()
    output = ROOT / 'reports/wayfarer-engine-check'
    output.mkdir(parents=True, exist_ok=True)
    fixture = ROOT / 'tests/wayfarer_engine'
    shutil.copyfile(fixture / 'settings.cfg', output / 'settings.cfg')
    command = [str(args.engine_root / 'openmw.exe'),
               '--replace', 'config', '--config', str(output),
               '--replace', 'data', '--data', str(args.engine_root / 'resources/vfs-mw'),
               str(args.game_data), str(MOD), str(fixture),
               '--data-local', str(fixture), '--replace', 'content', '--content',
               'Morrowind.esm', 'Tribunal.esm', 'Bloodmoon.esm',
               'WayfarerPacks.esp', 'WayfarerPacks.omwscripts', 'Smoke.omwscripts',
               '--replace', 'fallback-archive', '--fallback-archive',
               'Morrowind.bsa', 'Tribunal.bsa', 'Bloodmoon.bsa',
               '--user-data', str(output), '--resources', str(args.engine_root / 'resources'),
               '--skip-menu', '--new-game=0', '--start', "Seyda Neen, Arrille's Tradehouse",
               '--no-sound', '--no-grab']
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    result = subprocess.run(command, capture_output=True, text=True,
                            cwd=args.engine_root, startupinfo=startup, timeout=60)
    log = result.stdout + result.stderr
    (output / 'result.txt').write_text(log)
    messages = []
    for line in log.splitlines():
        if 'WFP_SMOKE' in line or ' E]' in line or 'Failed' in line or 'Error' in line:
            if line not in messages:
                messages.append(line)
    print('\n'.join(messages[:30]))
    if result.returncode or 'WFP_SMOKE_PASS' not in log or 'WFP_SMOKE_FAIL' in log:
        raise SystemExit('OpenMW smoke test failed; see '+str(output / 'result.txt'))
    if any(phrase in log for phrase in (' E]', 'Lua error', 'Failed to load', 'Error in Lua', 'No data loaded')):
        raise SystemExit('OpenMW reported a resource/script error; inspect the saved log')
    print('Verified: real engine equipment, switching, Feather, toggle, and lost-item cleanup.')
    print(output / 'result.txt')


if __name__ == '__main__':
    main()
