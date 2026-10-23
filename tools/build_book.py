#!/usr/bin/env python3
"""Собирает все руководства репозитория в одну HTML-книгу BOOK.html.

Книга открывается в любом браузере без интернета: слева оглавление,
справа текст выбранного руководства, без служебных символов разметки.

Запуск из корня репозитория:
    python3 tools/build_book.py
"""

import html
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "BOOK.html")

GROUPS = [
    ("Начало", ["Advanced/00_NAVIGATOR.md"]),
    ("Часть 0. Как учиться", ["Advanced/01_LEARNING_HOW_TO_LEARN.md", "Advanced/02_STUDY_PLAN.md"]),
    ("Часть 1. Язык музыки", ["Advanced/03_MUSIC_BASICS.md", "Advanced/04_HARMONY.md", "Advanced/05_MELODY.md", "Advanced/06_RHYTHM_DRUMS.md"]),
    ("Часть 2. Создание трека", ["Advanced/07_ARRANGEMENT_FORM.md", "Advanced/08_SOUND_DESIGN_SYNTHESIS.md", "Advanced/09_ORCHESTRATION.md"]),
    ("Часть 3. Звук", ["Advanced/10_MIXING.md", "Advanced/11_MASTERING.md"]),
    ("Часть 4. Игры и стили", ["Advanced/12_GAME_AUDIO.md", "Advanced/13_JAPANESE_COMPOSERS.md", "Advanced/14_MICROTONAL_19EDO.md"]),
    ("Часть 5. Практика и профессия", ["Advanced/15_STUDIO_SETUP.md", "Advanced/16_EAR_WORKFLOW.md", "Advanced/17_CAREER_BUSINESS.md"]),
    ("Приложения", ["Advanced/18_GLOSSARY.md", "Advanced/19_RESOURCES.md", "Advanced/20_LISTENING.md"]),
    ("Справочники", [
        "TUTORIALS/01_MIXING_MASTERING_LUFS_RU.md",
        "TUTORIALS/02_GAME_MUSIC_COMPOSITION_RU.md",
    ]),
    ("Инструменты 19-EDO", [
        "README.md",
        "docs/INSTRUCTION_RU.md",
        "docs/RESEARCH_RU.md",
    ]),
]
ALL_DOCS = [p for _, docs in GROUPS for p in docs]


def doc_id(path):
    return "doc-" + re.sub(r"[^\w]+", "-", path[:-3]).strip("-")


def slugify(text):
    """Якорь в стиле GitHub: строчные буквы, без знаков препинания, пробел → дефис."""
    return re.sub(r"[^\w\- ]", "", text.lower()).replace(" ", "-")


