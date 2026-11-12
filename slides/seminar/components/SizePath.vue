<script setup lang="ts">
// Slide 8: the two ways to get an int8 model, then the size path, built one step per click.
//   0  PTQ and QAT side by side. Each has a small timeline: PTQ rounds a trained model once;
//      QAT goes on training with the rounding, which takes a training run
//   1  the two methods leave and the path arrives: the teacher (measured) and int8 with only
//      the tokens of our four languages, against the current goal line, 12 times smaller
//   2  a student with 6 layers
//   3  then the word embeddings in int4, or the rare tokens dropped instead: just under the line
//   4  both: past the line, and the reminder that recall must be measured after each step
// The bars show how many times smaller each step is than the teacher, to scale from zero.
// Sizes and ratios are copied from docs/baselines.md, "The vocabulary of our four languages":
// estimates at 1 byte per parameter in int8 and half a byte in int4, GLiNER2 heads kept,
// tokenizer counted. Only the teacher (1,244 MB, every file) is measured.
import { useBeats, inOutCubic, linear, type Channels, type Seg } from './lib/beats'
import Callout from './Callout.vue'

type Row = { label: string; size: string; x: number; measured?: boolean; pass?: boolean; from: number }
const ROWS: Row[] = [
  { label: 'The teacher, float32, every file', size: '1,244 MB', x: 1, measured: true, from: 1 },
  { label: 'int8, only French, German, Italian, English tokens', size: 'about 179 MB', x: 6.9, from: 1 },
  { label: 'A student with 6 layers instead of 12', size: 'about 137 MB', x: 9.1, from: 2 },
  { label: 'Then word embeddings in int4: half a byte each', size: 'about 107 MB', x: 11.6, from: 3 },
  { label: 'Or drop the tokens seen under 10 times', size: 'about 108 MB', x: 11.6, from: 3 },
  { label: 'Or both', size: 'about 91 MB', x: 13.6, pass: true, from: 4 },
]
const GOAL = 12 // times smaller, O3: 1,244 MB / 12 = about 104 MB

// geometry of the path, in figure coordinates
const TRACK_X = 490
const MAX_X = 14
const PX = 27 // px per "times smaller"
const GOAL_X = TRACK_X + GOAL * PX
const ROW_Y = 72
const ROW_H = 50
const rowTop = (i: number) => ROW_Y + i * ROW_H

// ---------- states ----------
function target(n: number): Channels {
  const c: Channels = {
    a: n === 0 ? 1 : 0, // the two methods
    b: n >= 1 ? 1 : 0, // the path
    goal: n >= 1 ? 1 : 0,
    boxA: 1, arrow: 1, round: 1, qat: 1,
    check: n >= 4 ? 1 : 0,
    note: n >= 4 ? 1 : 0,
    gl: ROWS.filter((r) => n >= r.from).length, // how many rows the goal line crosses
  }
  ROWS.forEach((r, i) => {
    c['r' + i] = n >= r.from ? 1 : 0
    c['g' + i] = n >= r.from ? 1 : 0
  })
  return c
}
const show = (i: number, at: number, dur = 800): Seg[] => [
  { k: 'r' + i, to: 1, at, dur: 280 },
  { k: 'g' + i, to: 1, at: at + 80, dur, ease: inOutCubic },
]
const beats: Record<number, Seg[]> = {
  1: [
    { k: 'a', to: 0, at: 0, dur: 260 },
    { k: 'b', to: 1, at: 250, dur: 300 },
    { k: 'goal', to: 1, at: 260, dur: 300 },
    { k: 'gl', to: 2, at: 260, dur: 520 },
    ...show(0, 260, 360),
    ...show(1, 440, 820),
  ],
  2: [{ k: 'gl', to: 3, at: 0, dur: 280 }, ...show(2, 0)],
  3: [{ k: 'gl', to: 5, at: 0, dur: 580 }, ...show(3, 0), ...show(4, 300)],
  4: [
    { k: 'gl', to: 6, at: 0, dur: 280 },
    ...show(5, 0, 900),
    { k: 'check', to: 1, at: 980, dur: 260 },
    { k: 'note', to: 1, at: 1000, dur: 450 },
  ],
}
const { ch, fade } = useBeats({
  target,
  beats,
  entry: {
    from: { boxA: 0, arrow: 0, round: 0, qat: 0 },
    segs: [
      { k: 'boxA', to: 1, at: 300, dur: 300 },
      { k: 'arrow', to: 1, at: 520, dur: 220 },
      { k: 'round', to: 1, at: 700, dur: 300 },
      { k: 'qat', to: 1, at: 700, dur: 1100, ease: linear },
    ],
  },
})

