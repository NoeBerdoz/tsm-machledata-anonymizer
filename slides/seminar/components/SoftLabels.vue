<script setup lang="ts">
// Slide 6: what a soft label is, built one idea per click on one word of one sentence.
//   0  the sentence and the four types: which type is Dupont?
//   1  the issue: the same word is a person, then part of a place (Rue Dupont)
//   2  the hard label: the ground truth says PERSON, 100 %
//   3  the soft labels: the teacher's probability for each type; LOCATION 14 %
//   4  the temperature: the same teacher at tau = 4; the small values grow
// The teacher's scores are made up for the example: z = (4.0, 2.2, 0.6, 0.0) for PERSON,
// LOCATION, ORGANIZATION and NONE. Its probabilities are softmax(z / tau), computed here:
//   tau 1  82.17 / 13.58 / 2.74 / 1.51 %   (shown 82 / 14 / 3 / 2)
//   tau 4  41.10 / 26.21 / 17.57 / 15.12 % (shown 41 / 26 / 18 / 15)
// On click 4 the last column starts from the tau = 1 values and the temperature rises to 4.
import { computed } from 'vue'
import { useBeats, inOutCubic, type Channels, type Seg } from './lib/beats'
import Callout from './Callout.vue'
import Tex from './Tex.vue'

const TYPES = ['PERSON', 'LOCATION', 'ORGANIZATION', 'NONE']
const Z = [4.0, 2.2, 0.6, 0.0]
const TRUTH = [1, 0, 0, 0]
const HOT = 4

function softmax(z: number[], tau: number) {
  const e = z.map((v) => Math.exp(v / tau))
  const s = e.reduce((a, b) => a + b, 0)
  return e.map((v) => v / s)
}
const COOL = softmax(Z, 1)

// ---------- states ----------
function target(n: number): Channels {
  const c: Channels = {
    u: n >= 1 ? 1 : 0, l1: n >= 1 ? 1 : 0, l2: n >= 1 ? 1 : 0,
    gt: n >= 2 ? 1 : 0, gtFill: n >= 2 ? 1 : 0,
    t1: n >= 3 ? 1 : 0, t1Fill: n >= 3 ? 1 : 0, loc: n >= 3 ? 1 : 0,
    t4: n >= 4 ? 1 : 0, tau: n >= 4 ? HOT : 1, tag: n >= 4 ? 1 : 0,
  }
  for (let i = 0; i <= 4; i++) c['c' + i] = i === Math.min(n, 4) ? 1 : 0
  return c
}
// the sentence of the past click leaves, the new one comes in
const swap = (n: number): Seg[] => [
  { k: 'c' + (n - 1), to: 0, at: 0, dur: 180 },
  { k: 'c' + n, to: 1, at: 200, dur: 380 },
]
const beats: Record<number, Seg[]> = {
  1: [
    { k: 'u', to: 1, at: 0, dur: 420, ease: inOutCubic },
    { k: 'l1', to: 1, at: 80, dur: 360 },
    { k: 'l2', to: 1, at: 300, dur: 360 },
    ...swap(1),
  ],
  2: [
    { k: 'gt', to: 1, at: 0, dur: 300 },
    { k: 'gtFill', to: 1, at: 150, dur: 700, ease: inOutCubic },
    ...swap(2),
  ],
  3: [
    { k: 't1', to: 1, at: 0, dur: 300 },
    { k: 't1Fill', to: 1, at: 150, dur: 800, ease: inOutCubic },
    { k: 'loc', to: 1, at: 900, dur: 400 },
    ...swap(3),
  ],
  // the new column starts as a copy of the tau = 1 column, then the temperature rises
  4: [
    { k: 't4', to: 1, at: 0, dur: 280 },
    { k: 'tag', to: 1, at: 0, dur: 280 },
    { k: 'tau', to: HOT, at: 350, dur: 1300, ease: inOutCubic },
    ...swap(4),
  ],
}
const { ch, fade } = useBeats({ target, beats })

// ---------- what each state shows ----------
const hot = computed(() => softmax(Z, ch.tau))
const pct = (v: number) => `${Math.round(v * 100)} %`
const tauText = computed(() => (Math.abs(ch.tau - Math.round(ch.tau)) < 0.005 ? String(Math.round(ch.tau)) : ch.tau.toFixed(1)))
const vis = (v: number) => ({ opacity: v, visibility: v > 0.001 ? ('visible' as const) : ('hidden' as const) })
const rise = (v: number, d = 8) => ({ ...vis(v), transform: `translateY(${(1 - v) * d}px)` })
const bar = (v: number) => ({ transform: `scaleX(${Math.max(0, Math.min(1, v))})` })
</script>

