"""The deck being translated: $TEX2HTML_DECK is its folder of inputs (deck.json, deck.css,
titlepage.html, nudges.json), paths in deck.json relative to the deck's root."""
import json, os, pathlib

DIR = pathlib.Path(os.environ['TEX2HTML_DECK']).resolve()
CFG = json.load(open(DIR / 'deck.json'))
ROOT = (DIR / CFG.get('root', '../..')).resolve()

def path(key):
    return ROOT / CFG[key]
