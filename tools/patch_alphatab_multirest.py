#!/usr/bin/env python3
"""Give merged multi-bar rests a cursor position and their bar effects in alphaTab 1.8.4.

Upstream 1.8.4 draws a merged rest group as one glyph without beat bounds or effect
glyphs. The player cursor then has no place to go inside the group, and a tempo change
that starts the group (the grouping breaks there) is never drawn. This adds a beat bound
for the group's first beat over the whole rest glyph, and builds the first voice's effect
glyphs at the start of the group. A lookup that lands inside a group (a seek) plays the
group's first beat. No score or playback data is changed.
Fail closed if a future bundle no longer has the expected minified methods.
"""
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# The inserted code refers to these bundle-local classes: BeatBounds and Bounds.
REQUIRED = [
    'zn=class{barBounds;visualBounds;onNotesX=0;realBounds;beat;',
    '_s=class{x;y;w;h;',
]
PATCHES = [
    (
        # Merged rest glyph: the group's first beat spans from the rest area to the bar end,
        # so the cursor moves across the group for the group's whole duration.
        'buildBoundingsLookup(t,e,s){}doLayout(){this.renderer.showMultiBarRest&&(this.OS=new Ro',
        'buildBoundingsLookup(t,e,s){const n=this.renderer.bar.voices[0]?.beats[0];if(!n)return;'
        'const i=new zn,r=t.realBounds.x+t.realBounds.w-e;i.beat=n;'
        'i.visualBounds=new _s;i.visualBounds.x=e;i.visualBounds.y=t.visualBounds.y;'
        'i.visualBounds.w=r;i.visualBounds.h=t.visualBounds.h;'
        'i.realBounds=new _s;i.realBounds.x=e;i.realBounds.y=t.realBounds.y;'
        'i.realBounds.w=r;i.realBounds.h=t.realBounds.h;i.onNotesX=e;t.addBeat(i)}'
        'doLayout(){this.renderer.showMultiBarRest&&(this.OS=new Ro',
    ),
    (
        # A search without a nearby previous beat (a seek into the group) resolves to a hidden
        # bar of the group; play the group's first beat instead, as the following playback does.
        'n||(n=this.eg(s)),n?this.Ym(t,n,s,i):null}',
        'n||(n=this.eg(s)),n?this.restGroupStart(t,n,s,i):null}'
        'restGroupStart(t,e,s,i){if(this.multiBarRestInfo)for(const[n,r]of this.multiBarRestInfo)'
        'if(r.includes(e.masterBar.index)){for(;e.masterBar.index>n&&e.previousMasterBar;)e=e.previousMasterBar;'
        's=e.start;break}return this.Ym(t,e,s,i)}',
    ),
    (
        # Effects such as tempo on the group's first bar.
        'createBeatGlyphs(){if(this.additionalMultiRestBars){const t=new Oo;this.addBeatGlyph(t)}else',
        'createBeatGlyphs(){if(this.additionalMultiRestBars){const t=new Oo;this.addBeatGlyph(t);'
        'const e=this.bar.voices[0];e&&(this.topEffects.createVoiceGlyphs(e),this.bottomEffects.createVoiceGlyphs(e))}else',
    ),
    (
        # A merged rest has no beat container; its effects align to the start of the rest area.
        'oS(t,e){const s=this.rS[e.voice.index].get(e.index),i=this.renderer.getBeatContainer(e);',
        'oS(t,e){const s=this.rS[e.voice.index].get(e.index),'
        'i=this.renderer.getBeatContainer(e)??{x:0,onTimeX:0,isLastOfVoice:!0};',
    ),
]


def patch(source):
    if 'static version="1.8.4"' not in source:
        raise ValueError('Expected alphaTab 1.8.4; review the patch before upgrading')
    for anchor in REQUIRED:
        if source.count(anchor) != 1:
            raise ValueError('alphaTab 1.8.4 class anchor missing or ambiguous: ' + anchor)
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
            raise SystemExit('Multi-bar rest patch is missing')
        print('Multi-bar rest patch: present')
    else:
        if updated != source:
            args.bundle.write_text(updated)
        print('Multi-bar rest patch: applied')


if __name__ == '__main__':
    main()