class Doc:
    def __init__(self, path):
        self.path = path
        self.id = doc_id(path)
        self.dir = os.path.dirname(path)
        with open(os.path.join(ROOT, path), encoding="utf-8") as f:
            self.lines = f.read().split("\n")
        self.title = next((l[2:].strip() for l in self.lines if l.startswith("# ")),
                          path)
        self.slugs = {}

    def anchor(self, slug):
        return f"{self.id}--{slug}"

    def new_heading_id(self, text):
        base = slugify(text)
        n = self.slugs.get(base, 0)
        self.slugs[base] = n + 1
        return self.anchor(base if n == 0 else f"{base}-{n}")

    # ---------------------------------------------------------------- inline
    def resolve(self, url):
        if url.startswith(("http://", "https://", "mailto:")):
            return url, True
        path, _, frag = url.partition("#")
        if not path:
            return "#" + self.anchor(frag), False
        target = os.path.normpath(os.path.join(self.dir, path)).replace(os.sep, "/")
        if target in ALL_DOCS:
            tid = doc_id(target)
            return "#" + (f"{tid}--{frag}" if frag else tid), False
        return target, True

    def inline(self, text):
        parts = []
        pos = 0
        for m in re.finditer(r"\[([^\]]+)\]\(([^)\s]+)\)", text):
            parts.append(self.autolink(text[pos:m.start()]))
            href, external = self.resolve(m.group(2))
            attrs = ' target="_blank" rel="noopener"' if external and href.startswith("http") else ""
            parts.append(f'<a href="{html.escape(href)}"{attrs}>{html.escape(m.group(1))}</a>')
            pos = m.end()
        parts.append(self.autolink(text[pos:]))
        return "".join(parts)

    @staticmethod
    def autolink(text):
        out = []
        pos = 0
        for m in re.finditer(r"https?://[^\s<>()]+[^\s<>().,;:]", text):
            out.append(html.escape(text[pos:m.start()]))
            url = html.escape(m.group(0))
            out.append(f'<a href="{url}" target="_blank" rel="noopener">{url}</a>')
            pos = m.end()
        out.append(html.escape(text[pos:]))
        return "".join(out)

    # ----------------------------------------------------------------- blocks
    def render(self):
        out = []
        lines = self.lines
        i = 0
        para = []

        def flush_para():
            if para:
                out.append(f"<p>{self.inline(' '.join(para))}</p>")
                para.clear()

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            if stripped.startswith("```"):
                flush_para()
                i += 1
                code = []
                while i < len(lines) and not lines[i].strip().startswith("```"):
                    code.append(lines[i])
                    i += 1
                i += 1
                out.append(f"<pre><code>{html.escape(chr(10).join(code))}</code></pre>")
                continue
            m = re.match(r"^(#{1,6})\s+(.*)$", line)
            if m:
                flush_para()
                level = len(m.group(1))
                text = m.group(2).strip()
                out.append(f'<h{level} id="{self.new_heading_id(text)}">'
                           f"{self.inline(text)}</h{level}>")
                i += 1
                continue
            if re.match(r"^-{3,}\s*$", stripped):
                flush_para()
                out.append("<hr>")
                i += 1
                continue
            if stripped.startswith("|"):
                flush_para()
                block = []
                while i < len(lines) and lines[i].strip().startswith("|"):
                    block.append(lines[i].strip())
                    i += 1
                out.append(self.table(block))
                continue
            if re.match(r"^\s*(-|\d+\.)\s+", line):
                flush_para()
                i = self.list_block(i, out)
                continue
            if not stripped:
                flush_para()
                i += 1
                continue
            para.append(stripped)
            i += 1
        flush_para()
        result = "\n".join(out)
        # ответы самопроверки скрыты, пока читатель сам не откроет их
        return re.sub(r'<h3 id="[^"]+">Ответы</h3>\n(<ol>.*?</ol>)',
                      r'<details class="answers"><summary>Показать ответы</summary>\1</details>',
                      result, flags=re.S)

    def table(self, block):
        rows = [[c.strip() for c in r.strip("|").split("|")] for r in block
                if not re.match(r"^\|[\s:|-]+\|$", r)]
        head, body = rows[0], rows[1:]
        h = "".join(f"<th>{self.inline(c)}</th>" for c in head)
        b = "".join("<tr>" + "".join(f"<td>{self.inline(c)}</td>" for c in r) + "</tr>"
                    for r in body)
        return (f'<div class="table-wrap"><table><thead><tr>{h}</tr></thead>'
                f"<tbody>{b}</tbody></table></div>")

    def list_block(self, i, out):
        """Списки с вложенностью по отступу."""
        items = []  # (indent, ordered, text)
        lines = self.lines
        while i < len(lines):
            line = lines[i]
            m = re.match(r"^(\s*)(-|\d+\.)\s+(.*)$", line)
            if m:
                items.append([len(m.group(1)), m.group(2) != "-", m.group(3).strip()])
                i += 1
                continue
            if line.strip() and line.startswith("  ") and items:
                items[-1][2] += " " + line.strip()
                i += 1
                continue
            if not line.strip() and i + 1 < len(lines) and \
                    re.match(r"^\s*(-|\d+\.)\s+", lines[i + 1]) and \
                    (lines[i + 1].startswith(" ") or items and
                     (lines[i + 1].lstrip()[0].isdigit()) == items[0][1]):
                i += 1
                continue
            break
        out.append(self.nest(items))
        return i

    def nest(self, items):
        html_out = []
        stack = []  # (indent, tag)
        for indent, ordered, text in items:
            tag = "ol" if ordered else "ul"
            while stack and indent < stack[-1][0]:
                html_out.append(f"</li></{stack.pop()[1]}>")
            if not stack or indent > stack[-1][0]:
                html_out.append(f"<{tag}>")
                stack.append((indent, tag))
            else:
                html_out.append("</li>")
            html_out.append(f"<li>{self.inline(text)}")
        while stack:
            html_out.append(f"</li></{stack.pop()[1]}>")
        return "".join(html_out)


