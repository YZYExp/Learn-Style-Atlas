#!/usr/bin/env python3
"""Validate real deliverable constraints: links, image bytes, order and build anchors."""
from pathlib import Path
from html.parser import HTMLParser
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[1]


class Scan(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.refs = []
        self.images = 0
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if 'id' in a:
            self.ids.append(a['id'])
        if tag == 'a' and a.get('href', '').startswith('#'):
            self.refs.append(a['href'][1:])
        if tag == 'img' and a.get('src', '').startswith('data:image/jpeg;base64,'):
            self.images += 1


def main():
    errors = []
    docs = [ROOT/'README.md', ROOT/'SUMMARY.md', *sorted((ROOT/'chapters').glob('*.md')), *sorted((ROOT/'editorial').glob('*.md'))]
    for p in docs:
        for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', p.read_text()):
            if target.startswith(('https://', 'http://', '#')):
                continue
            if not (p.parent / target.split('#')[0]).exists():
                errors.append(f'{p.relative_to(ROOT)} missing {target}')
    chapter_files = sorted((ROOT/'chapters').glob('*.md'))
    if len(chapter_files) != 24:
        errors.append('Expected 24 complete manuscript units')
    entries = json.loads((ROOT/'assets/manifest.json').read_text())
    if len(entries) != 16 or len({e['id'] for e in entries}) != 16:
        errors.append('Illustration index count or unique ids invalid')
    for e in entries:
        p = ROOT/e['original']
        if hashlib.sha256(p.read_bytes()).hexdigest() != e['sha256_original']:
            errors.append('Original checksum changed: '+e['id'])
        jpg = ROOT/e['reading_image']
        if not jpg.read_bytes().startswith(b'\xff\xd8'):
            errors.append('Invalid reading JPEG: '+e['id'])
        uses = [p for p in chapter_files if '../'+e['reading_image'] in p.read_text()]
        if not uses:
            errors.append('Unreferenced image: '+e['id'])
    s = Scan()
    s.feed((ROOT/'build/index.html').read_text())
    if len(set(s.ids)) != len(s.ids):
        errors.append('Duplicate HTML ids')
    if set(s.refs)-set(s.ids):
        errors.append('Broken HTML anchor links')
    if s.images != 28:
        errors.append(f'Expected 16 chapter images + 12 comparison images, got {s.images}')
    if errors:
        raise SystemExit('\n'.join(errors))
    print(f'PASS: {len(docs)} Markdown files, 16 image checksums, 28 embedded image uses, all local links and HTML anchors')


if __name__ == '__main__':
    main()
