<script setup lang="ts">
// Slide 5: most of the teacher is its dictionary, and we only need four of its languages.
// Read on 2026-11-10 from the safetensors header and config of
// fastino/gliner2-privacy-filter-PII-multi at commit 1cb4166 (docs/smart-goals.md):
// 307.1M parameters in float32.
//   dictionary (word embeddings)  250,112 tokens = 192.1M (63 %)
//   the rest: encoder 85.5M + GLiNER2 heads 29.5M = 115.0M
// The 103,718 French, German, Italian and English texts of OpenPII-1M's validation split use
// 77,347 of the 250,112 tokens (30.9 %, docs/baselines.md). Pruned to them, the dictionary
// keeps 59.4M parameters, a lower bound, and the teacher about 174M (an estimate). Pruning is
// an option if time allows (docs/smart-goals.md).
//   0  the teacher as one bar to scale: the dictionary and the rest
//   1  the dictionary opens below as slices of languages; the split per language is an
//      illustration, only the total of our four is measured
//   2  our four languages stay, the others fade: 77,347 of 250,112 tokens
//   3  the other tokens go: both bars shrink to scale, the teacher to about 174M
import { useBeats, inOutCubic, linear, type Channels, type Seg } from './lib/beats'

const W = 1136
const GAP = 3
const TOTAL = 307.1
const EMB = 192.1
const REST = 115.0
const PRUNED = 59.4
const TOKENS = 250112
const KEPT = 77347
const pA = (m: number) => (W * m) / TOTAL
const EMB_W = pA(EMB)
const REST_W = pA(REST)
const PRUNED_W = pA(PRUNED)

// the dictionary, opened: the slices of our four languages are to scale together
const FOUR = ['French', 'German', 'Italian', 'English']
const FOUR_W = (W * KEPT) / TOKENS
const SLICE = FOUR_W / FOUR.length
const OTHERS = 9
const OTHER_W = (W - FOUR_W) / OTHERS
const share = Math.round((100 * KEPT) / TOKENS)

function target(n: number): Channels {
  return {
    zoom: n >= 1 ? 1 : 0,
    slices: n >= 1 ? 1 : 0,
    langs: n >= 1 ? 1 : 0,
    keep: n >= 2 ? 1 : 0,
    brace: n >= 2 ? 1 : 0,
    note1: n >= 2 ? 1 : 0,
    cut: n >= 3 ? 1 : 0,
    note2: n >= 3 ? 1 : 0,
  }
}
const beats: Record<number, Seg[]> = {
  1: [
    { k: 'zoom', to: 1, at: 0, dur: 520, ease: inOutCubic },
    { k: 'slices', to: 1, at: 160, dur: 900, ease: linear },
    { k: 'langs', to: 1, at: 520, dur: 420 },
  ],
  2: [
    { k: 'keep', to: 1, at: 0, dur: 480 },
    { k: 'brace', to: 1, at: 280, dur: 420 },
    { k: 'note1', to: 1, at: 520, dur: 420 },
  ],
  3: [
    { k: 'cut', to: 1, at: 0, dur: 1150, ease: inOutCubic },
    { k: 'note2', to: 1, at: 950, dur: 420 },
  ],
}
const { ch, fade } = useBeats({ target, beats })

const clamp01 = (v: number) => Math.max(0, Math.min(1, v))
const vis = (v: number) => ({ opacity: v, visibility: v > 0.001 ? ('visible' as const) : ('hidden' as const) })
const rise = (v: number) => ({ ...vis(v), transform: `translateY(${(1 - v) * 8}px)` })
// a text that gives way to another in the middle of the cut
const before = () => vis(clamp01(1 - ch.cut * 2))
const after = () => vis(clamp01(ch.cut * 2 - 1))

// the teacher bar: the dictionary shrinks, the rest follows it
const dictW = () => EMB_W - (EMB_W - PRUNED_W) * ch.cut
// the opened dictionary: the other slices close up
const otherW = () => OTHER_W * (1 - ch.cut)
const barBW = () => FOUR_W + (W - FOUR_W) * (1 - ch.cut)
// slices appear one after the other, from the left
const N_SLICES = FOUR.length + OTHERS
const sliceIn = (i: number) => clamp01((ch.slices - (i / (N_SLICES - 1)) * 0.55) / 0.45)