CSS = """
:root{--bg:#fbfaf7;--panel:#f2efe8;--text:#1f2328;--muted:#5d6470;--accent:#2f5fa7;
--border:#d9d4c7;--code:#efece4;--row:#f6f4ef;--head:#e8e3d6}
@media (prefers-color-scheme:dark){:root{--bg:#16181c;--panel:#1d2026;--text:#e6e6e3;
--muted:#9aa1ab;--accent:#8db4f0;--border:#343a44;--code:#22262d;--row:#1b1e23;--head:#272c34}}
*{box-sizing:border-box}
html{scroll-padding-top:16px}
body{margin:0;background:var(--bg);color:var(--text);
font:17px/1.65 "Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif}
a{color:var(--accent);text-decoration:none;overflow-wrap:anywhere}
p,li,td,th{overflow-wrap:break-word}a:hover{text-decoration:underline}
.layout{display:flex;min-height:100vh}
nav{width:310px;flex:none;background:var(--panel);border-right:1px solid var(--border);
position:sticky;top:0;height:100vh;overflow-y:auto;padding:18px 14px 40px}
nav .book-title{font-weight:700;font-size:19px;margin:0 6px 12px}
nav input{width:100%;padding:8px 10px;border:1px solid var(--border);border-radius:6px;
background:var(--bg);color:var(--text);font-size:15px;margin-bottom:10px}
nav .group{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);
margin:18px 6px 6px}
nav a.doc{display:block;padding:6px 8px;border-radius:6px;color:var(--text);font-size:15px;
line-height:1.35}
nav a.doc:hover{background:var(--head);text-decoration:none}
nav a.doc.active{background:var(--accent);color:#fff}
nav .toc{margin:4px 0 8px 10px;border-left:2px solid var(--border);padding-left:8px}
nav .toc a{display:block;font-size:14px;color:var(--muted);padding:3px 4px;line-height:1.3}
main{flex:1;min-width:0;padding:32px 48px 80px}
article{max-width:860px;margin:0 auto}
h1{font-size:32px;line-height:1.25;margin:0 0 18px}
h2{font-size:25px;margin:44px 0 14px;padding-bottom:6px;border-bottom:1px solid var(--border)}
h3{font-size:20px;margin:30px 0 10px}
h4{font-size:17px;margin:24px 0 8px}
p,ul,ol{margin:0 0 14px}
ul,ol{padding-left:26px}li{margin:4px 0}li>ul,li>ol{margin:6px 0}
hr{border:0;border-top:1px solid var(--border);margin:32px 0}
.table-wrap{overflow-x:auto;margin:0 0 20px;border:1px solid var(--border);border-radius:8px}
table{border-collapse:collapse;width:100%;font-size:15px;line-height:1.45}
th,td{padding:8px 12px;text-align:left;vertical-align:top;border-bottom:1px solid var(--border)}
th{background:var(--head);font-weight:600}
tbody tr:nth-child(even){background:var(--row)}tbody tr:last-child td{border-bottom:0}
pre{background:var(--code);border:1px solid var(--border);border-radius:8px;padding:14px 16px;
overflow-x:auto;font:15px/1.5 Consolas,"DejaVu Sans Mono",Menlo,monospace;margin:0 0 18px}
.pager{display:flex;justify-content:space-between;gap:12px;margin-top:48px;padding-top:18px;
border-top:1px solid var(--border)}
.pager a{display:block;max-width:48%;padding:10px 14px;border:1px solid var(--border);
border-radius:8px}
.menu-btn{display:none}
details.answers{border:1px solid var(--border);border-radius:8px;padding:10px 16px;margin:0 0 18px;
background:var(--row)}
details.answers summary{cursor:pointer;font-weight:600;color:var(--accent)}
details.answers[open] summary{margin-bottom:8px}
@media (max-width:900px){
.layout{display:block}
nav{position:fixed;inset:0 auto 0 0;width:85%;max-width:340px;z-index:10;
transform:translateX(-100%);transition:transform .2s;box-shadow:0 0 30px rgba(0,0,0,.3)}
nav.open{transform:none}
main{padding:72px 16px 60px}
html{scroll-padding-top:64px}
pre{font-size:12.5px;padding:12px}
h1{font-size:26px}h2{font-size:21px}
.menu-btn{display:block;position:fixed;top:0;left:0;right:0;width:100%;z-index:11;
padding:12px 16px;text-align:left;border:0;border-bottom:1px solid var(--border);
background:var(--panel);color:var(--text);font-size:16px;font-weight:600}
nav{padding-top:64px}}
@media print{nav,.menu-btn,.pager{display:none}main{padding:0}
section.doc{display:block!important;page-break-after:always}}
"""