const clamp01 = (v: number) => Math.max(0, Math.min(1, v))
const on = (v: number) => ({ opacity: v, visibility: v > 0.001 ? ('visible' as const) : ('hidden' as const) })
const rise = (v: number, d = 10) => ({ ...on(v), transform: `translateY(${(1 - v) * d}px)` })
const barW = (i: number) => ROWS[i].x * PX * ch['g' + i]
const val = (i: number) => on(clamp01((ch['g' + i] - 0.7) / 0.3))
</script>

<template>
  <div class="sp" :style="{ opacity: fade }">
    <!-- 0: the two ways to get an int8 model -->
    <div class="methods" :style="on(ch.a)">
      <div class="card">
        <div class="ab">PTQ</div>
        <div class="nm">Post-training quantization</div>
        <svg class="tl" width="498" height="56" viewBox="0 0 500 56" aria-hidden="true">
          <g :style="{ opacity: ch.boxA }">
            <rect x="1" y="6" width="168" height="44" rx="6" class="model" />
            <text x="85" y="34" class="t mid">Trained model</text>
          </g>
          <g :style="{ opacity: ch.arrow }">
            <path d="M 176 28 H 202" class="ar" />
            <path d="M 196 22 L 203 28 L 196 34" class="ar" />
          </g>
          <g :style="{ opacity: ch.round, transformOrigin: '265px 28px', transform: `scale(${0.9 + 0.1 * ch.round})` }">
            <rect x="210" y="6" width="110" height="44" rx="6" class="rnd" />
            <text x="265" y="34" class="t ink mid">Round</text>
          </g>
        </svg>
        <p class="s1">Round a trained model, with no retraining.</p>
        <p class="s2">Static int8 also measures inner value ranges on a few inputs.</p>
      </div>
      <div class="card">
        <div class="ab">QAT</div>
        <div class="nm">Quantization-aware training</div>
        <svg class="tl" width="498" height="56" viewBox="0 0 500 56" aria-hidden="true">
          <g :style="{ opacity: ch.boxA }">
            <rect x="1" y="6" width="168" height="44" rx="6" class="model" />
            <text x="85" y="34" class="t mid">Trained model</text>
          </g>
          <g :style="{ opacity: ch.arrow }">
            <path d="M 176 28 H 202" class="ar" />
            <path d="M 196 22 L 203 28 L 196 34" class="ar" />
          </g>
          <g :style="on(ch.qat > 0.001 ? 1 : 0)">
            <rect x="210" y="6" :width="Math.max(8, 288 * ch.qat)" height="44" rx="6" class="train" />
            <text x="354" y="34" class="t ink mid" :style="{ opacity: clamp01((ch.qat - 0.8) / 0.2) }">Training with rounding</text>
          </g>
        </svg>
        <p class="s1">Train with the rounding, so the model adapts to it.</p>
        <p class="s2">It costs a training run, but it can recover accuracy.</p>
      </div>
    </div>

    <!-- 1 to 4: the size path -->
    <div class="path" :style="on(ch.b)">
      <p class="lede-s">Only the teacher is measured. The rest are estimates.</p>

      <div class="head" :style="{ top: ROW_Y - 26 + 'px' }">
        <span class="eyebrow" style="left: 884px">Smaller</span>
        <span class="eyebrow" style="left: 990px">Size</span>
      </div>
      <p class="goal-l" :style="{ ...on(ch.goal), top: ROW_Y - 34 + 'px', right: 1136 - GOAL_X - 1 + 'px' }">Current goal, O3: {{ GOAL }}x, about 104 MB</p>
      <div class="rule" :style="{ top: ROW_Y + 'px' }" />

      <div v-for="(r, i) in ROWS" :key="r.label" class="row" :style="{ top: rowTop(i) + 'px', ...rise(ch['r' + i], 6) }">
        <span class="lab">{{ r.label }}</span>
        <span class="track" :style="{ left: TRACK_X + 'px', width: MAX_X * PX + 'px' }" />
        <span class="bar" :class="{ measured: r.measured }" :style="{ left: TRACK_X + 'px', width: barW(i) + 'px' }" />
        <span class="times-v" :style="val(i)">
          {{ r.x }}x
          <svg v-if="r.pass" class="tick" width="16" height="16" viewBox="0 0 14 14" aria-hidden="true" :style="{ opacity: ch.check }"><path d="M2 7.6l3.3 3.2L12.2 3.4" /></svg>
        </span>
        <span class="size-v" :style="val(i)">
          <span>{{ r.size }}</span><span v-if="r.measured" class="meas">measured</span>
        </span>
      </div>

      <!-- the goal line, drawn down from its label -->
      <span class="goal" :style="{ left: GOAL_X - 1 + 'px', top: ROW_Y - 8 + 'px', height: rowTop(ch.gl) - ROW_Y + 8 + 'px', opacity: ch.goal }" />

      <Callout class="note" :style="{ top: rowTop(ROWS.length) + 26 + 'px', ...rise(ch.note, 10) }">Recall must be measured after each step.</Callout>
    </div>
  </div>