const Y_TOP = 0
const Y_BOT = 54
const zoomPath = () => `M 0 ${Y_TOP} L ${dictW() - GAP} ${Y_TOP} L ${barBW() - GAP} ${Y_BOT} L 0 ${Y_BOT} Z`
</script>

<template>
  <div class="dict" :style="{ opacity: fade }">
    <!-- the teacher, in parameters -->
    <div class="head">
      <span class="swap" :style="before()">The teacher: <span class="figure-num">307M</span> parameters</span>
      <span class="swap" :style="after()">With our four languages: about <span class="figure-num">174M</span>, an estimate</span>
    </div>

    <div class="labels">
      <span class="lab" :style="{ left: 0 }">
        <span class="l1">
          <span class="swap" :style="before()">Dictionary (word embeddings)</span>
          <span class="swap" :style="after()">Dictionary</span>
        </span>
        <span class="l2">
          <span class="swap" :style="before()"><span class="figure-num">192M</span>, <span class="figure-num">63 %</span></span>
          <span class="swap" :style="after()"><span class="figure-num">59M</span> or more</span>
        </span>
      </span>
      <span class="lab" :style="{ left: dictW() + 'px' }">
        <span class="l1"><span class="swap">The rest of the model</span></span>
        <span class="l2"><span class="swap"><span class="figure-num">115M</span></span></span>
      </span>
    </div>

    <div class="bar bar-a">
      <div class="ghost" :style="{ width: W + 'px', opacity: ch.cut }" />
      <span class="ghost-lab" :style="after()"><span>Today: <span class="figure-num">307M</span>, dictionary <span class="figure-num">192M</span></span></span>
      <div class="seg emb" :style="{ left: 0, width: dictW() - GAP + 'px' }" />
      <div class="seg rest" :style="{ left: dictW() + 'px', width: REST_W + 'px' }" />
    </div>

    <!-- the dictionary, opened -->
    <div class="zoom">
      <svg :width="W" :height="Y_BOT" class="zoom-svg" aria-hidden="true">
        <path :d="zoomPath()" class="zoom-fill" :style="{ opacity: ch.zoom }" />
        <line x1="0" :y1="Y_TOP" x2="0" :y2="Y_BOT" pathLength="1" class="zoom-line" :style="{ strokeDashoffset: 1 - ch.zoom }" />
        <line :x1="dictW() - GAP" :y1="Y_TOP" :x2="barBW() - GAP" :y2="Y_BOT" pathLength="1" class="zoom-line" :style="{ strokeDashoffset: 1 - ch.zoom }" />
      </svg>
      <span class="ztitle" :style="vis(ch.zoom)">
        <span class="swap" :style="before()">The dictionary: <span class="figure-num">250,112</span> tokens</span>
        <span class="swap" :style="after()">The smaller dictionary</span>
      </span>
    </div>

    <div class="bar bar-b">
      <div
        v-for="(l, i) in FOUR"
        :key="l"
        class="seg slice"
        :style="{ left: i * SLICE + 'px', width: SLICE - 2 + 'px', opacity: sliceIn(i) }"
      />
      <div
        v-for="j in OTHERS"
        :key="'o' + j"
        class="seg slice"
        :style="{
          left: FOUR_W + (j - 1) * otherW() + 'px',
          width: Math.max(0, otherW() - 2) + 'px',
          opacity: sliceIn(FOUR.length + j - 1) * (1 - 0.86 * ch.keep),
        }"
      />
    </div>

    <div class="langs">
      <span v-for="(l, i) in FOUR" :key="l" class="lang" :style="{ left: i * SLICE + 'px', width: SLICE + 'px', ...vis(ch.langs) }">{{ l }}</span>
      <span class="lang other" :class="{ faded: ch.keep > 0.5 }" :style="{ left: FOUR_W + 'px', width: W - FOUR_W + 'px', ...vis(ch.langs * (1 - ch.cut)) }">Other languages</span>
    </div>

    <div class="brace">
      <svg :width="FOUR_W" height="10" aria-hidden="true" :style="vis(ch.brace)">
        <path :d="`M 1 0 V 7 H ${FOUR_W - 3} V 0`" class="brace-line" />
      </svg>
      <span class="brace-text" :style="vis(ch.brace)"><span class="figure-num">77,347</span> of <span class="figure-num">250,112</span> tokens: <span class="figure-num">{{ share }} %</span></span>
      <span class="eyebrow illus" :style="vis(ch.langs)">Illustration: one token can serve several languages</span>
    </div>

    <div class="notes">
      <p class="note" :style="rise(ch.note1)">Our model targets Switzerland: it needs only four languages.</p>
      <p class="note" :style="rise(ch.note2)">An option if time allows: drop the other tokens.</p>
    </div>
  </div>
