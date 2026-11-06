#!/usr/bin/env python3
"""Scoped alphaTab 1.8.4 engraving fixes, after the existing TAB tie patch.

This edits glyph layout only. No score flags or playback events are changed.
The minified anchors intentionally fail closed on an upstream upgrade.
"""
import argparse
from pathlib import Path
from patch_alphatab_tab_ties import patch as patch_ties

ROOT = Path(__file__).resolve().parents[1]
PATCHES = [
    # Standard multi-voice rests need the nearest free staff-space position.
    # The upstream voice-index rule always pushes voice 3+ below the staff.
    # Register only the final position, including first-voice rests; hidden
    # duplicate rests must not create phantom occupied areas.
    ('applyRestCollisionOffset(t,e,s){if(t.voice.index>0&&this.reservedLayoutAreasByDisplayTime.has(t.playbackStart)){'
     'const i=Go.computeLineHeightsForRest(t.duration).map(t=>t*s),n=e-i[0],r=e+i[1];let a=n;'
     'const h=this.reservedLayoutAreasByDisplayTime.get(t.playbackStart);let o=!1;'
     'for(const t of h.slots)if(n>=t.topY&&n<=t.bottomY||r>=t.topY&&r<=t.bottomY){o=!0;break}'
     'if(o){a=1===t.voice.index?h.topY-i[1]-i[0]:h.bottomY;const e=a+i[0]+i[1],r=2*s,'
     'o=Math.ceil(Math.abs(a-n)/r);return h.addSlot(a,e),a<n?o*-r:o*r}}return 0}',
     'applyRestCollisionOffset(t,e,s){'
     'const i=this.restDurationsByDisplayTime.get(t.displayStart)?.get(t.playbackDuration);'
     'if(void 0!==i&&i!==t.id)return 0;'
     'const n=Go.computeLineHeightsForRest(t.duration).map(t=>t*s),r=e-n[0],a=e+n[1],'
     'h=this.reservedLayoutAreasByDisplayTime.get(t.displayStart)?.slots??[],o=s/2,l=2*s,c=[0];'
     'for(const t of h)c.push(Math.floor((t.topY-a-o)/l)*l,Math.ceil((t.bottomY-r+o)/l)*l);'
     'c.sort((e,s)=>Math.abs(e)-Math.abs(s)||(t.voice.index<2?e-s:s-e));'
     'const u=c.find(t=>h.every(e=>r+t>=e.bottomY+o||a+t<=e.topY-o))??0;'
     'return this.reserveBeatSlot(t,r+u,a+u),u}'),
    # Whole/breve notes have no stem. Do not reserve imaginary stems through
    # the middle of the staff when placing other voices' valid rests.
    ('i===Fe.Up?(e=this.getHighestNoteY(Xo.TopWithStem)-n,s=this.getLowestNoteY(Xo.Bottom)):',
     'this.container.beat.duration<w.Half?(e=this.getHighestNoteY(Xo.Top),s=this.getLowestNoteY(Xo.Bottom)):'
     'i===Fe.Up?(e=this.getHighestNoteY(Xo.TopWithStem)-n,s=this.getLowestNoteY(Xo.Bottom)):'),
    # Collision reservation runs before glyph.doLayout populates height. Use
    # the chosen SMuFL head's real metrics, including custom/grace noteheads.
    ('case Xo.Top:s-=t.height/2;break;case Xo.Center:break;case Xo.Bottom:s+=t.height/2;',
     'case Xo.Top:s-=(t.height||i.smuflMetrics.glyphHeights.get(t.symbol)*n)/2;break;'
     'case Xo.Center:break;case Xo.Bottom:s+=(t.height||i.smuflMetrics.glyphHeights.get(t.symbol)*n)/2;'),
    ('if(0===this.container.beat.voice.index){const e=Go.computeLineHeightsForRest(this.container.beat.duration),'
     'i=s.y-t.getScoreHeight(e[0]),n=s.y+t.getScoreHeight(e[1]);'
     'this.renderer.collisionHelper.reserveBeatSlot(this.container.beat,i,n)}'
     'else this.renderer.collisionHelper.registerRest(this.container.beat);',
     '{this.renderer.collisionHelper.registerRest(this.container.beat);}'),
    # After rest avoidance, report the same shifted bounds that paint uses.
    ('this.restGlyph&&(t=this.restGlyph.getBoundingBoxTop()),this.wT',
     'this.restGlyph&&(t=this.y+this.restGlyph.getBoundingBoxTop()),this.wT'),
    ('this.restGlyph&&(t=this.restGlyph.getBoundingBoxBottom()),this.wT',
     'this.restGlyph&&(t=this.y+this.restGlyph.getBoundingBoxBottom()),this.wT'),
    ('t.has(this.container.beat.playbackStart)&&t.get(this.container.beat.playbackStart).has(this.container.beat.playbackDuration)'
     '&&t.get(this.container.beat.playbackStart).get(this.container.beat.playbackDuration)!==this.container.beat.id',
     't.has(this.container.beat.displayStart)&&t.get(this.container.beat.displayStart).has(this.container.beat.playbackDuration)'
     '&&t.get(this.container.beat.displayStart).get(this.container.beat.playbackDuration)!==this.container.beat.id'),
    # A silent full-bar voice is redundant when another voice contains notes.
    # Keep all model beats and containers: audio, timing and hit testing still
    # use the original voices. The final shared-view patch below extends the
    # merged TAB rule to standard notation, as confirmed by the user.
    ('sl=class extends el{onTimeX=0;middleX=0;stemX=0}',
     'sl=class extends el{onTimeX=0;middleX=0;stemX=0;'
     'get hideFullBarRest(){const t=this.container.beat;'
     'return t.isFullBarRest&&t.voice.bar.voices.some(e=>e!==t.voice'
     '&&e.beats.some(t=>!t.isEmpty&&!t.isRest))}'
     'get hideTabRest(){const t=this.container.beat;'
     'if(!t.isRest||!this.renderer.showRests)return!1;'
     'return t.voice.bar.voices.some(e=>e!==t.voice&&e.beats.some(s=>!s.isEmpty&&('
     '!s.isRest&&s.displayStart<t.displayStart+t.displayDuration'
     '&&s.displayStart+s.displayDuration>t.displayStart'
     '||s.isRest&&e.index<t.voice.index&&s.displayStart===t.displayStart'
     '&&s.displayDuration===t.displayDuration&&s.duration===t.duration&&s.dots===t.dots)))}}'),
    ('this.container.beat.isEmpty||(this.container.beat.isRest?this.kT():this.ST())',
     'this.container.beat.isEmpty||this.hideFullBarRest||'
     '(this.container.beat.isRest?this.kT():this.ST())'),
    # Standard augmentation dots belong in staff spaces, including notes which
    # sit on a staff/ledger line. TAB rhythm dots keep their own stem anchors.
    ('_T(t,e){const s=this.renderer,i=new tl(0,s.getScoreY(t));',
     '_T(t,e){const s=this.renderer,i=new tl(0,s.getScoreY(t%2===0?t-1:t));'),
    # TAB merges simultaneous voices. One shared rhythmic value needs one dot
    # group, including a real two-dot group; different durations stay distinct.
    ('if(this.container.beat.dots>0&&t.rhythmMode!==C.Hidden){',
     'if(this.container.beat.dots>0&&t.rhythmMode!==C.Hidden'
     '&&!this.container.beat.voice.bar.voices.some(e=>e.index<this.container.beat.voice.index'
     '&&e.beats.some(e=>!e.isRest&&!e.isEmpty&&e.notes.some(t=>t.isVisible)'
     '&&e.displayStart===this.container.beat.displayStart'
     '&&e.displayDuration===this.container.beat.displayDuration'
     '&&e.duration===this.container.beat.duration&&e.dots===this.container.beat.dots))){'),
    # Seat short-note dots just above the beams of their own beat, beside the
    # stem. A neighbour's extra beams end at its stem and do not reach the dot.
    # Flags curl into that spot, so they keep their x. Only paint coordinates
    # move; the dot's layout width stays reserved.
    ('calculateOverflows(t,e){super.calculateOverflows(t,e),this.bar.isEmpty||'
     'this.rhythmMode!==C.Hidden&&this.calculateBeamingOverflows(t,e)}',
     'calculateOverflows(t,e){super.calculateOverflows(t,e);'
     'if(!this.bar.isEmpty&&this.rhythmMode!==C.Hidden){this.calculateBeamingOverflows(t,e);'
     'for(const t of this.helpers.beamHelpers)for(const e of t)for(const s of e.beats){'
     'if(s.isRest||!s.dots||s.duration<w.Eighth)continue;'
     'const i=this.getBeatContainer(s),n=i?.onNotes,'
     'dots=(n?.glyphs??[]).filter(t=>t.symbol===xt.AugmentationDot);'
     'if(!dots.length)continue;'
     'const space=this.smuflMetrics.oneStaffSpace,a=e.graceType!==y.None?.75:1,'
     'origin=this.beatGlyphsStart+i.x+n.x;'
     'if(!this.drawBeamHelperAsFlags(e)){'
     'const t=this.getBeatX(s,Ua.Stem)+this.smuflMetrics.stemThickness+.4*space-origin-dots[0].x;'
     'for(const e of dots)e.x+=t}'
     'const r=Math.max(1,Math.log2(s.duration)-2);'
     'for(const t of dots){'
     'const h=this.calculateBeamY(e,origin+t.x)'
     '-(this.beamThickness+(r-1)*(this.beamSpacing+this.beamThickness))*a;'
     't.y=h-space*.5-(t.getBoundingBoxBottom()-t.y);'
     'this.registerOverflowTop(-t.getBoundingBoxTop())}}}}'),
    # Reserve two staff spaces between lyrics and TAB. In TAB-only the margin
    # precedes the text below the rhythm; in Both it follows the text above TAB.
    # Include it in glyph height so system layout and lazy tiles reserve it.
    ('e.font=this.font;let s=0;for(const i of this.Bk){',
     'e.font=this.font;const i=this.renderer.bar.staff,'
     'n=i.showTablature?this.renderer.smuflMetrics.oneStaffSpace*2:0;'
     'let s=i.showStandardNotation?0:n;for(const i of this.Bk){'),
    ('s-=t,this.height=s}paint(t,e,s){s.font=this.font;',
     's-=t,this.height=s+(i.showStandardNotation?n:0)}paint(t,e,s){s.font=this.font;'),
    # Text effects normally do not enter horizontal spacing. Reserve the actual
    # marker glyph width in its first beat spring before system breaking.
    ('let s=this.postBeatStretch;for(const t of this.nw)s+=t.width;',
     'let s=this.postBeatStretch;'
     'const markerBand=this.renderer.topEffects.getBand(this.beat.voice,A.EffectMarker.toString()),'
     'markerGlyph=markerBand?.rS[this.beat.voice.index]?.get(this.beat.index);'
     'if(markerGlyph)s=Math.max(s,markerGlyph.width-e+8);'
     'for(const t of this.nw)s+=t.width;'),
    # A requested fixed bar count must not squeeze a visible marker out of its
    # system. Keep automatic wrapping scoped to systems containing a marker.
    ('-1===i&&s.width>=n&&0!==s.masterBarsRenderers.length',
     '(-1===i||s.masterBarsRenderers.some(t=>t.renderers.some(t=>t.bar.masterBar.section)))'
     '&&s.width>=n&&s.masterBarsRenderers.length>1'),
    # Fixed-count systems with sections also need reflow after a width change.
    ('G_(t,e){const s=this.getBarsPerSystem(0)>0;',
     'G_(t,e){const s=this.getBarsPerSystem(0)>0&&!this.renderer.score.masterBars.some(t=>t.section);'),
    ('s++,this.U_(s)&&(n.isFull=!0);else{for(;r&&!r.canWrap',
     's++,(this.U_(s)||(this.getBarsPerSystem(n.index)>0&&n.masterBarsRenderers.length>=this.getBarsPerSystem(n.index)))'
     '&&(n.isFull=!0);else{for(;r&&!r.canWrap'),
    # Muted+slash must reach the per-note X glyphs, including mixed chords.
    ('if(s.renderer=this.renderer,this.container.beat.slashed){',
     'if(s.renderer=this.renderer,this.container.beat.slashed&&!this.container.beat.notes.some(t=>t.isDead)){'),
    ('t.beat.slashed&&(t=t.beat.notes[0])',
     't.beat.slashed&&!t.beat.notes.some(t=>t.isDead)&&(t=t.beat.notes[0])', 2),
    ('if(this.container.beat.slashed&&(!this.container.beat.notes.some(t=>t.isTieDestination)',
     'if(this.container.beat.slashed&&!this.container.beat.notes.some(t=>t.isDead)&&(!this.container.beat.notes.some(t=>t.isTieDestination)'),
    ('&&this.startNote.beat.slashed&&this.endNote.beat.slashed)return Fe.Down;',
     '&&this.startNote.beat.slashed&&this.endNote.beat.slashed'
     '&&!this.startNote.beat.notes.some(t=>t.isDead)'
     '&&!this.endNote.beat.notes.some(t=>t.isDead))return Fe.Down;'),
    # An effect starting at the same beat as the prior effect still occupies
    # space: allocate another row instead of sharing the baseline.
    ('this.shared.lastBeat===t.firstBeat||',
     'this.shared.lastBeat!==t.firstBeat&&'),
    # Preserve TAB simile beat containers for hit testing, but do not paint the
    # placeholder empty beat as a quarter rest over the bar-level repeat sign.
    ('doLayout(){const t=this.renderer,e=[];if(this.container.beat.isRest){',
     'doLayout(){if(this.renderer.showTiedNotes&&this.renderer.bar.simileMark!==H.None)return;'
     'const t=this.renderer,e=[];if(this.container.beat.isRest){'),
    ('const t=this.renderer,e=[];if(this.container.beat.isRest){',
     'if(this.hideFullBarRest||this.hideTabRest)return;'
     'const t=this.renderer,e=[];if(this.container.beat.isRest){'),
    # TAB-only labels under downwards slurs must clear the rhythm beams. The
    # slur itself keeps its anchors. Include the text in overflow calculation.
    ('constructor(t,e,s,i,n){super(t,e,s,n),this.mx=i}getTieHeight(t,e,s,i){',
     'constructor(t,e,s,i,n){super(t,e,s,n),this.mx=i}'
     'doLayout(){super.doLayout();'
     'if(this.renderer.showTiedNotes&&this.renderer.rhythmMode!==C.Hidden'
     '&&this.tieDirection===Fe.Down&&this.NS>0){'
     'const t=this.lookupStartBeatRenderer(),e=this.lookupEndBeatRenderer(),'
     's=this.renderer.smuflMetrics.oneStaffSpace*.5;'
     'let i=t.y+t.height+t.settings.notation.rhythmHeight+s;'
     'if(e&&e.staff===t.staff)i=Math.max(i,e.y+e.height+e.settings.notation.rhythmHeight+s);'
     'let n=this.TS.y+this.TS.h;'
     'for(let t=0;t<this.NS;t++){const e=this.vS[t];'
     'e.y=Math.max(e.y+this.PS,i);'
     'n=Math.max(n,e.y+this.renderer.resources.getFontForNotationElement(e.element).size+s)}'
     'this.PS=0;this.TS.h=n-this.TS.y;this.height=this.TS.h}}'
     'getTieHeight(t,e,s,i){'),
    # F1 TAB number displacement was rejected and reverted by the user.
    # Keep the upstream string/fret glyph positions; do not reassign strings.
    # F2: a slash chord has one visible head, so its augmentation dot group
    # must use that head's staff position, not the original chord's pitches.
    ('for(const s of this.container.beat.notes)if(s.isVisible){this._T(t.getNoteSteps(s),e).colorOverride=Kh.noteColor(t.resources,Et.StandardNotationEffects,s)}',
     'for(const s of this.container.beat.notes)if(s.isVisible){'
     'const slash=this.container.beat.slashed&&!this.container.beat.notes.some(n=>n.isDead);'
     'this._T(slash?t.heightLineCount-1:t.getNoteSteps(s),e).colorOverride=Kh.noteColor(t.resources,Et.StandardNotationEffects,s);'
     'if(slash)break;}'),
    # F3: mixed dead/slash beats paint real X heads. They must not enter the
    # later slash-specific beam override that would move beams through them.
    ('t.slashed&&this.slashBeats.push(t)',
     't.slashed&&!t.notes.some(n=>n.isDead)&&this.slashBeats.push(t)'),
    # Other slash beats in the same helper can still override the whole beam.
    # Finish against every visible X chord, including secondary beam levels.
    ('}Fe.Up,s.startY=Math.round(s.startY),s.endY=Math.round(s.endY)}applyBarShift(',
     '}if(this.getScoreY&&t.beats.some(b=>b.slashed&&b.notes.some(n=>n.isDead))){'
     'const depth=this.beamThickness+Math.max(0,i-1)*(this.beamSpacing+this.beamThickness),'
     'gap=this.smuflMetrics.oneStaffSpace*.5;'
     'for(const beat of t.beats){if(!beat.notes.some(n=>n.isDead))continue;'
     'const current=s.calcY(this.getBeatX(beat,Ua.Stem));'
     'if(e===Fe.Up){const limit=Math.min(this.getFlagTopY(beat,e),this.voiceContainer.getHighestNoteY(beat,Xo.Top)-gap-depth);'
     'const delta=Math.min(0,limit-current);s.startY+=delta;s.endY+=delta;}'
     'else{const limit=Math.max(this.getFlagBottomY(beat,e),this.voiceContainer.getLowestNoteY(beat,Xo.Bottom)+gap+depth);'
     'const delta=Math.max(0,limit-current);s.startY+=delta;s.endY+=delta;}}}'
     'Fe.Up,s.startY=Math.round(s.startY),s.endY=Math.round(s.endY)}applyBarShift('),
    # F4: different text kinds need independent rows even if their start/end
    # beats do not overlap. Their visible text may extend past those beats.
    ('canBeUsed(t){return!((this.shared.uniqueEffectId||!t.info.canShareBand)',
     'canBeUsed(t){if(this.bands.some(b=>b.info.notationElement!==t.info.notationElement))return!1;'
     'return!((this.shared.uniqueEffectId||!t.info.canShareBand)'),
    # The measured text height does not include a safe ink gap. Reserve one
    # on either side of an effect stack and between its independent rows.
    ('mS(t){if(!this.fS)return!1;let e=0;const s=this.Nw.settings.display.effectBandPaddingBottom;',
     'mS(t){if(!this.fS)return!1;'
     'const s=Math.max(this.Nw.settings.display.effectBandPaddingBottom,this.Nw.smuflMetrics.oneStaffSpace*.75);'
     'let e=this.fS.slots.length?s:0;'),
    # F5: reserve the upper lyric margin in standard and combined views too.
    # Combined view retains the lower TAB margin added by the earlier patch.
    ('let s=i.showStandardNotation?0:n;for(const i of this.Bk){',
     'let s=this.renderer.smuflMetrics.oneStaffSpace*2;for(const i of this.Bk){'),
    # F6: the first grace note following a rest needs its own left clearance.
    # Add it to the spring before breaking systems, not a paint-only offset.
    ('const e=this.preNotes.computedWidth+this.onNotes.onTimeX;let s=this.postBeatStretch;',
     'const e=this.preNotes.computedWidth+this.onNotes.onTimeX+'
     '(this.beat.graceType!==y.None&&this.beat.graceIndex===0&&this.beat.previousBeat?.isRest?'
     'this.renderer.smuflMetrics.oneStaffSpace*1.5:0);let s=this.postBeatStretch;'),
    # Q1: do not repeatedly label silent bars with a propagated LetRing flag.
    # Original note flags and the model's sustain/continuation remain intact.
    ('shouldCreateGlyph(t,e){return e.isLetRing}',
     'shouldCreateGlyph(t,e){return e.isLetRing&&!e.isRest&&!e.isEmpty}'),
    # Q2: unpitched percussion staves do not need a key signature glyph.
    ('YT(){let e=0;const s=this.bar.keySignature,',
     'YT(){if(this.bar.staff.isPercussion)return;let e=0;const s=this.bar.keySignature,'),
    # All three reading modes merge rests. A rest covered by another voice's
    # note must not imply collective silence. Keep musical beats and timing;
    # the same shared predicate also deduplicates identical common rests.
    ('get hideTabRest(){const t=this.container.beat;'
     'if(!t.isRest||!this.renderer.showRests)return!1;',
     'get hideMergedRest(){const t=this.container.beat;'
     'if(!t.isRest)return!1;'),
    ('this.container.beat.isEmpty||this.hideFullBarRest||'
     '(this.container.beat.isRest?this.kT():this.ST())',
     'this.container.beat.isEmpty||this.hideFullBarRest||this.hideMergedRest||'
     '(this.container.beat.isRest?this.kT():this.ST())'),
    ('if(this.hideFullBarRest||this.hideTabRest)return;',
     'if(this.hideFullBarRest||this.hideMergedRest)return;'),
]


def patch(source):
    # Restore this layer first so the earlier tie patch can verify its own
    # anchors. Reapplying the complete patch remains deterministic.
    for entry in reversed(PATCHES):
        before, after = entry[:2]
        count = entry[2] if len(entry) > 2 else 1
        if source.count(after) == count:
            source = source.replace(after, before)
    source = patch_ties(source)
    for entry in PATCHES:
        before, after = entry[:2]
        count = entry[2] if len(entry) > 2 else 1
        if source.count(after) == count:
            continue
        if source.count(before) != count:
            raise ValueError('alphaTab notation anchor missing or ambiguous: ' + before)
        source = source.replace(before, after)
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
        if source != updated:
            raise SystemExit('Notation patches are missing')
    elif source != updated:
        args.bundle.write_text(updated)
    print('alphaTab notation patches: present' if args.check else 'alphaTab notation patches: applied')


if __name__ == '__main__':
    main()
