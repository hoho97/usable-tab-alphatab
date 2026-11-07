#!/usr/bin/env python3
"""Reapply the header line spacing switch to the vendored alphaTab 1.8.4.

alphaTab moves each title, artist and credit line down by exactly its font size, so on a phone the lines touch (#70).
With a number in globalThis.alphaTabHeaderLineSpacing, each line moves down by its font size times that number.
Without it the layout is the upstream one. Fail closed if the bundle changes.
"""
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATCHES = [
    (
        'e.y=i,this.alignScoreInfoGlyph(e);let s=e.font.size;t===bt.Words&&',
        'e.y=i,this.alignScoreInfoGlyph(e);let s=e.font.size*(globalThis.alphaTabHeaderLineSpacing||1);t===bt.Words&&',
    ),
]


def patch(source):
    if 'static version="1.8.4"' not in source:
        raise ValueError('Expected alphaTab 1.8.4; review the patch before upgrading')
    for before, after in PATCHES:
        if source.count(after) == 1:
            continue
        if source.count(before) != 1:
            raise ValueError('alphaTab 1.8.4 patch anchor missing or ambiguous: ' + before)
        source = source.replace(before, after, 1)
    return source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', nargs='?', type=Path,
                        default=ROOT / 'UsableTab/AlphaTabAssets/alphaTab.min.js')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    source = args.bundle.read_text()
    updated = patch(source)
    if args.check:
        if updated != source:
            raise SystemExit('Header line spacing patch is missing')
        print('Header line spacing patch: present')
    else:
        if updated != source:
            args.bundle.write_text(updated)
        print('Header line spacing patch: applied')


if __name__ == '__main__':
    main()