</template>

<style scoped>
.dict {
  position: relative;
  width: 1136px;
  margin-top: 26px;
}
.swap {
  position: absolute;
  left: 0;
  top: 0;
  white-space: nowrap;
}

/* the teacher */
.head {
  position: relative;
  height: 40px;
  border-bottom: 1px solid var(--ink);
  font-size: 20px;
  color: var(--muted);
}
.head .swap {
  top: 2px;
}
.head .figure-num {
  font-size: 26px;
  color: var(--ink);
}
.labels {
  position: relative;
  height: 54px;
  margin-top: 14px;
}
.lab {
  position: absolute;
  top: 0;
  padding-left: 2px;
}
.l1,
.l2 {
  position: relative;
  display: block;
  height: 26px;
  font-size: 20px;
}
.l1 {
  color: var(--ink);
}
.l2 {
  color: var(--muted);
}
.l2 .figure-num {
  font-size: 24px;
  color: var(--ink);
}
.bar {
  position: relative;
  height: 38px;
}
.bar-a {
  margin-top: 6px;
}
.seg {
  position: absolute;
  top: 0;
  bottom: 0;
}
.emb {
  background: var(--ink);
}
.rest {
  background: var(--ink);
  opacity: 0.4;
}
/* the teacher today, named inside the frame of its old size */
.ghost-lab {
  position: absolute;
  right: 14px;
  top: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 20px;
  color: var(--muted);
  white-space: nowrap;
}
.ghost-lab .figure-num {
  font-size: 24px;
  color: var(--ink);
}
/* what the cut removes: an empty frame of the old teacher */
.ghost {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  border: 1.5px dashed var(--ink);
}

/* the dictionary, opened */
.zoom {
  position: relative;
  height: 54px;
}
.zoom-svg {
  position: absolute;
  left: 0;
  top: 0;
  overflow: visible;
}
.zoom-fill {
  fill: var(--wash);
}
.zoom-line {
  stroke: var(--ink);
  stroke-width: 1.2;
  stroke-dasharray: 1;
  fill: none;
}
.ztitle {
  position: absolute;
  left: 14px;
  top: 14px;
  height: 26px;
  font-size: 20px;
  color: var(--ink);
}
.ztitle .figure-num {
  font-size: 22px;
}
.slice {
  background: var(--ink);
}
.langs {
  position: relative;
  height: 28px;
  margin-top: 8px;
}
.lang {
  position: absolute;
  top: 0;
  text-align: center;
  font-size: 19px;
  color: var(--ink);
  white-space: nowrap;
}
/* one label for the group, between two rules that span its slices */
.lang.other {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 4px 0 6px;
  transition: color 0.3s;
}
.lang.other::before,
.lang.other::after {
  content: '';
  flex: 1;
  height: 0;
  border-top: 1px solid currentColor;
  opacity: 0.5;
}
.lang.other.faded {
  color: var(--muted-2);
}
.illus {
  position: absolute;
  right: 0;
  top: 19px;
}
.brace {
  position: relative;
  height: 40px;
  margin-top: 4px;
}
.brace svg {
  display: block;
  overflow: visible;
}
.brace-line {
  fill: none;
  stroke: var(--ink);
  stroke-width: 1.5;
}
.brace-text {
  position: absolute;
  left: 2px;
  top: 12px;
  font-size: 20px;
  color: var(--ink);
  white-space: nowrap;
}
.brace-text .figure-num {
  font-size: 22px;
}

/* the two notes */
.notes {
  display: grid;
  grid-template-columns: 1fr 1fr;
  column-gap: 48px;
  margin-top: 18px;
}
.note {
  border-left: 3px solid var(--ink);
  padding: 2px 0 3px 16px;
  font-size: 22px;
  line-height: 1.3;
  color: var(--ink);
}
</style>
