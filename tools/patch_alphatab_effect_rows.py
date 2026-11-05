#!/usr/bin/env python3
"""Reapply the effect-row packing switch to the vendored alphaTab 1.8.4.

alphaTab gives every effect type its own row above or below the staff for a whole system, so a horizontal score,
which is one system, reserves a row for each technique that appears anywhere in the song. With
globalThis.alphaTabPackEffects === true, a band may take any row whose last band ended before it begins, whatever
the effect type. Without the flag the layout is the upstream one. Fail closed if the bundle changes.
"""
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATCHES = [
    (
        'canBeUsed(t){if(this.bands.some(b=>b.info.notationElement!==t.info.notationElement))return!1;'
        'return!((this.shared.uniqueEffectId||!t.info.canShareBand)&&t.info.effectId!==this.shared.uniqueEffectId)'
        '&&(!this.shared.firstBeat||',
        'canBeUsed(t){const p=globalThis.alphaTabPackEffects===!0;'
        'if(!p&&this.bands.some(b=>b.info.notationElement!==t.info.notationElement))return!1;'
        'return(p||!((this.shared.uniqueEffectId||!t.info.canShareBand)&&t.info.effectId!==this.shared.uniqueEffectId))'
        '&&(!this.shared.firstBeat||',
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
            raise SystemExit('Effect row packing patch is missing')
        print('Effect row packing patch: present')
    else:
        if updated != source:
            args.bundle.write_text(updated)
        print('Effect row packing patch: applied')


if __name__ == '__main__':
    main()
