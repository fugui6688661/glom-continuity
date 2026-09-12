#!/usr/bin/env python3
"""Build a local candidate from an explicit allowlist; does not publish or install."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import zipfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    paths = json.loads((root / 'release-files.json').read_text(encoding='utf-8'))
    if not isinstance(paths, list) or not paths or len(paths) != len(set(paths)):
        parser.error('Invalid or duplicate release allowlist')
    files = {}
    for name in paths:
        relative = PurePosixPath(name)
        if relative.is_absolute() or '..' in relative.parts or '\\' in name:
            parser.error('Unsafe allowlist path')
        current = root
        for part in relative.parts:
            current = current / part
            if current.is_symlink():
                parser.error('Release symlinks are not allowed')
        if not current.is_file() or current.stat().st_size > 1024 * 1024:
            parser.error('Release input missing or unexpectedly large: ' + name)
        content = current.read_bytes()
        text = content.decode('utf-8')
        # A targeted privacy preflight, not an exhaustive secret scanner.
        if re.search(r'/Users/[A-Za-z0-9_.-]+/|[A-Z]:\\Users\\[A-Za-z0-9_.-]+\\', text):
            parser.error('Personal absolute path found; sanitize before packaging: ' + name)
        files[name] = content
    manifest = {'format': 'continuity-package-v1', 'published': False,
                'files': [{'path': name, 'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest()}
                          for name, content in sorted(files.items())]}
    files['PACKAGE-MANIFEST.json'] = (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode()
    # Exclusive creation: rebuilding never silently overwrites a prior candidate.
    with zipfile.ZipFile(args.output, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, content in sorted(files.items()):
            info = zipfile.ZipInfo('glom-continuity/' + name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, content)
    print(json.dumps({'path': str(args.output), 'files': len(files),
                      'bytes': args.output.stat().st_size,
                      'sha256': hashlib.sha256(args.output.read_bytes()).hexdigest(),
                      'published': False}))


if __name__ == '__main__':
    main()
