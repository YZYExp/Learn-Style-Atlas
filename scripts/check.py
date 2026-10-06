#!/usr/bin/env python3
"""Validate real deliverable constraints: links, image bytes, order and build anchors."""
from pathlib import Path
from html.parser import HTMLParser
import hashlib
import base64
import argparse
import binascii
import json
import re

ROOT = Path(__file__).resolve().parents[1]


class Scan(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.refs = []
        self.images = 0
        self.image_bytes = []
        self.image_alt = []
        self.sections = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if 'id' in a:
            self.ids.append(a['id'])
        if tag == 'a' and a.get('href', '').startswith('#'):
            self.refs.append(a['href'][1:])
        if tag == 'img' and a.get('src', '').startswith('data:image/jpeg;base64,'):
            self.images += 1
            try:
                self.image_bytes.append(base64.b64decode(a['src'].split(',',1)[1],validate=True))
            except binascii.Error:
                self.image_bytes.append(b'')
            self.image_alt.append(a.get('alt',''))
        if tag == 'section':
            self.sections.append(a.get('id'))


def subprocess_output():
    import subprocess
    tracked=subprocess.check_output(['git','ls-files'],cwd=ROOT,text=True).splitlines()
    return [p for p in tracked if p.endswith('.html')]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--html',action='store_true',help='Verify HTML only after an explicit local HTML build')
    args=parser.parse_args()
    errors = []
    config = json.loads((ROOT/'book.json').read_text())
    docs = [ROOT/'README.md', ROOT/'SUMMARY.md', *sorted((ROOT/'chapters').glob('*.md')), *sorted((ROOT/'editorial').glob('*.md'))]
    for p in docs:
        for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', p.read_text()):
            if target.startswith(('https://', 'http://', '#')):
                continue
            if not (p.parent / target.split('#')[0]).exists():
                errors.append(f'{p.relative_to(ROOT)} missing {target}')
    chapter_files = sorted((ROOT/'chapters').glob('*.md'))
    if len(chapter_files) != config['manuscript_units']:
        errors.append('Manuscript unit count does not match final scope')
    entries = json.loads((ROOT/'assets/manifest.json').read_text())
    if len(entries) != config['unique_illustrations'] or len({e['id'] for e in entries}) != config['unique_illustrations']:
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
    image_uses=sum(len(re.findall(r'!\[',p.read_text())) for p in chapter_files)
    if image_uses != config['illustration_uses']:
        errors.append('Markdown illustration reference count mismatch')
    if args.html:
        s = Scan()
        s.feed((ROOT/'build/index.html').read_text())
        if len(set(s.ids)) != len(s.ids):
            errors.append('Duplicate HTML ids')
        if set(s.refs)-set(s.ids):
            errors.append('Broken HTML anchor links')
        if s.images != config['illustration_uses']:
            errors.append(f'Illustration uses mismatch: {s.images}')
        allowed = {hashlib.sha256((ROOT/e['reading_image']).read_bytes()).hexdigest() for e in entries}
        if any(hashlib.sha256(b).hexdigest() not in allowed for b in s.image_bytes):
            errors.append('Embedded JPEG does not match a reading image')
        if not all(s.image_alt):
            errors.append('Missing illustration description')
    order = re.findall(r'\]\(([^)]+\.md)\)',(ROOT/'SUMMARY.md').read_text())
    if len(order) != config['manuscript_units']+1 or len(order)!=len(set(order)):
        errors.append('Reading sequence has duplicate or missing units')
    expected = {str(p.relative_to(ROOT)) for p in chapter_files}|{'editorial/SOURCES.md'}
    if set(order) != expected:
        errors.append('Reading sequence does not include all manuscript and sources')
    if args.html and len(s.sections) != len(order):
        errors.append('HTML section count mismatch')
    for p in chapter_files:
        text=p.read_text()
        if re.search(r'待补|待扩写|TODO|TBD|第一卷|后续.*扩充',text):
            errors.append('Unfinished or obsolete formal text: '+p.name)
        if len(re.findall(r'[\u4e00-\u9fff]',text)) < 250:
            errors.append('Suspiciously short manuscript: '+p.name)
    sources = json.loads((ROOT/'editorial/source-index.json').read_text())
    bibliography = (ROOT/'editorial/SOURCES.md').read_text()
    if len(sources) != 40 or set(re.findall(r'^\| (S\d+) \|', bibliography, re.M)) != set(sources):
        errors.append('Source index and bibliography differ')
    history_count = 0
    for p in chapter_files:
        text = p.read_text()
        for sid, target in re.findall(r'\[(S\d+)\]\(([^)]+)\)', text):
            if sid not in sources or target != sources[sid]:
                errors.append('Invalid source citation: '+p.name+' '+sid)
        if '## 来源与发展' in text:
            history_count += 1
            history = text.split('## 来源与发展',1)[1].split('\n## ',1)[0]
            if not re.search(r'\[S\d+\]\(https://', history):
                errors.append('History lacks adjacent source: '+p.name)
    if history_count != config['style_chapters']:
        errors.append('Not all style chapters contain origins and development')
    merged = (ROOT/'build/book.md').read_text()
    anchors = re.findall(r'<a id="([^"]+)"></a>', merged)
    refs = re.findall(r'\]\(#([^\)]+)\)', merged)
    if len(set(anchors)) != len(order) or set(refs)-set(anchors):
        errors.append('Merged Markdown anchors are invalid')
    for target in re.findall(r'!\[[^\]]*\]\(([^)]+)\)', merged):
        if not (ROOT/'build'/target).exists():
            errors.append('Merged Markdown image missing: '+target)
    if errors:
        raise SystemExit('\n'.join(errors))
    if len(subprocess_output()) > 0:
        errors.append('HTML unexpectedly tracked by Git')
    if errors:
        raise SystemExit('\n'.join(errors))
    print(f'PASS: {len(docs)} Markdown files, {len(entries)} original checksums, {image_uses} Markdown image uses; complete reading order, local links and reading anchors')


if __name__ == '__main__':
    main()
