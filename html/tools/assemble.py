#!/usr/bin/env python3
"""One self-contained HTML page from the per-page SVGs of a deck (dvisvgm, then fixdvi/svgfix).

The SVGs are inlined, so their text is real text: selectable, searchable, read aloud. Inlined SVGs
share one document, so every id, class and font family is prefixed with its page; a picture that
recurs on every page (the campus background) is stored once and used by reference. Keyboard
navigation, #n for page n, and the deck-size message APICe listens for, as the other HTML decks.

With a fifth argument, the SVG of allglyphs.py's extra page: its fonts, one per family with every
character of the deck, replace the per-page subsets.

Usage: assemble.py <svgdir> <npages> <title> <out.html> [<glyphs.svg>]   (run with python3 -I)
"""
import base64, hashlib, html, re, sys

d, n, title, out = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
union = {}
if len(sys.argv) > 5:
    for fam, data in re.findall(r"@font-face\{font-family:([^;]+);src:url\((data:[^)]+)\)", open(sys.argv[5], encoding='utf-8').read()):
        union[fam.strip()] = data
    # private-use glyphs (old-style figures …) get their real characters too: fontfix.py, run with
    # Homebrew's fonttools interpreter, which reads and writes WOFF2
    import json, subprocess
    r = subprocess.run(['/opt/homebrew/opt/fonttools/libexec/bin/python3', '-I',
                        __import__('os').path.join(__import__('os').path.dirname(__import__('os').path.abspath(__file__)), 'fontfix.py')],
                       input=json.dumps(union), capture_output=True, text=True, timeout=600)
    if r.returncode == 0:
        fixed = json.loads(r.stdout)
        union = {k: v['data'] for k, v in fixed.items()}
        pua = {k: {chr(c): chr(c - 0xE000) for c in v['cps']} for k, v in fixed.items()}
    else:
        print('fontfix failed:', r.stderr[-300:]); pua = {}
else:
    pua = {}
shared, frames, W, H = {}, [], None, None
videos = {}
fonts = {}

# internal links: dvisvgm marks each anchor with <view id='locN'> on its page and links to it as
# 'pK.svg#locN' (often naming the wrong file); in the one page they become '#<page>'
where = {}
for i in range(1, n + 1):
    for v in re.findall(r"<view id='(loc\d+)'", open(f'{d}/p{i}.svg', encoding='utf-8').read()):
        where[v] = i

for i in range(1, n + 1):
    s = open(f'{d}/p{i}.svg', encoding='utf-8').read()
    s = re.sub(r'^<\?xml[^>]*>\s*', '', s)
    s = re.sub(r'<!--.*?-->', '', s, flags=re.S)
    if W is None:
        m = re.search(r"viewBox='([-\d.]+) ([-\d.]+) ([\d.]+) ([\d.]+)'", s)
        W, H = float(m.group(3)), float(m.group(4))
    s = re.sub(r"xlink:href='[^'#]*#(loc\d+)'", lambda m: f"xlink:href='#{where.get(m.group(1), i)}'", s)
    s = re.sub(r"<a xlink:href='(https?:[^']*)'", r"<a xlink:href='\1' target='_blank'", s)
    p = f'p{i}-'
    if pua:
        famof = dict(re.findall(r"text\.(f\d+)\s*\{font-family:([^;}]+)", s))
        def unpua(m):
            fam = famof.get(m.group(1), '').strip()
            table = pua.get(fam)
            if not table:
                return m.group(0)
            return m.group(0)[:m.start(2) - m.start(0)] + ''.join(table.get(ch, ch) for ch in m.group(2)) + m.group(0)[m.end(2) - m.start(0):]
        s = re.sub(r"<text class='(f\d+)'[^>]*>(.*?)</text>", unpua, s, flags=re.S)
    # ligatures as plain letters, so that the text searches as "final": the eye sees no difference
    s = s.translate({0xFB00: 'ff', 0xFB01: 'fi', 0xFB02: 'fl', 0xFB03: 'ffi', 0xFB04: 'ffl'})
    s = re.sub(r"\bid='([^']+)'", lambda m: f"id='{p}{m.group(1)}'", s)
    s = re.sub(r"((?:xlink:)?href)='#([^']*[^'0-9][^']*)'", lambda m: f"{m.group(1)}='#{p}{m.group(2)}'", s)
    s = re.sub(r"url\(#([^)]+)\)", lambda m: f"url(#{p}{m.group(1)})", s)
    s = re.sub(r"class='([^']+)'", lambda m: "class='" + ' '.join(p + c for c in m.group(1).split()) + "'", s)
    def css(m):
        c = m.group(0)
        # a font subset identical to one already met (overlay steps share most of them) is stored
        # once, in the page's head, under a name made from its content
        names = {}
        def face(f):
            fam, data = f.group(1).strip(), f.group(2)
            if fam in union:
                data = union[fam]
            key = 'ff' + hashlib.sha1(data.encode()).hexdigest()[:12]
            names[fam] = key
            fonts.setdefault(key, f"@font-face{{font-family:{key};src:url({data}) format('woff2');}}")
            return ''
        c = re.sub(r"@font-face\{font-family:([^;]+);src:url\((data:[^)]+)\)[^}]*\}", face, c)
        c = re.sub(r'font-family:([^;}]+)', lambda f: f'font-family:{names.get(f.group(1).strip(), p + f.group(1).strip())}', c)
        c = re.sub(r'(?m)^text\.([A-Za-z0-9_-]+)|(?<=[\s}])text\.([A-Za-z0-9_-]+)',
                   lambda f: f'text.{p}{f.group(1) or f.group(2)}', c)
        return c
    s = re.sub(r'<style type=\'text/css\'>.*?</style>', css, s, flags=re.S)
    def hoist(m):
        tag = m.group(0)
        data = re.search(r"(?:xlink:)?href='(data:[^']+)'", tag).group(1)
        key = hashlib.sha1(data.encode()).hexdigest()[:10]
        if key not in shared and data.startswith('data:image/png;base64,') and len(data) > 100000:
            # a large PNG (PDF bitmaps come out of mutool as PNG): JPEG at quality 88 if smaller
            import base64, subprocess
            png = base64.b64decode(data.split(',', 1)[1])
            if png[25] in (4, 6):                       # an alpha channel: JPEG has none, WebP keeps it
                webp = subprocess.run(['magick', 'png:-', '-quality', '90', 'webp:-'], input=png,
                                      capture_output=True, timeout=120).stdout
                if webp and len(webp) < 0.5 * len(png):
                    tag = tag.replace(data, 'data:image/webp;base64,' + base64.b64encode(webp).decode())
                    data = 'data:image/webp;base64,' + base64.b64encode(webp).decode()
                png = b''
            jpg = subprocess.run(['magick', 'png:-', '-quality', '88', 'jpg:-'], input=png,
                                 capture_output=True, timeout=120).stdout if png else b''
            if jpg and len(jpg) < 0.8 * len(png):
                tag = tag.replace(data, 'data:image/jpeg;base64,' + base64.b64encode(jpg).decode())
                data = 'data:image/jpeg;base64,' + base64.b64encode(jpg).decode()
        if key not in shared:
            shared[key] = re.sub(r"(?:xlink:)?href='data:[^']+'", f"href='{data}'", tag)
            shared[key] = re.sub(r"\b(x|y|transform)='[^']*'", '', shared[key])
            shared[key] = shared[key].replace('<image', f"<image id='img{key}'", 1)
        keep = ' '.join(re.findall(r"\b(?:x|y|transform)='[^']*'", tag))
        return f"<use href='#img{key}' {keep}/>"
    s = re.sub(r"<image\b[^>]*?(?:xlink:)?href='data:[^']+'[^>]*/>", hoist, s)
    def vid(m):
        k = videos.setdefault(m.group(1), len(videos))
        return f"<g class='videolink' data-video='v{k}' style='cursor:pointer' onclick='playVideo(this)'><title>Click to play the video</title>"
    s = re.sub(r"<g class='(?:p\d+-)?videolink' data-video='([^']+)'>", vid, s)
    s = re.sub(r'<svg\b', '<svg class="page" preserveAspectRatio="none"', s, count=1)
    frames.append(f'<section class="frame" id="f{i}">{s}</section>')

