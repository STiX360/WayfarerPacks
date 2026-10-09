import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import release


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = json.loads((ROOT / 'release/config.json').read_text(encoding='utf-8'))
        for name in ('release/config.json', 'CHANGELOG.md', self.config['version_file'], *self.config['files']):
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        self.version = (self.root / self.config['version_file']).read_text().strip()

    def write_config(self):
        (self.root / 'release/config.json').write_text(json.dumps(self.config), encoding='utf-8')

    def test_deterministic_install_paths_and_no_test_files(self):
        archive = release.package(self.root)
        original = archive.read_bytes()
        release.package(self.root)
        self.assertEqual(original, archive.read_bytes())
        with zipfile.ZipFile(archive) as stream:
            self.assertEqual(set(self.config['files'].values()), set(stream.namelist()))
            self.assertIn(self.config['content_manifest'], stream.namelist())
            self.assertFalse(any(name.startswith(('tests/', '.runtime/')) for name in stream.namelist()))

    def test_version_tag_and_manual_dispatch_boundaries(self):
        release.identity(self.root, 'push', f'refs/tags/v{self.version}')
        release.identity(self.root, 'workflow_dispatch', f"refs/heads/{self.config['main_branch']}")
        for event, ref in [('push', 'refs/tags/v999.0.0'), ('push', 'refs/heads/main'),
                           ('workflow_dispatch', 'refs/heads/feature'), ('pull_request', 'refs/pull/1')]:
            with self.assertRaises(ValueError):
                release.identity(self.root, event, ref)

    def test_tampered_archive_and_wrong_expected_hash_fail(self):
        archive = release.package(self.root)
        with self.assertRaises(ValueError):
            release.verify(self.root, '0' * 64)
        archive.write_bytes(archive.read_bytes() + b'changed')
        with self.assertRaises(ValueError):
            release.verify(self.root)

    def test_missing_runtime_script_fails(self):
        source = next(k for k, v in self.config['files'].items() if v == self.config['content_manifest'])
        (self.root / source).write_text('PLAYER: scripts/missing.lua\n', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Missing declared'):
            release.package(self.root)

    def test_unsafe_paths_and_case_collisions_fail(self):
        for name in ('../escape.lua', '/absolute.lua', 'C:/outside.lua', 'scripts\\bad.lua', 'a//b'):
            with self.assertRaises(ValueError):
                release.safe_name(name)
        first = next(iter(self.config['files'].values()))
        self.config['files']['extra.lua'] = first.upper()
        self.write_config()
        with self.assertRaisesRegex(ValueError, 'case-colliding'):
            release.inputs(self.root)

    def test_missing_production_file_fails(self):
        (self.root / next(iter(self.config['files']))).unlink()
        with self.assertRaises(FileNotFoundError):
            release.package(self.root)

    def test_changelog_duplicate_empty_and_fenced_headings(self):
        changelog = self.root / 'CHANGELOG.md'
        for text in (f'## {self.version}\n\n', f'## {self.version}\n<!-- pending -->\n',
                     f'## {self.version}\nOne\n## {self.version}\nTwo\n'):
            changelog.write_text(text, encoding='utf-8')
            with self.assertRaises(ValueError):
                release.notes(self.root, self.version)
        changelog.write_text(f'## {self.version}\nNotes\n```\n## {self.version}\n```\n', encoding='utf-8')
        self.assertIn('Notes', release.notes(self.root, self.version))

    def test_manual_publish_rejected_without_network(self):
        with self.assertRaises(ValueError):
            release.publish(self.root, 'workflow_dispatch', 'refs/heads/main', 'owner/repo', '',
                            run=lambda *a, **k: self.fail('Unexpected network operation'))

    def test_github_create_uses_verified_tag_and_explicit_status(self):
        release.package(self.root)
        metadata = release.verify(self.root)
        calls = []

        def run(args, **kwargs):
            calls.append(args)
            if args[1:3] == ['release', 'view']:
                return subprocess.CompletedProcess(args, 1, '', 'release not found')
            self.assertIn('--verify-tag', args)
            self.assertEqual('--prerelease' in args, self.config['prerelease'])
            note_file = Path(args[args.index('--notes-file') + 1])
            self.assertIn(metadata['changelog'], note_file.read_text(encoding='utf-8'))
            return subprocess.CompletedProcess(args, 0, '', '')

        release.publish(self.root, 'push', f'refs/tags/v{self.version}', 'owner/repo', metadata['sha256'], run)
        self.assertEqual(len(calls), 2)

    def test_conflicting_existing_asset_never_overwritten(self):
        archive = release.package(self.root)
        calls = []

        def run(args, **kwargs):
            calls.append(args)
            if args[1:3] == ['release', 'view']:
                value = {'tagName': f'v{self.version}', 'isPrerelease': self.config['prerelease'],
                         'isDraft': False, 'assets': [{'name': archive.name}]}
                return subprocess.CompletedProcess(args, 0, json.dumps(value), '')
            if args[1:3] == ['release', 'download']:
                (Path(args[args.index('--dir') + 1]) / archive.name).write_bytes(b'other build')
                return subprocess.CompletedProcess(args, 0, '', '')
            self.fail('Unexpected mutation: ' + str(args))

        with self.assertRaisesRegex(ValueError, 'Existing release asset differs'):
            release.publish(self.root, 'push', f'refs/tags/v{self.version}', 'owner/repo',
                            release.verify(self.root)['sha256'], run)

    def test_matching_existing_release_is_a_noop(self):
        release.package(self.root)
        artifacts = release.paths(self.root, self.config, self.version)

        def run(args, **kwargs):
            if args[1:3] == ['release', 'view']:
                value = {'tagName': f'v{self.version}', 'isPrerelease': self.config['prerelease'],
                         'isDraft': False, 'assets': [{'name': p.name} for p in artifacts]}
                return subprocess.CompletedProcess(args, 0, json.dumps(value), '')
            if args[1:3] == ['release', 'download']:
                name = args[args.index('--pattern') + 1]
                shutil.copyfile(self.root / 'dist' / name, Path(args[args.index('--dir') + 1]) / name)
                return subprocess.CompletedProcess(args, 0, '', '')
            self.fail('Unexpected mutation: ' + str(args))

        release.publish(self.root, 'push', f'refs/tags/v{self.version}', 'owner/repo',
                        release.verify(self.root)['sha256'], run)

    def test_nexus_requires_project_configuration(self):
        release.package(self.root)
        checksum = release.verify(self.root)['sha256']
        with patch.dict('os.environ', {}, clear=True), self.assertRaises(ValueError):
            release.nexus(self.root, checksum)
        with patch.dict('os.environ', {'NEXUSMODS_FILE_ID': '123', 'NEXUSMODS_MOD_ID': '456',
                                      'NEXUSMODS_API_KEY': 'fixture-only'}):
            self.assertEqual(release.nexus(self.root, checksum)['version'], self.version)

    def test_existing_release_download_uses_exact_companions(self):
        release.package(self.root)
        artifacts = release.paths(self.root, self.config, self.version)
        originals = {p.name: p.read_bytes() for p in artifacts}
        for artifact in artifacts:
            artifact.unlink()

        def run(args, **kwargs):
            if args[1:3] == ['release', 'view']:
                status = {'tagName': f'v{self.version}', 'isDraft': False,
                          'isPrerelease': self.config['prerelease']}
                return subprocess.CompletedProcess(args, 0, json.dumps(status), '')
            self.assertEqual(args[1:3], ['release', 'download'])
            name = args[args.index('--pattern') + 1]
            (Path(args[args.index('--dir') + 1]) / name).write_bytes(originals[name])
            return subprocess.CompletedProcess(args, 0, '', '')

        result = release.download(self.root, f'v{self.version}', 'owner/repo', run)
        self.assertEqual(result['filename'], artifacts[0].name)

    def test_download_rejects_mismatched_tags_and_drafts(self):
        with self.assertRaises(ValueError):
            release.download(self.root, 'v999.0.0', 'owner/repo',
                             lambda *a, **k: self.fail('Unexpected network operation'))

        def run(args, **kwargs):
            self.assertEqual(args[1:3], ['release', 'view'])
            status = {'tagName': f'v{self.version}', 'isDraft': True,
                      'isPrerelease': self.config['prerelease']}
            return subprocess.CompletedProcess(args, 0, json.dumps(status), '')

        with self.assertRaisesRegex(ValueError, 'identity/status'):
            release.download(self.root, f'v{self.version}', 'owner/repo', run)

    def test_enabled_plugin_must_be_packaged(self):
        self.config['files'].pop('Wayfarer Packs/WayfarerPacks.esp')
        self.write_config()
        with self.assertRaisesRegex(ValueError, 'Missing enabled content file'):
            release.package(self.root)

    def test_wayfarer_allowlist_and_version_metadata(self):
        production = {p.relative_to(ROOT).as_posix()
                      for p in (ROOT / 'Wayfarer Packs').rglob('*') if p.is_file()}
        self.assertEqual(production, set(self.config['files']))
        self.assertEqual(self.config['archive_prefix'], 'WayfarerPacks')
        self.assertEqual((ROOT / 'Wayfarer Packs/README.md').read_text(encoding='utf-8').splitlines()[0],
                         '# Wayfarer Packs ' + self.version)
        self.assertEqual(self.config['content_files'],
                         ['WayfarerPacks.esp', 'WayfarerPacks.omwscripts'])
