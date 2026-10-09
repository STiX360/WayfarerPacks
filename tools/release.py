"""Deterministic production packaging and exact-artifact release helpers."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import tempfile
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe_name(name):
    path = PurePosixPath(name)
    if (not name or '\\' in name or ':' in name or path.is_absolute()
            or any(part in ('', '.', '..') for part in name.split('/'))
            or any(ord(c) < 32 for c in name)):
        raise ValueError(f'Unsafe relative file path: {name!r}')
    return name


def local_path(root, name):
    path = root / safe_name(name)
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f'File escapes project directory: {name}')
    return path


def inputs(root):
    config = json.loads((root / 'release/config.json').read_text(encoding='utf-8'))
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', config['slug']):
        raise ValueError('Invalid slug')
    if not isinstance(config['prerelease'], bool):
        raise ValueError('prerelease must be a boolean')
    version = local_path(root, config['version_file']).read_text(encoding='utf-8').strip()
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('Version must be X.Y.Z')
    mappings = config['files']
    if not isinstance(mappings, dict) or not mappings:
        raise ValueError('Explicit production file mappings are required')
    destinations = []
    for source, target in mappings.items():
        local_path(root, source)
        safe_name(target)
        destinations.append(target.casefold())
    if len(destinations) != len(set(destinations)):
        raise ValueError('Duplicate or case-colliding archive destinations')
    manifest = safe_name(config['content_manifest'])
    if manifest not in mappings.values() or not manifest.endswith('.omwscripts'):
        raise ValueError('Production content manifest must be allowlisted')
    return config, version


def notes(root, version):
    sections = []
    current = None
    fence = None
    for line in (root / 'CHANGELOG.md').read_text(encoding='utf-8').splitlines():
        stripped = line.strip()
        marker = re.match(r'^(`{3,}|~{3,})', stripped)
        if fence:
            if re.fullmatch(re.escape(fence[0]) + '{' + str(len(fence)) + ',}', stripped):
                fence = None
        elif marker:
            fence = marker.group(1)
        elif re.match(r'^##\s+', line):
            current = [] if stripped == f'## {version}' else None
            if current is not None:
                sections.append(current)
            continue
        if current is not None:
            current.append(line)
    if len(sections) != 1:
        raise ValueError(f'Need exactly one CHANGELOG section ## {version}')
    result = '\n'.join(sections[0]).strip()
    if not re.sub(r'<!--.*?-->', '', result, flags=re.DOTALL).strip():
        raise ValueError('Release notes must not be empty')
    return result


def paths(root, config, version):
    prefix = config.get('archive_prefix', config['slug'])
    if not re.fullmatch(r'[A-Za-z0-9_-]+', prefix):
        raise ValueError('Invalid archive prefix')
    archive = local_path(root, f"dist/{prefix}-{version}.zip")
    return archive, archive.with_suffix('.manifest.json'), archive.with_suffix('.zip.sha256')


def check_content(config, files):
    manifest = config['content_manifest']
    text = files[manifest].decode('utf-8-sig')
    referenced = []
    for line in text.splitlines():
        line = line.split('#', 1)[0].strip()
        if not line:
            continue
        match = re.fullmatch(r'(GLOBAL|PLAYER|LOCAL|CUSTOM)\s*:\s*(.+)', line)
        if not match:
            raise ValueError('Invalid .omwscripts declaration: ' + line)
        name = safe_name(match.group(2).strip())
        if name not in files:
            raise ValueError('Missing declared runtime script: ' + name)
        referenced.append(name)
    if not referenced:
        raise ValueError('Content manifest has no scripts')
    for name in config.get('content_files', [manifest]):
        if safe_name(name) not in files:
            raise ValueError('Missing enabled content file: ' + name)


def package(root=ROOT):
    config, version = inputs(root)
    notes(root, version)
    files = {target: local_path(root, source).read_bytes()
             for source, target in config['files'].items()}
    check_content(config, files)
    archive, manifest, checksum = paths(root, config, version)
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, 'w') as output:
        for name, data in sorted(files.items()):
            entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            entry.compress_type = zipfile.ZIP_DEFLATED
            output.writestr(entry, data)
    record = {'version': version, 'slug': config['slug'], 'profile': 'production',
              'files': {name: digest(data) for name, data in sorted(files.items())}}
    manifest.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8', newline='\n')
    checksum.write_text(''.join(f'{digest(p.read_bytes())}  {p.name}\n' for p in (archive, manifest)),
                        encoding='ascii', newline='\n')
    verify(root)
    return archive


def verify(root=ROOT, expected_sha=None):
    config, version = inputs(root)
    changelog = notes(root, version)
    archive, manifest, checksum = paths(root, config, version)
    hashes = {}
    for line in checksum.read_text(encoding='ascii').splitlines():
        match = re.fullmatch(r'([0-9a-f]{64})  (.+)', line)
        if not match or match[2] in hashes:
            raise ValueError('Malformed or duplicate checksum entry')
        hashes[match[2]] = match[1]
    if set(hashes) != {archive.name, manifest.name}:
        raise ValueError('Checksums must name exactly the ZIP and manifest')
    for path in (archive, manifest):
        if digest(path.read_bytes()) != hashes[path.name]:
            raise ValueError('Checksum mismatch: ' + path.name)
    if expected_sha is not None and hashes[archive.name] != expected_sha:
        raise ValueError('Archive differs from the verified build')
    record = json.loads(manifest.read_text(encoding='utf-8'))
    if (record['version'], record['slug'], record['profile']) != (version, config['slug'], 'production'):
        raise ValueError('Manifest release identity mismatch')
    if set(record['files']) != set(config['files'].values()):
        raise ValueError('Manifest differs from production allowlist')
    with zipfile.ZipFile(archive) as stream:
        names = stream.namelist()
        if len(names) != len(set(names)) or set(names) != set(record['files']):
            raise ValueError('ZIP entries differ from manifest')
        files = {}
        for name in names:
            safe_name(name)
            files[name] = stream.read(name)
            if digest(files[name]) != record['files'][name]:
                raise ValueError('Packaged file hash mismatch: ' + name)
        check_content(config, files)
    return {'version': version, 'filename': archive.name, 'sha256': hashes[archive.name],
            'name': config['name'], 'changelog': changelog, 'main_branch': config['main_branch']}


def identity(root, event, ref):
    config, version = inputs(root)
    if event == 'push':
        if ref != f'refs/tags/v{version}':
            raise ValueError('Tag must match VERSION')
    elif event != 'workflow_dispatch' or ref != f"refs/heads/{config['main_branch']}":
        raise ValueError('Manual builds must run from the configured main branch')
    return config, version


def outputs(values):
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8', newline='\n') as stream:
            for key, value in values.items():
                marker = 'output_' + uuid.uuid4().hex
                while marker in str(value).splitlines():
                    marker = 'output_' + uuid.uuid4().hex
                stream.write(f'{key}<<{marker}\n{value}\n{marker}\n')


def publish(root, event, ref, repository, expected_sha, run=subprocess.run):
    config, version = identity(root, event, ref)
    if event != 'push':
        raise ValueError('Manual dispatch never publishes')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository):
        raise ValueError('Invalid GitHub repository')
    metadata = verify(root, expected_sha)
    artifacts = paths(root, config, version)
    tag = f'v{version}'

    def gh(*args, check=True):
        return run(['gh', *args, '--repo', repository], check=check, capture_output=True, text=True)

    result = gh('release', 'view', tag, '--json', 'assets,isDraft,isPrerelease,tagName,url', check=False)
    if result.returncode:
        if 'release not found' not in result.stderr.lower() and 'HTTP 404' not in result.stderr:
            raise RuntimeError('Cannot inspect GitHub release: ' + result.stderr)
        text = (metadata['changelog'] + '\n\nDownload ' + metadata['filename']
                + ' under Assets. Requires OpenMW ' + config['engine_version']
                + '. Enable ' + ', then '.join(config.get('content_files', [config['content_manifest']])) + '.\n')
        with tempfile.TemporaryDirectory() as directory:
            note_file = Path(directory) / 'notes.md'
            note_file.write_text(text, encoding='utf-8')
            args = ['release', 'create', tag, *(str(p) for p in artifacts), '--verify-tag',
                    '--title', f"{config['name']} {version}", '--notes-file', str(note_file)]
            if config['prerelease']:
                args.extend(['--prerelease', '--latest=false'])
            gh(*args)
        return
    release = json.loads(result.stdout)
    if release['tagName'] != tag or release['isPrerelease'] != config['prerelease']:
        raise ValueError('Existing release status differs; inspect manually')
    existing = {asset['name'] for asset in release['assets']}
    # Check all existing companions before adding any missing asset.
    with tempfile.TemporaryDirectory() as directory:
        for artifact in artifacts:
            if artifact.name in existing:
                gh('release', 'download', tag, '--pattern', artifact.name, '--dir', directory)
                if (Path(directory) / artifact.name).read_bytes() != artifact.read_bytes():
                    raise ValueError('Existing release asset differs: ' + artifact.name)
    for artifact in artifacts:
        if artifact.name not in existing:
            gh('release', 'upload', tag, str(artifact))
    if release['isDraft']:
        gh('release', 'edit', tag, '--draft=false')


def nexus(root, expected_sha):
    metadata = verify(root, expected_sha)
    for key in ('NEXUSMODS_FILE_ID', 'NEXUSMODS_MOD_ID'):
        if not re.fullmatch(r'[1-9][0-9]*', os.environ.get(key, '')):
            raise ValueError('Configure ' + key + ' for this project')
    if not os.environ.get('NEXUSMODS_API_KEY', '').strip():
        raise ValueError('Configure NEXUSMODS_API_KEY secret')
    return metadata


def download(root, tag, repository, run=subprocess.run):
    config, version = identity(root, 'push', 'refs/tags/' + tag)
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository):
        raise ValueError('Invalid GitHub repository')
    result = run(['gh', 'release', 'view', tag, '--repo', repository, '--json',
                  'tagName,isDraft,isPrerelease'], check=True, capture_output=True, text=True)
    status = json.loads(result.stdout)
    if (status['tagName'] != tag or status['isDraft']
            or status['isPrerelease'] != config['prerelease']):
        raise ValueError('GitHub release identity/status differs; inspect manually')
    artifacts = paths(root, config, version)
    artifacts[0].parent.mkdir(parents=True, exist_ok=True)
    for artifact in artifacts:
        run(['gh', 'release', 'download', tag, '--repo', repository, '--pattern',
             artifact.name, '--dir', str(artifact.parent)], check=True,
            capture_output=True, text=True)
    return verify(root)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['package', 'verify', 'identity', 'metadata', 'publish',
                                          'nexus', 'download', 'nexus-manual'])
    args = parser.parse_args()
    if args.command == 'package':
        print(package())
    elif args.command == 'verify':
        print('Verified:', verify()['filename'])
    elif args.command == 'identity':
        config, version = identity(ROOT, os.environ['GITHUB_EVENT_NAME'], os.environ['GITHUB_REF'])
        outputs({'main_branch': config['main_branch'], 'version': version})
    elif args.command == 'metadata':
        identity(ROOT, os.environ['GITHUB_EVENT_NAME'], os.environ['GITHUB_REF'])
        outputs(verify())
    elif args.command == 'publish':
        publish(ROOT, os.environ['GITHUB_EVENT_NAME'], os.environ['GITHUB_REF'],
                os.environ['GITHUB_REPOSITORY'], os.environ['ZIP_SHA256'])
    elif args.command == 'download':
        identity(ROOT, os.environ['GITHUB_EVENT_NAME'], os.environ['GITHUB_REF'])
        if os.environ['GITHUB_EVENT_NAME'] != 'workflow_dispatch':
            raise ValueError('Existing-release downloads require manual dispatch')
        download(ROOT, os.environ['RELEASE_TAG'], os.environ['REPOSITORY'])
    elif args.command == 'nexus-manual':
        identity(ROOT, os.environ['GITHUB_EVENT_NAME'], os.environ['GITHUB_REF'])
        if os.environ['GITHUB_EVENT_NAME'] != 'workflow_dispatch':
            raise ValueError('Manual Nexus upload requires manual dispatch')
        metadata = verify(ROOT)
        outputs(nexus(ROOT, metadata['sha256']))
    else:
        identity(ROOT, os.environ['GITHUB_EVENT_NAME'], os.environ['GITHUB_REF'])
        if os.environ['GITHUB_EVENT_NAME'] != 'push':
            raise ValueError('Manual dispatch never uploads')
        nexus(ROOT, os.environ['ZIP_SHA256'])
        print('Nexus configuration and archive verified; no credentials logged.')


if __name__ == '__main__':
    main()