defs = ''.join(shared.values())
templates = ''.join(f'<template id="v{k}"><video controls playsinline src="data:video/mp4;base64,'
                    f'{base64.b64encode(open(path, "rb").read()).decode()}"></video></template>'
                    for path, k in videos.items())
page = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
html, body {{ margin: 0; height: 100%; background: #fff; overflow: hidden }}
#deck {{ position: absolute; inset: 0; display: flex; align-items: center; justify-content: center }}
.frame {{ display: none; position: relative; aspect-ratio: {W} / {H}; width: min(100vw, 100vh * {W} / {H}) }}
.frame.on {{ display: block }}
.frame > svg.page {{ position: absolute; inset: 0; width: 100%; height: 100% }}
{''.join(fonts.values())}
</style></head><body>
<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>{defs}</defs></svg>
{templates}
<main id="deck">
{chr(10).join(frames)}
</main>
<script>
function playVideo(g) {{
  // the video lies over the poster, in % of the frame so that it follows any resize
  const f = g.closest('.frame'), fr = f.getBoundingClientRect(), r = g.getBoundingClientRect();
  const v = document.getElementById(g.dataset.video).content.firstElementChild.cloneNode(true);
  Object.assign(v.style, {{ position: 'absolute', left: (r.left - fr.left) / fr.width * 100 + '%',
    top: (r.top - fr.top) / fr.height * 100 + '%', width: r.width / fr.width * 100 + '%',
    height: r.height / fr.height * 100 + '%', objectFit: 'contain', background: '#000' }});
  g.style.visibility = 'hidden'; f.append(v); v.play();
}}
(() => {{
  const fr = [...document.querySelectorAll('.frame')];
  let cur = 0;
  function show(k) {{
    cur = Math.max(0, Math.min(fr.length - 1, k));
    fr.forEach((f, j) => f.classList.toggle('on', j === cur));
    if (location.hash !== '#' + (cur + 1)) history.replaceState(null, '', '#' + (cur + 1));
  }}
  const fromHash = () => show((parseInt(location.hash.slice(1), 10) || 1) - 1);
  addEventListener('hashchange', fromHash);
  addEventListener('keydown', e => {{
    if (['ArrowRight', 'PageDown', ' '].includes(e.key)) show(cur + 1);
    else if (['ArrowLeft', 'PageUp'].includes(e.key)) show(cur - 1);
    else if (e.key === 'Home') show(0);
    else if (e.key === 'End') show(fr.length - 1);
    else if (e.key === 'f') document.documentElement.requestFullscreen?.();
    else return;
    e.preventDefault();
  }});
  if (parent !== window) parent.postMessage({{ type: 'deck-size', width: {W}, height: {H} }}, '*');
  fromHash();
}})();
</script>
</body></html>
'''
open(out, 'w', encoding='utf-8').write(page)
print(f'{n} pages, {len(shared)} shared picture(s), {len(fonts)} font subset(s), {len(page) // 1024} KB')
