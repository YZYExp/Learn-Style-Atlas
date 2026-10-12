#!/usr/bin/env python3
"""Render all units and a combined book, with adjacent citations as page footnotes."""
import html
import json
import re
import zipfile
from io import BytesIO
from pypdf import PdfReader, PdfWriter
from build import ROOT, OUT, LINK, chapter_paths, markdown, inline
from weasyprint import HTML

CSS = '''
@page { size: A4; margin: 18mm 16mm 45mm;
 @bottom-center { content: counter(page); font-size: 9pt; }
 @footnote { border-top: .5pt solid #bbb; padding-top: 2mm; }
}
body { font: 11pt/1.7 "Noto Sans CJK SC", sans-serif; color: #283836; }
section { break-before: page; } h1 { font-size: 25pt; } h2 { font-size: 20pt; }
h2,h3 { break-after: avoid; } img { max-width: 100%; max-height: 155mm; display: block; margin: 4mm auto; }
a { color: #196b60; overflow-wrap: anywhere; } table { border-collapse: collapse; width: 100%; font-size: 9pt; }
th,td { border: .5pt solid #bbb; padding: 2mm; vertical-align: top; }
table img { max-height: 65mm; } tr { break-inside: avoid; }
'''


def main():
    config = json.loads((ROOT / 'book.json').read_text())
    sources = {}
    for line in (ROOT / 'editorial/SOURCES.md').read_text().splitlines():
        cells = line.strip('|').split('|')
        if len(cells) > 2 and re.fullmatch(r'S\d+', cells[0].strip()):
            sources[cells[0].strip()] = cells[1].strip()
    source_urls = json.loads((ROOT / 'editorial/source-index.json').read_text())
    def write_pdf(content, target, include_sources=True):
        raw = HTML(string=content, base_url=str(ROOT)).write_pdf()
        reader = PdfReader(BytesIO(raw))
        writer = PdfWriter()
        appendix = False
        for page in reader.pages:
            if ''.join(page.extract_text().split()).startswith('资料与进一步阅读'):
                appendix = True
            urls = set()
            for ref in page.get('/Annots', []):
                action = ref.get_object().get('/A', {})
                if action.get('/URI'):
                    urls.add(str(action['/URI']))
            notes = [sid + ': ' + sources[sid] for sid, url in source_urls.items() if url in urls]
            if notes and include_sources and not appendix:
                footer = '<html><meta charset="utf-8"><style>@page {size:A4;margin:0} body{margin:0;font:6pt/1.3 "Noto Sans CJK SC"} div{position:absolute;left:16mm;right:16mm;bottom:13mm;max-height:30mm;border-top:.5pt solid #bbb;padding-top:2mm;overflow-wrap:anywhere} p{margin:0}</style><div>' + ''.join('<p>' + inline(note) + '</p>' for note in notes) + '</div></html>'
                overlay = PdfReader(BytesIO(HTML(string=footer).write_pdf()))
                page.merge_page(overlay.pages[0])
        writer.append(reader)
        writer.add_metadata({'/Title': config['title'], '/Author': config['credit'], '/Subject': config['ai_notice']})
        with open(target, 'wb') as output:
            writer.write(output)
    dest = OUT / 'pdf'
    dest.mkdir(parents=True, exist_ok=True)
    sections = []
    toc = []
    for path in chapter_paths():
        def rewrite(match):
            bang, label, target = match.groups()
            if target.startswith(('https://', 'http://', '#')):
                return match[0]
            resolved = (path.parent / target).resolve()
            if bang:
                return f'![{label}]({resolved.as_uri()})'
            return f'[{label}](#section-{resolved.stem})'
        body = markdown(LINK.sub(rewrite, path.read_text()))
        title = path.read_text().splitlines()[0].removeprefix('# ')
        toc.append(f'<p><a href="#section-{path.stem}">{html.escape(title)}</a></p>')
        section = f'<section id="section-{path.stem}">{body}</section>'
        sections.append(section)
        credit = '<p>' + html.escape(config['credit']) + '</p><p>' + html.escape(config['ai_notice']) + '</p>'
        document = lambda content: '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>' + html.escape(title) + '</title><style>' + CSS + '</style><body>' + content + '</body></html>'
        write_pdf(document(re.sub(r'href="#section-([^"]+)"', lambda m: 'href="' + m[1] + '.pdf"', section.replace('</h2>', '</h2>' + credit, 1))), dest / (path.stem + '.pdf'), path.parent.name != 'editorial')
    cover = '<h1>' + html.escape(config['title']) + '</h1>' + credit + '<p>版本 ' + html.escape(config['version']) + '</p>'
    write_pdf(document(cover + '<section><h2>目录</h2>' + ''.join(toc) + '</section>' + ''.join(sections)), dest / 'style-atlas.pdf')
    with zipfile.ZipFile(dest / 'style-atlas-chapters.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for pdf in sorted(dest.glob('*.pdf')):
            if pdf.name != 'style-atlas.pdf':
                archive.write(pdf, pdf.name)
    print(f'Built full book and {len(sections)} independent units in {dest}')

if __name__ == '__main__':
    main()
