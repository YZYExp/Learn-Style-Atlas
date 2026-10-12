#!/usr/bin/env python3
"""Check PDF completeness, readable credits and chapter boundaries."""
import json
import zipfile
from pypdf import PdfReader
from build import ROOT, OUT, chapter_paths

config = json.loads((ROOT / 'book.json').read_text())
paths = chapter_paths()
folder = OUT / 'pdf'
book = PdfReader(folder / 'style-atlas.pdf')
cover = book.pages[0].extract_text().replace(' ', '').replace('\n', '')
for text in [config['credit'], config['ai_notice']]:
    assert text.replace(' ', '') in cover, f'Missing credit: {text}'
starts = [''.join(page.extract_text().split()) for page in book.pages]
source_urls = json.loads((ROOT / 'editorial/source-index.json').read_text())
appendix = False
for page, text in zip(book.pages, starts):
    appendix |= text.startswith('资料与进一步阅读')
    if appendix:
        continue
    urls = {str(ref.get_object().get('/A', {}).get('/URI', '')) for ref in page.get('/Annots', [])}
    for sid, url in source_urls.items():
        if url in urls:
            assert sid + ':' in text, f'Missing same-page source: {sid}'
for path in paths:
    reader = PdfReader(folder / (path.stem + '.pdf'))
    title = ''.join(path.read_text().splitlines()[0].removeprefix('# ').split())
    assert any(page.startswith(title) for page in starts), f'Chapter does not start a page: {title}'
    assert title in ''.join(reader.pages[0].extract_text().split()), f'Missing unit: {path}'
    assert not any('\ufffd' in page.extract_text() for page in reader.pages), f'Broken text: {path}'
with zipfile.ZipFile(folder / 'style-atlas-chapters.zip') as archive:
    assert set(archive.namelist()) == {p.stem + '.pdf' for p in paths}
    assert archive.testzip() is None
print(f'PASS: full book ({len(book.pages)} pages), {len(paths)} unit PDFs, credits, chapter starts and ZIP')
