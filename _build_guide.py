"""Build-time only: copy canonical documentation, never a second editable source."""
import ast
import hashlib
import json
from pathlib import Path, PurePosixPath

from setuptools.command.build_py import build_py


class BuildWithGuide(build_py):
    def guide_mapping(self):
        root = Path(__file__).resolve().parent
        names = json.loads((root / 'guide-files.json').read_text(encoding='utf-8'))
        if not isinstance(names, list) or not names or len(names) != len(set(names)):
            raise ValueError('Invalid guide allowlist')
        mapping = {}
        for name in names:
            relative = PurePosixPath(name)
            if relative.is_absolute() or '..' in relative.parts or '\\' in name:
                raise ValueError('Unsafe guide path')
            source = root
            for part in relative.parts:
                source = source / part
                if source.is_symlink():
                    raise ValueError('Guide symlinks are not allowed')
            if not source.is_file() or source.stat().st_size > 1024 * 1024:
                raise ValueError('Guide source missing or too large: ' + name)
            destination = Path(self.build_lib) / 'glom_continuity' / '_guide' / name
            mapping[str(destination)] = str(source)
        return mapping

    def run(self):
        super().run()
        guide = Path(self.build_lib) / 'glom_continuity' / '_guide'
        if guide.exists() or guide.is_symlink():
            if guide.is_symlink() or guide.parent.is_symlink() or not guide.is_dir():
                raise ValueError('Unsafe previous guide output; use a fresh build directory')
            manifest_path = guide / 'GUIDE-MANIFEST.json'
            if manifest_path.is_symlink() or not manifest_path.is_file():
                raise ValueError('Unowned previous guide output; use a fresh build directory')
            previous = json.loads(manifest_path.read_text(encoding='utf-8'))
            if previous.get('format') != 'recaloom-guide-v1':
                raise ValueError('Unknown previous guide output; preserve it and use a fresh build directory')
            owned = {item['path']: item['sha256'] for item in previous['files']}
            removable = []
            for path in guide.rglob('*'):
                if path.is_symlink():
                    raise ValueError('Unexpected guide symlink; preserve it and use a fresh build directory')
                if path.is_dir() or path == manifest_path:
                    continue
                name = path.relative_to(guide).as_posix()
                if (not path.is_file() or name not in owned
                        or hashlib.sha256(path.read_bytes()).hexdigest() != owned[name]):
                    raise ValueError('Changed or unowned guide output; preserve it and use a fresh build directory')
                removable.append(path)
            # Delete only verified build-generated files, never the source or an unknown tree.
            for path in removable:
                path.unlink()
            manifest_path.unlink()
        for destination, source in self.guide_mapping().items():
            self.mkpath(str(Path(destination).parent))
            self.copy_file(source, destination)
        root = Path(__file__).resolve().parent
        program = (root / 'scripts/continuity.py').read_bytes()
        version = next(ast.literal_eval(node.value) for node in ast.parse(program).body
                       if isinstance(node, ast.Assign)
                       and any(isinstance(t, ast.Name) and t.id == 'VERSION' for t in node.targets))
        files = []
        for source in self.guide_mapping().values():
            content = Path(source).read_bytes()
            files.append({'path': Path(source).relative_to(root).as_posix(), 'bytes': len(content),
                          'sha256': hashlib.sha256(content).hexdigest()})
        manifest = {'format': 'recaloom-guide-v1', 'tool_version': version,
                    'program_sha256': hashlib.sha256(program).hexdigest(), 'files': files}
        (Path(self.build_lib) / 'glom_continuity/_guide/GUIDE-MANIFEST.json').write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    def get_source_files(self):
        root = Path(__file__).resolve().parent
        inputs = [str(Path(p).relative_to(root)) for p in self.guide_mapping().values()]
        return super().get_source_files() + ['_build_guide.py', 'guide-files.json'] + inputs

    def get_outputs(self, include_bytecode=1):
        return (super().get_outputs(include_bytecode) + list(self.guide_mapping())
                + [str(Path(self.build_lib) / 'glom_continuity/_guide/GUIDE-MANIFEST.json')])

    def get_output_mapping(self):
        return {**super().get_output_mapping(), **self.guide_mapping()}