JS = """
(function(){
var docs=[].slice.call(document.querySelectorAll('section.doc'));
var links=[].slice.call(document.querySelectorAll('nav a.doc'));
var nav=document.querySelector('nav');
function show(hash){
  var target=hash?document.getElementById(decodeURIComponent(hash.slice(1))):null;
  var sec=target?(target.closest('section.doc')):null;
  if(!sec)sec=docs[0];
  docs.forEach(function(d){d.style.display=d===sec?'':'none';});
  links.forEach(function(a){
    var on=a.getAttribute('href')==='#'+sec.id;
    a.classList.toggle('active',on);
    var toc=a.nextElementSibling;if(toc&&toc.classList.contains('toc'))toc.hidden=!on;
  });
  if(target&&target!==sec)target.scrollIntoView();else window.scrollTo(0,0);
  nav.classList.remove('open');
  var h=sec.querySelector('h1');document.title=(h?h.textContent+' — ':'')+'Музыкальная книга';
}
window.addEventListener('hashchange',function(){show(location.hash);});
show(location.hash);
document.querySelector('.menu-btn').addEventListener('click',function(){nav.classList.toggle('open');});
var q=document.getElementById('filter');
q.addEventListener('input',function(){
  var v=q.value.trim().toLowerCase();
  links.forEach(function(a){
    var sec=document.getElementById(a.getAttribute('href').slice(1));
    var hit=!v||a.textContent.toLowerCase().indexOf(v)>=0||sec.textContent.toLowerCase().indexOf(v)>=0;
    a.style.display=hit?'':'none';
  });
});
})();
"""


def main():
    docs = [Doc(p) for p in ALL_DOCS]
    by_path = {d.path: d for d in docs}
    sections = []
    for idx, d in enumerate(docs):
        body = d.render()
        pager = ['<div class="pager">']
        pager.append(f'<a href="#{docs[idx - 1].id}">← {html.escape(docs[idx - 1].title)}</a>'
                     if idx > 0 else "<span></span>")
        if idx + 1 < len(docs):
            pager.append(f'<a href="#{docs[idx + 1].id}">{html.escape(docs[idx + 1].title)} →</a>')
        pager.append("</div>")
        sections.append(f'<section class="doc" id="{d.id}"><article>{body}'
                        f'{"".join(pager)}</article></section>')

    nav = ['<div class="book-title">Музыкальная книга</div>',
           '<input id="filter" type="search" placeholder="Поиск по руководствам">']
    for group, paths in GROUPS:
        nav.append(f'<div class="group">{html.escape(group)}</div>')
        for p in paths:
            d = by_path[p]
            nav.append(f'<a class="doc" href="#{d.id}">{html.escape(d.title)}</a>')
            h2 = re.findall(r'<h2 id="([^"]+)">(.*?)</h2>', sections[ALL_DOCS.index(p)])
            if h2:
                nav.append('<div class="toc" hidden>' + "".join(
                    f'<a href="#{hid}">{re.sub("<[^>]+>", "", t)}</a>' for hid, t in h2) + "</div>")

    page = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Музыкальная книга</title>
<style>{CSS}</style>
</head>
<body>
<button class="menu-btn" type="button">☰ Оглавление</button>
<div class="layout">
<nav>{"".join(nav)}</nav>
<main>{"".join(sections)}</main>
</div>
<script>{JS}</script>
</body>
</html>
"""
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"BOOK.html: документов — {len(docs)}, размер — {len(page) // 1024} КБ")


if __name__ == "__main__":
    main()
