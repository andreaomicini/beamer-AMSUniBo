"""The deck being translated: $TEX2HTML_DECK is its folder of inputs (deck.json, deck.css,
titlepage.html, nudges.json), paths in deck.json relative to the deck's root.
STYLE is what the tools must know of the deck's Beamer style: deck.json's "style", AMSUniBo
when absent."""
import json, os, pathlib

DIR = pathlib.Path(os.environ['TEX2HTML_DECK']).resolve()
CFG = json.load(open(DIR / 'deck.json'))
ROOT = (DIR / CFG.get('root', '../..')).resolve()

def path(key):
    return ROOT / CFG[key]

def rgb(h):
    return tuple(round(int(h[i:i + 2], 16) / 255, 3) for i in (0, 2, 4))

# per style, in pt on 128 mm paper: a block body's bottom padding (theme CSS); the bottom of the headline, of the frame title band, the top
# of the footline; the colour of a \ccite; block title and body fills (block, alert, example);
# the PDF's font names -> the OTF whose outlines depth.py reads
STYLES = {
    'AMSUniBo': dict(
        theme='theme.css', bottom=2.8, head=12.9, title=37.2, foot=262.0, cite=0xc7c9cb,
        titles=[(0.212, 0.408, 0.38), (0.733, 0.18, 0.161), (0.698, 0.843, 0.824)],
        bodies=[(0.867, 0.929, 0.922), (0.965, 0.851, 0.847), (0.882, 0.937, 0.929)],
        faces={'MerriwthrSans-Light': 'MerriweatherSans-Light', 'MerriwthrSans-LightItali': 'MerriweatherSans-LightItalic',
               'MerriwthrSans-Regular': 'MerriweatherSans-Regular', 'MerriwthrSans-Bold': 'MerriweatherSans-Bold',
               'MerriwthrSans-BoldItalic': 'MerriweatherSans-BoldItalic', 'Inconsolatazi4-Regular': 'Inconsolatazi4-Regular'}),
    'AMSBolognaFC': dict(
        theme='theme-AMSBolognaFC.css', bottom=3.58, head=11.1, title=38.92, foot=263.4, cite=0xbdbdbd,
        titles=[rgb('142336'), rgb('091019'), rgb('BAC1C8')],
        bodies=[rgb('FAFBFB'), rgb('F4F5F6'), rgb('EFF0F2')],
        faces={}),
    # AMSBolognaFC's theme and geometry in the old Cesena purple and gold (experiment 5)
    'AMSPurpleAndGold': dict(
        theme='theme-AMSPurpleAndGold.css', bottom=3.58, head=11.1, title=38.92, foot=263.4, cite=0xbeba89,
        titles=[rgb('660066'), rgb('380038'), rgb('D1B2D1')],
        bodies=[rgb('F4EDF4'), rgb('F9F5E5'), rgb('F4EDF4')],
        faces={}),
    # the same again in the old Cesena blue and silver (experiment 6)
    'AMSSilverBlue': dict(
        theme='theme-AMSSilverBlue.css', bottom=3.58, head=11.1, title=38.92, foot=263.4, cite=0xbfbfbf,
        cites=[0xbfbfbf, 0xececec],   # \ccite and \cccite
        titles=[rgb('003F66'), rgb('0073BA'), rgb('DCDCDC')],
        bodies=[rgb('EBF4F9'), rgb('DEEDF6'), rgb('F1F1F1')],
        faces={}),
}
STYLE = STYLES[CFG.get('style', 'AMSUniBo')]
CITES = STYLE.get('cites', [STYLE['cite']])   # the colours of the citation commands

def cm_face(name):
    """a cm-super or CM font name of the PDF -> the Latin Modern OTF with its outlines"""
    import re
    m = re.match(r'(SFSS|SFSI|SFSX|SFSO|SFTT|SFCC)(\d{4})$', name)
    if not m:
        return {'CMSSI10': 'lmsans10-oblique', 'CMMI10': 'lmroman10-italic'}.get(name)
    kind, size = m.group(1), int(m.group(2)) / 100
    if kind in ('SFSX', 'SFSO'):
        return 'lmsans10-bold' if kind == 'SFSX' else 'lmsans10-boldoblique'
    if kind == 'SFTT':
        return 'lmmono%d-regular' % (8 if size < 8.5 else 9 if size < 9.5 else 10 if size < 11.5 else 12)
    if kind == 'SFCC':
        return 'lmromancaps10-regular'
    opt = 8 if size < 8.5 else 9 if size < 9.5 else 10 if size < 11.5 else 12 if size < 15 else 17
    return 'lmsans%d-%s' % (opt, 'regular' if kind == 'SFSS' else 'oblique')
