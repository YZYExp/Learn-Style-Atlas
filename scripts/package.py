#!/usr/bin/env python3
"""Archive tracked sources, Git history and Markdown output; never HTML."""
import argparse
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.is_relative_to(ROOT):
        parser.error('Place the archive outside the repository')
    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    paths = {ROOT / p for p in tracked if p and not p.endswith('.html')}
    paths.update((ROOT / '.git').rglob('*'))
    paths.add(ROOT / '.git')
    # Git needs this directory even when every branch and tag is packed.
    (ROOT / '.git/refs').mkdir(exist_ok=True)
    paths.add(ROOT / '.git/refs')
    paths.update(p for p in [ROOT / 'build/book.md', ROOT / 'build/stats.json'] if p.exists())
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for p in sorted(paths):
            if p.name.endswith(('.html', '.lock')) or p.is_symlink():
                continue
            archive.write(p, Path(ROOT.name) / p.relative_to(ROOT))
    print(f'Archived {output.name}: {output.stat().st_size} bytes; no HTML')


if __name__ == '__main__':
    main()