<template>
  <div class="soft" :style="{ opacity: fade }">
    <!-- the sentence, with the word in question -->
    <div class="top">
      <p class="line">
        Send the contract to Mrs
        <span class="w"><span class="val">Dupont</span><span class="tag" :style="rise(ch.l1, 6)">a person</span></span>,
        Rue
        <span class="w">Dupont<span class="u" :style="bar(ch.u)" /><span class="tag" :style="rise(ch.l2, 6)">part of a place</span></span>
        4, Lausanne.
      </p>
      <span class="eyebrow ex">Simplified example, made-up scores</span>
    </div>

    <!-- the table: the type, then one column per target -->
    <div class="tab">
      <div class="row head">
        <span />
        <span class="h" :style="rise(ch.gt)">
          <span class="eyebrow ink">Ground truth</span>
          <span class="form">hard label</span>
        </span>
        <span class="h" :style="rise(ch.t1)">
          <span class="eyebrow ink">The teacher<span class="tau" :style="vis(ch.tag)">, <Tex e="\tau = 1" /></span></span>
          <span class="form">soft labels: a probability for each type</span>
        </span>
        <span class="h" :style="rise(ch.t4)">
          <span class="eyebrow ink">The teacher, <Tex class="tau" :e="`\\tau = ${tauText}`" /></span>
          <span class="form">softer labels</span>
        </span>
      </div>

      <div v-for="(t, i) in TYPES" :key="t" class="row" :style="{ '--lit': i === 1 ? ch.loc : 0 }">
        <span class="mono cname">{{ t }}</span>
        <span class="cell" :style="vis(ch.gt)">
          <span class="track"><span class="fill" :style="bar(TRUTH[i] * ch.gtFill)" /></span>
          <span class="num">{{ pct(TRUTH[i] * ch.gtFill) }}</span>
        </span>
        <span class="cell" :style="vis(ch.t1)">
          <span class="track"><span class="fill" :style="bar(COOL[i] * ch.t1Fill)" /></span>
          <span class="num">{{ pct(COOL[i] * ch.t1Fill) }}</span>
        </span>
        <span class="cell" :style="vis(ch.t4)">
          <span class="track"><span class="fill" :style="bar(hot[i])" /></span>
          <span class="num">{{ pct(hot[i]) }}</span>
        </span>
      </div>
    </div>

    <!-- one sentence per click, in the order the speaker says it -->
    <div class="says">
      <Callout class="note" :style="rise(ch.c0)">Here, each word gets one of these types. Which one is Dupont?</Callout>
      <Callout class="note" :style="rise(ch.c1)">The same word can be a person or part of a place. A model can hesitate.</Callout>
      <Callout class="note" :style="rise(ch.c2)">A hard label gives one answer. It says nothing about the other types.</Callout>
      <Callout class="note" :style="rise(ch.c3)">The teacher's soft labels show its doubt: Dupont might be a place.</Callout>
      <Callout class="note" :style="rise(ch.c4)">
        A higher temperature <Tex e="\tau" /> spreads the probabilities: small ones grow.<br>The student sees the second choices.
      </Callout>
    </div>
  </div>
</template>

<style scoped>
.soft {
  position: relative;
  width: 1136px;
  margin-top: 30px;
}
.ink {
  color: var(--ink);
}

/* the sentence */
.top {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  height: 74px;
}
.line {
  font-size: 28px;
  line-height: 1.25;
}
.w {
  position: relative;
  display: inline-block;
}
.val {
  color: var(--red);
  text-decoration: underline;
  text-decoration-thickness: 1.5px;
  text-underline-offset: 5px;
}
/* the second Dupont: an ink rule drawn under it, as the issue appears */
.u {
  position: absolute;
  left: 0;
  right: 0;
  bottom: -1px;
  height: 1.5px;
  background: var(--ink);
  transform-origin: left center;
}
.tag {
  position: absolute;
  left: 0;
  top: calc(100% + 6px);
  font-size: 18px;
  line-height: 1.2;
  color: var(--muted);
  white-space: nowrap;
}
.ex {
  flex: none;
}

/* the table */
.tab {
  margin-top: 10px;
}
.row {
  display: grid;
  grid-template-columns: 170px 320px 320px 1fr;
  align-items: center;
  height: 44px;
  border-bottom: 1px solid var(--hair);
  background: rgba(22, 22, 22, calc(var(--lit, 0) * 0.06));
}
.row.head {
  height: auto;
  min-height: 74px;
  align-items: start;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--ink);
}
.h {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding-right: 28px;
}
/* one fixed line for each eyebrow, so the math in some of them does not shift the row */
.h > .eyebrow {
  height: 18px;
  line-height: 18px;
  white-space: nowrap;
}
.form {
  font-size: 20px;
  line-height: 1.22;
  color: var(--muted);
}
/* the eyebrows are uppercase: the math in them keeps its own case */
.tau :deep(.katex) {
  font-size: 18px;
  line-height: 1;
  letter-spacing: 0;
  text-transform: none;
  color: var(--ink);
}
.cname {
  padding-left: 8px;
  font-size: 18px;
  color: var(--ink);
}
.cell {
  display: flex;
  align-items: center;
  gap: 14px;
}
.track {
  position: relative;
  width: 210px;
  height: 12px;
  background: var(--wash);
  border-radius: 2px;
}
.fill {
  position: absolute;
  inset: 0;
  transform-origin: left center;
  background: var(--ink);
  border-radius: 2px;
}
.num {
  min-width: 62px;
  font-size: 20px;
  font-variant-numeric: lining-nums tabular-nums;
}

/* the sentence of each click, one at a time */
.says {
  position: relative;
  height: 76px;
  margin-top: 26px;
}
.note {
  position: absolute;
  left: 0;
  top: 0;
  max-width: 1100px;
}
.note :deep(.text) {
  font-size: 24px;
}
.note :deep(.katex) {
  font-size: 1.05em;
}
</style>
