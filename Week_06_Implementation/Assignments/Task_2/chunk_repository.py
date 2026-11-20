"""Split Python repository files into lossless, line-based chunks (stdlib only)."""

import argparse
import json
import os
from pathlib import Path
import sys
import tokenize


EXCLUDED_DIRECTORIES = {
    '.git', '.hg', '.svn', '__pycache__', '.pytest_cache', '.mypy_cache',
    '.ruff_cache', '.tox', '.nox', '.venv', 'venv', 'env', 'node_modules',
    'site-packages', 'build', 'dist', '.eggs',
}


def split_lines(lines, max_lines):
    """Yield contiguous ranges, preferring nearby blank-line boundaries."""
    start = 0
    while start < len(lines):
        end = min(start + max_lines, len(lines))
        if end < len(lines):
            # Keep reasonably sized chunks while avoiding many mid-block cuts.
            for boundary in range(end, start + max_lines // 2, -1):
                if not lines[boundary - 1].strip():
                    end = boundary
                    break
        yield start, end
        start = end


def chunk_repository(repository, max_lines, output):
    chunks = []
    processed_files = []
    skipped_files = []

    def walk_error(error):
        skipped_files.append({'path': str(error.filename), 'reason': str(error)})

    for directory, directories, filenames in os.walk(repository, onerror=walk_error):
        directories[:] = sorted(
            name for name in directories
            if name not in EXCLUDED_DIRECTORIES
            and not name.endswith('.egg-info')
            and not (Path(directory) / name).is_symlink()
        )
        for filename in sorted(filenames):
            path = Path(directory) / filename
            relative_path = path.relative_to(repository).as_posix()
            if path.suffix.lower() != '.py':
                skipped_files.append({'path': relative_path, 'reason': 'unsupported file type'})
                continue
            if path.is_symlink() or path.resolve() == output:
                skipped_files.append({'path': relative_path, 'reason': 'symlink or output file'})
                continue
            try:
                # Honour Python encoding declarations and UTF-8 BOMs. Newlines
                # are normalised to LF by the text reader for portable retrieval.
                with tokenize.open(path) as source:
                    content = source.read()
                if '\x00' in content:
                    raise ValueError('binary content (NUL byte)')
            except (OSError, UnicodeError, SyntaxError, LookupError, ValueError) as error:
                skipped_files.append({'path': relative_path, 'reason': str(error)})
                continue
            lines = content.splitlines(keepends=True)
            if not lines:
                skipped_files.append({'path': relative_path, 'reason': 'empty file'})
                continue
            file_chunks = []
            for index, (start, end) in enumerate(split_lines(lines, max_lines), 1):
                file_chunks.append({
                    'chunk_id': f'{relative_path}::{index}',
                    'relative_path': relative_path,
                    'language': 'python',
                    'start_line': start + 1,
                    'end_line': end,
                    'content': ''.join(lines[start:end]),
                })
            # Check exact reconstruction before recording each file.
            if ''.join(chunk['content'] for chunk in file_chunks) != content:
                raise RuntimeError(f'Chunk reconstruction failed: {relative_path}')
            chunks.extend(file_chunks)
            processed_files.append(relative_path)
    return {
        'schema_version': 1,
        'repository': repository.name,
        'settings': {'max_lines': max_lines, 'overlap_lines': 0,
                     'file_types': ['.py'], 'newline_policy': 'normalise to LF'},
        'summary': {'processed_files': len(processed_files), 'chunks': len(chunks)},
        'processed_files': processed_files,
        'skipped_files': skipped_files,
        'chunks': chunks,
    }


def main():
    task_directory = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path,
                        default=task_directory.parent / 'Task_1' / 'AI4SE_Playground')
    parser.add_argument('--output', type=Path, default=task_directory / 'chunks.json')
    parser.add_argument('--max-lines', type=int, default=80)
    arguments = parser.parse_args()
    repository = arguments.repo.resolve()
    output = arguments.output.resolve()
    if not repository.is_dir():
        parser.error(f'Repository directory does not exist: {repository}')
    if arguments.max_lines < 2:
        parser.error('--max-lines must be at least 2')
    try:
        data = chunk_repository(repository, arguments.max_lines, output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n',
                          encoding='utf-8')
    except (OSError, RuntimeError) as error:
        print(f'Error: {error}', file=sys.stderr)
        return 1
    print(f"Processed {data['summary']['processed_files']} files; "
          f"generated {data['summary']['chunks']} chunks: {output}")
    for skipped in data['skipped_files']:
        print(f"Skipped {skipped['path']}: {skipped['reason']}", file=sys.stderr)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