</template>

<style scoped>
.sp {
  position: relative;
  width: 1136px;
  height: 470px;
  margin-top: 26px;
}
.methods,
.path {
  position: absolute;
  inset: 0;
}

/* ---------- the two methods ---------- */
.methods {
  display: grid;
  grid-template-columns: 1fr 1fr;
  column-gap: var(--gutter);
  align-items: start;
  padding-top: 30px;
}
.card {
  min-width: 0;
  padding: 26px 28px 28px;
  background: var(--card);
  border: 1px solid var(--hair);
  border-radius: 10px;
  box-shadow:
    0 1px 0 rgba(22, 22, 22, 0.04),
    0 18px 36px -22px rgba(22, 22, 22, 0.38);
}
.ab {
  font-family: var(--sans);
  font-size: 40px;
  font-weight: 500;
  line-height: 1;
  letter-spacing: -0.01em;
  color: var(--ink);
}
.nm {
  margin-top: 8px;
  font-size: 22px;
  color: var(--muted);
}
.tl {
  display: block;
  margin: 26px 0 24px;
  overflow: visible;
}
.model {
  fill: var(--ui);
  stroke: var(--hair);
  stroke-width: 1;
}
.rnd {
  fill: var(--card);
  stroke: var(--ink);
  stroke-width: 2;
}
/* training with the rounding: the training fill with the ink edge of the rounding */
.train {
  fill: var(--ui);
  stroke: var(--ink);
  stroke-width: 2;
}
.t {
  font-family: var(--sans);
  font-size: 18px;
  fill: var(--muted);
}
.t.ink {
  fill: var(--ink);
}
.t.mid {
  text-anchor: middle;
}
.ar {
  fill: none;
  stroke: var(--muted-2);
  stroke-width: 1.6;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.s1 {
  font-size: 24px;
  line-height: 1.3;
  color: var(--ink);
  text-wrap: balance;
}
.s2 {
  margin-top: 12px;
  font-size: 20px;
  line-height: 1.34;
  color: var(--muted);
  text-wrap: balance;
}

/* ---------- the size path ---------- */
.lede-s,
.goal-l {
  position: absolute;
  font-size: var(--fs-label);
  line-height: 1.3;
  white-space: nowrap;
}
/* the lede of the size path sits where every lede of the deck sits, 12 px under the claim */
.lede-s {
  left: 0;
  top: -14px;
  font-size: var(--fs-lede);
  line-height: 1.34;
  color: var(--muted);
}
.goal-l {
  color: var(--ink);
  padding-right: 10px;
}
.head {
  position: absolute;
  left: 0;
  width: 1136px;
  height: 20px;
}
.head .eyebrow {
  position: absolute;
  top: 0;
}
.rule {
  position: absolute;
  left: 0;
  width: 1136px;
  height: 0;
  border-top: 1px solid var(--ink);
}
.row {
  position: absolute;
  left: 0;
  width: 1136px;
  height: 50px;
  border-bottom: 1px solid var(--hair);
}
.lab {
  position: absolute;
  left: 0;
  top: 0;
  line-height: 50px;
  font-size: 20px;
  white-space: nowrap;
}
.track,
.bar {
  position: absolute;
  top: 16px;
  height: 18px;
  border-radius: 2px;
}
.track {
  background: var(--wash);
}
/* an estimate: a dashed ink outline; the measured teacher: solid ink */
.bar {
  box-sizing: border-box;
  border: 1.5px dashed var(--ink);
  background: rgba(22, 22, 22, 0.1);
}
.bar.measured {
  border-style: solid;
  background: var(--ink);
}
.times-v,
.size-v {
  position: absolute;
  top: 0;
  height: 50px;
  display: flex;
  align-items: center;
  font-family: var(--sans);
  font-size: 20px;
  font-variant-numeric: lining-nums tabular-nums;
  white-space: nowrap;
}
.times-v {
  left: 884px;
  gap: 8px;
}
.size-v {
  left: 990px;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  line-height: 1.15;
}
.meas {
  font-size: var(--fs-label);
  color: var(--muted-2);
}
.tick {
  flex: none;
  fill: none;
  stroke: var(--ink);
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.goal {
  position: absolute;
  width: 0;
  border-left: 2px solid var(--ink);
  z-index: 1;
}
.note {
  position: absolute;
  left: 0;
}
</style>
