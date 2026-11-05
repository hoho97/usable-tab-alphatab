#!/usr/bin/env python3
"""Reapply the scoped slash/tie renderer fix to the vendored alphaTab 1.8.4.

The existing empty-stem guard stays intact. This does not alter the score model.
Fail closed if a future bundle no longer has the expected minified methods.
"""
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATCHES = [
    (
        # A slash has one visual anchor, independent of the underlying strings.
        'getNoteY(t,e){return this.noteNumbers?this.noteNumbers.getNoteY(t,e):0}',
        'getNoteY(t,e){if(this.slash&&this.renderer.showTiedNotes){'
        'if(e===Xo.Top||e===Xo.StemUp)return this.slash.getBoundingBoxTop();'
        'if(e===Xo.Bottom||e===Xo.StemDown)return this.slash.getBoundingBoxBottom();'
        'if(e===Xo.TopWithStem)return -this.renderer.settings.notation.rhythmHeight;'
        'if(e===Xo.BottomWithStem)return this.renderer.height+this.renderer.settings.notation.rhythmHeight;'
        'if(e===Xo.Center)return this.slash.y}'
        'return this.noteNumbers?this.noteNumbers.getNoteY(t,e):0}',
    ),
    (
        # Fully tied slash chords remain slashes in TAB-only. Mixed ties retain
        # their fret glyphs. Both retains the original destination branch.
        'this.container.beat.slashed&&!this.container.beat.notes.some(t=>t.isTieDestination)',
        'this.container.beat.slashed&&(!this.container.beat.notes.some(t=>t.isTieDestination)'
        '||(this.renderer.showTiedNotes&&this.container.beat.notes.every('
        't=>t.isTieDestination&&t.tieOrigin.beat.slashed)))',
    ),
    (
        # Only ordinary slash-to-slash ties share a direction. Effect slurs,
        # left-hand taps and ordinary fret ties keep their existing direction.
        'calculateTieDirection(){return this.isLeftHandTap?Fe.Up:t.getBeamDirectionForNote(this.startNote)}',
        'calculateTieDirection(){if(this.renderer.showTiedNotes'
        '&&this.slurEffectId==="tab.tie."+this.startNote.id'
        '&&this.startNote.beat.slashed&&this.endNote.beat.slashed)return Fe.Down;'
        'return this.isLeftHandTap?Fe.Up:t.getBeamDirectionForNote(this.startNote)}',
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
            raise SystemExit('TAB slash tie patch is missing')
        print('TAB slash tie patch: present')
    else:
        if updated != source:
            args.bundle.write_text(updated)
        print('TAB slash tie patch: applied')


if __name__ == '__main__':
    main()
