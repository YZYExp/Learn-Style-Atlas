#!/usr/bin/env python3
"""Build the book from its Markdown chapters, with no runtime dependencies."""
from pathlib import Path
import base64
import argparse
import html
import json
import re

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build'
LINK = re.compile(r'(!?)\[([^\]]*)\]\(([^)]+)\)')


def chapter_paths():
    return [ROOT / p for p in re.findall(r'\]\(([^)]+\.md)\)', (ROOT / 'SUMMARY.md').read_text())]


def inline(text):
    text = html.escape(text)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<em>\1</em>', text)

    def replace(m):
        bang, title, url = m.groups()
        if bang:
            return f'<img src="{url}" alt="{title}" loading="lazy" decoding="async">'
        return f'<a href="{url}">{title}</a>'
    return LINK.sub(replace, text)


def markdown(text):
    """Render the explicit subset used by this book: headings, tables, lists, code."""
    lines = text.splitlines()
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.startswith('```'):
            code = []
            i += 1
            while i < len(lines) and not lines[i].startswith('```'):
                code.append(lines[i])
                i += 1
            result.append('<pre><code>' + html.escape('\n'.join(code)) + '</code></pre>')
            i += 1
            continue
        if line.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].startswith('|'):
                row = [v.strip() for v in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-+:?', v.replace(' ', '')) for v in row):
                    rows.append(row)
                i += 1
            body = '<thead><tr>' + ''.join('<th>' + inline(v) + '</th>' for v in rows[0]) + '</tr></thead><tbody>'
            for row in rows[1:]:
                body += '<tr>' + ''.join('<td>' + inline(v) + '</td>' for v in row) + '</tr>'
            grid = ' visual-grid' if any('![' in v for row in rows for v in row) else ''
            result.append('<div class="table-scroll' + grid + '"><table>' + body + '</tbody></table></div>')
            continue
        m = re.match(r'^(#{1,6}) (.*)', line)
        if m:
            n = min(len(m[1]) + 1, 6)
            result.append(f'<h{n}>' + inline(m[2]) + f'</h{n}>')
            i += 1
            continue
        if line.startswith('- '):
            items = []
            while i < len(lines) and lines[i].startswith('- '):
                items.append('<li>' + inline(lines[i][2:]) + '</li>')
                i += 1
            result.append('<ul>' + ''.join(items) + '</ul>')
            continue
        paragraph = [line]
        i += 1
        while i < len(lines) and lines[i].strip() and not re.match(r'^(#|\||- |```)', lines[i]):
            paragraph.append(lines[i])
            i += 1
        result.append('<p>' + inline(' '.join(paragraph)) + '</p>')
    return '\n'.join(result)


def main():
    parser = argparse.ArgumentParser(description='Build Markdown by default; HTML is an explicit local option.')
    parser.add_argument('--html', action='store_true', help='Also generate the untracked offline HTML locally')
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True)
    config = json.loads((ROOT / 'book.json').read_text())
    entries = json.loads((ROOT / 'assets/manifest.json').read_text())
    paths = chapter_paths()
    anchors = {p.resolve(): 'section-' + p.stem for p in paths}
    merged = ['# 看懂画风：一场有趣的插画旅行\n\n修订版 · v1.1 · 2026-10-06\n\n所有插图均为 AI 生成教学示意。\n']
    merged.append('## 全书目录\n\n' + '\n'.join(f'- [{p.read_text().splitlines()[0].removeprefix("# ")}](#{anchors[p.resolve()]})' for p in paths) + '\n')
    sections = []
    toc = []
    for p in paths:
        original = p.read_text()
        title = original.splitlines()[0].removeprefix('# ')
        anchor = anchors[p.resolve()]
        toc.append(f'<a href="#{anchor}">{html.escape(title)}</a>')

        def rewrite(m, embed=False):
            bang, label, target = m.groups()
            if target.startswith(('http://', 'https://', '#')):
                return m[0]
            resolved = (p.parent / target).resolve()
            if bang:
                if embed:
                    data = base64.b64encode(resolved.read_bytes()).decode()
                    return f'![{label}](data:image/jpeg;base64,{data})'
                return f'![{label}](../{resolved.relative_to(ROOT)})'
            if resolved in anchors:
                return f'[{label}](#{anchors[resolved]})'
            return f'[{label}](../{resolved.relative_to(ROOT)})'

        merged.append(f'\n<a id="{anchor}"></a>\n\n' + LINK.sub(rewrite, original))
        rendered = markdown(LINK.sub(lambda m: rewrite(m, True), original)) if args.html else ''
        sections.append(f'<section id="{anchor}" aria-label="{html.escape(title)}">{rendered}<a class="back" href="#top">↑ 返回开头</a></section>')
    if args.html:
        css = '''
        :root{--bg:#f5f1e8;--page:#fffcf6;--ink:#283836;--muted:#65716b;--line:#d7dfd7;--accent:#196b60}
        *{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--bg);color:var(--ink);font:17px/1.95 system-ui,-apple-system,"PingFang SC","Microsoft YaHei",sans-serif}
        body.dark{--bg:#172421;--page:#20312d;--ink:#e8efe8;--muted:#acbeb2;--line:#3f554a;--accent:#8ad3ba}
        a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}aside{position:fixed;inset:0 auto 0 0;width:290px;padding:32px 24px;overflow:auto;border-right:1px solid var(--line);background:var(--page)}
        .brand{font-size:24px;font-weight:750;line-height:1.4}.label{font:12px/1.6 system-ui;letter-spacing:.13em;color:var(--muted)}nav{margin-top:24px}nav a[hidden]{display:none}nav a{display:block;padding:7px 0;font-size:13px;line-height:1.6}nav a:nth-child(3),nav a:nth-child(13),nav a:nth-child(19){margin-top:16px;border-top:1px solid var(--line);padding-top:17px}
        main{max-width:1130px;margin-left:290px;padding:50px 54px 90px}header{padding:42px 0 56px;border-bottom:2px solid var(--accent)}h1{font-size:44px;line-height:1.3;margin:20px 0}header p{max-width:650px;color:var(--muted)}.pill{display:inline-block;font-size:12px;border:1px solid var(--line);border-radius:20px;padding:2px 12px;margin-right:8px}
        section{padding:40px 0;border-bottom:1px solid var(--line);scroll-margin-top:20px}h2{font-size:30px;line-height:1.5;letter-spacing:-.02em;margin:0 0 28px}h3{font-size:20px;line-height:1.6;margin:32px 0 12px}p{margin:15px 0}strong{font-weight:700}em{color:var(--muted);font-size:14px}img{display:block;width:auto;max-width:100%;max-height:720px;height:auto;margin:24px auto;border-radius:4px;cursor:zoom-in}table img{width:100%;height:auto;max-height:none;margin:0;border-radius:0}
        .table-scroll{overflow:auto;margin:24px 0}.visual-grid table{min-width:620px}.visual-grid td{min-width:150px}.visual-grid th{font-size:13px}input{width:100%;padding:9px 10px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--ink);font:inherit;font-size:13px}table{width:100%;border-collapse:collapse;background:var(--page);font-size:14px;line-height:1.7}th,td{padding:14px;border:1px solid var(--line);vertical-align:top}th{color:var(--accent);text-align:left}pre{overflow:auto;background:var(--page);border-left:3px solid var(--accent);padding:20px;font:14px/1.9 monospace}code{font-size:.9em}.back{font-size:12px;color:var(--muted)}button{border:1px solid var(--line);border-radius:6px;background:var(--page);color:var(--ink);padding:8px 12px;cursor:pointer;margin-top:16px}
        dialog{border:0;background:transparent;padding:20px;max-width:95vw;max-height:95vh}dialog::backdrop{background:#000c}dialog img{margin:0;max-height:88vh;max-width:88vw;cursor:zoom-out}dialog button{position:absolute;right:24px;top:24px;background:#fffcf6;color:#283836;margin:0}
        @media(max-width:900px){aside{position:static;width:auto;border-right:0;border-bottom:1px solid var(--line)}nav{columns:2}nav a{break-inside:avoid}main{margin:0;padding:28px 24px}h1{font-size:34px}h2{font-size:26px}header{padding-top:10px}}@media(max-width:500px){nav{columns:1}th,td{padding:7px}body{font-size:16px}}
        @media print{aside,button,.back,dialog{display:none}main{margin:0;padding:0;max-width:none}body{background:white;color:black}section{break-before:page}img{max-height:18cm}a{color:inherit}table{break-inside:avoid}header{break-after:page}}
        '''
        page = '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>看懂画风 · 全书终稿</title><style>' + css + '</style></head><body id="top">'
        page += '<aside><div class="label">ILLUSTRATION FIELD TRIP</div><div class="brand">看懂画风</div><p class="label">修订版 · 35 个方向 · v1.1</p><button id="theme">切换明暗</button><p><input id="find" type="search" placeholder="查目录：如水彩、漫画、比较" aria-label="筛选目录"></p><nav aria-label="书籍目录">' + ''.join(toc) + '</nav></aside>'
        page += '<main><header><span class="label">一场有趣的插画旅行</span><h1>先看图，<br>再学名字。</h1><p>写给喜欢看图、想说清楚自己喜欢什么的人。跟着不同角色旅行，用具体线索认识画风，用小实验发现区别。</p><span class="pill">43 张独立插图</span><span class="pill">14 组对照</span><span class="pill">53 个正文单元</span><p>2026-10-06 · 所有插图均为 AI 生成教学示意。点击图片可放大。</p></header>'
        page += ''.join(sections) + '</main><dialog id="zoom"><button id="close">关闭 ×</button><img alt="插图放大"></dialog>'
        page += '''<script>document.querySelector('#find').addEventListener('input',e=>document.querySelectorAll('nav a').forEach(a=>a.hidden=!a.textContent.includes(e.target.value)));const zoom=document.querySelector('#zoom');document.querySelector('#theme').onclick=()=>document.body.classList.toggle('dark');document.querySelectorAll('main img').forEach(i=>i.addEventListener('click',()=>{const z=zoom.querySelector('img');z.src=i.src;z.alt=i.alt;zoom.showModal()}));document.querySelector('#close').onclick=()=>zoom.close();zoom.addEventListener('click',e=>{if(e.target===zoom||e.target.tagName==='IMG')zoom.close()});</script></body></html>'''
    (OUT / 'book.md').write_text('\n'.join(merged))
    if args.html:
        (OUT / 'index.html').write_text(page)
    cjk = len(re.findall(r'[\u4e00-\u9fff]', '\n'.join(merged)))
    (OUT / 'stats.json').write_text(json.dumps({'version':config['version'],'units_including_sources':len(paths),'style_chapters':config['style_chapters'],'unique_illustrations':len(entries),'comparison_groups':config['comparison_groups'],'image_uses':sum(len(re.findall(r'!\[',p.read_text())) for p in paths),'cjk_characters':cjk},ensure_ascii=False,indent=2)+'\n')
    print(f'Built {len(paths)} units; {cjk} Chinese characters; Markdown written')


if __name__ == '__main__':
    main()
