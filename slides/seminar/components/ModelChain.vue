<script setup lang="ts">
// Slide 5: the map of the model part. Four models in a chain, read left to right, one per click,
// then what comes out on the laptop. Slides 6 to 9 zoom into the steps.
//   0  GLiNER2-PII as published, in the zone where we train (Google Cloud); the laptop waits.
//      It misses about 1 entity in 5 on T1 (recall 80.65 %), as slide 4 shows
//   1  step 1, fine-tune on 50,000 labelled rows: the teacher (v1), the same size, never in the
//      app; it learns the types the published model has no label for, such as titles and ages
//   2  step 2, distill: the student (v2), with fewer layers (6 in our size estimate) and a
//      smaller dictionary
//   3  step 3, quantize: the student we ship (v3) crosses to the laptop; it shows the O3 goal,
//      not a size estimate, because the number of layers is still open
//   4  the output on the laptop, on the prompt of slide 2: the student returns a span and its type,
//      the regex rules beside it catch the AVS number, and the app sends placeholders
// A model is a card, a step is an arrow with a verb. Facts: docs/project-management.md (v1 to
// v3), docs/baselines.md (1,244 MB measured; titles, ages, sex and gender have no label in the
// published model), docs/smart-goals.md (O3: at least 8 times smaller, at most 155.5 MB),
// src/pii_anonymizer/rules.py (AVS numbers by regex). The training rows are OpenPII-1M and
// Gretel. Nothing on this slide claims a result of the teacher or the students: they come later.
// The prompt stops after the AVS number: the type the student gives an address is not shown, so
// it is not claimed. The slide's one red is the headline's emphasis: the values stay ink here.
import { useBeats, inOutCubic, type Channels, type Seg } from './lib/beats'

const W = 1136

// ---------- geometry, in figure coordinates ----------
// the four model cards, and the dashed line between the cloud and the laptop
const CARDS = [
  { x: 0, w: 152 },
  { x: 268, w: 206 },
  { x: 578, w: 190 },
  { x: 904, w: 232 },
]
const LINE_X = 888
const CARD_Y = 40
const CARD_H = 218
const CARD_B = CARD_Y + CARD_H
// the arrows of the steps run at the height of the model names
const ARROW_Y = CARD_Y + 62
const STEPS = CARDS.slice(0, 3).map((c, i) => {
  const x1 = c.x + c.w + 8
  const x2 = CARDS[i + 1].x - 10
  // the label of the last step stays on the cloud side of the line
  const end = i === 2 ? LINE_X - 4 : CARDS[i + 1].x
  return { x1, x2, mid: (c.x + c.w + end) / 2, room: end - c.x - c.w - 6 }
})
// what each step does, one line each, under its arrow
const HOW = [
  ['on 50,000', 'labelled rows'],
  ['the teacher', 'teaches'],
  ['weights in', '1 byte, not 4'],
]
// the output, under the chain
const OUT_Y = CARD_B + 64
const H = OUT_Y + 142
const Q = CARDS[3]
const DOWN_X = Q.x + Q.w / 2

// ---------- states ----------
function target(n: number): Channels {
  return {
    a0: n >= 1 ? 1 : 0, l0: n >= 1 ? 1 : 0, m1: n >= 1 ? 1 : 0,
    a1: n >= 2 ? 1 : 0, l1: n >= 2 ? 1 : 0, m2: n >= 2 ? 1 : 0,
    a2: n >= 3 ? 1 : 0, l2: n >= 3 ? 1 : 0, m3: n >= 3 ? 1 : 0,
    down: n >= 4 ? 1 : 0, out: n >= 4 ? 1 : 0, u: n >= 4 ? 1 : 0, ty: n >= 4 ? 1 : 0, ph: n >= 4 ? 1 : 0,
  }
}
// One step: its label comes in, its arrow draws, then the new model arrives at the arrow's end
const step = (i: number): Seg[] => [
  { k: 'l' + i, to: 1, at: 0, dur: 300 },
  { k: 'a' + i, to: 1, at: 0, dur: 520, ease: inOutCubic },
  { k: 'm' + (i + 1), to: 1, at: 380, dur: 420 },
]
const beats: Record<number, Seg[]> = {
  1: step(0),
  2: step(1),
  3: step(2),
  4: [
    { k: 'down', to: 1, at: 0, dur: 420 },
    { k: 'out', to: 1, at: 160, dur: 380 },
    { k: 'u', to: 1, at: 560, dur: 500, ease: inOutCubic },
    { k: 'ty', to: 1, at: 860, dur: 360 },
    { k: 'ph', to: 1, at: 1160, dur: 380 },
  ],
}
const { ch, fade } = useBeats({ target, beats })

// ---------- what each state shows ----------
const clamp01 = (v: number) => Math.max(0, Math.min(1, v))
const vis = (v: number) => ({ opacity: v, visibility: v > 0.001 ? ('visible' as const) : ('hidden' as const) })
const rise = (v: number, d = 8) => ({ ...vis(v), transform: `translateY(${(1 - v) * d}px)` })
// a model card slides in from the arrow that makes it
const card = (i: number) => {
  const v = i === 0 ? 1 : ch['m' + i]
  return {
    left: CARDS[i].x + 'px',
    top: CARD_Y + 'px',
    width: CARDS[i].w + 'px',
    height: CARD_H + 'px',
    ...vis(v),
    transform: `translateX(${(1 - v) * -14}px)`,
  }
}
// the underlines of the two values draw one after the other
const under = (i: number) => ({ transform: `scaleX(${clamp01(ch.u * 1.6 - i * 0.6)})` })
const pop = (v: number) => ({ ...vis(v), transform: `scale(${1.12 - 0.12 * v})` })
</script>

<template>
  <div class="chain" :style="{ opacity: fade, height: H + 'px' }">
    <!-- where each model runs -->
    <div class="zone" :style="{ left: 0, width: LINE_X - 16 + 'px' }"><span class="eyebrow">Google Cloud, where we train</span></div>
    <div class="zone" :style="{ left: LINE_X + 16 + 'px', width: W - LINE_X - 16 + 'px' }"><span class="eyebrow">The laptop, in our app</span></div>
    <div class="divide" :style="{ left: LINE_X + 'px', height: OUT_Y - 12 + 'px' }" />

    <!-- the arrows: three steps, and the way down to the output -->
    <svg class="wires" :width="W" :height="H" aria-hidden="true">
      <g v-for="(s, i) in STEPS" :key="'a' + i">
        <path :d="`M ${s.x1} ${ARROW_Y} H ${s.x2}`" pathLength="1" class="shaft" :style="{ strokeDashoffset: 1 - ch['a' + i], ...vis(ch['a' + i]) }" />
        <path :d="`M ${s.x2 - 7} ${ARROW_Y - 6} L ${s.x2 + 1} ${ARROW_Y} L ${s.x2 - 7} ${ARROW_Y + 6}`" class="head" :style="vis(ch['a' + i] > 0.92 ? 1 : 0)" />
      </g>
      <path :d="`M ${DOWN_X} ${CARD_B + 8} V ${OUT_Y - 10}`" pathLength="1" class="shaft" :style="{ strokeDashoffset: 1 - ch.down, ...vis(ch.down) }" />
      <path :d="`M ${DOWN_X - 6} ${OUT_Y - 17} L ${DOWN_X} ${OUT_Y - 9} L ${DOWN_X + 6} ${OUT_Y - 17}`" class="head" :style="vis(ch.down > 0.92 ? 1 : 0)" />
    </svg>

    <!-- the steps: a verb above the arrow, what it does below -->
    <div
      v-for="(t, i) in ['Fine-tune', 'Distill', 'Quantize']"
      :key="t"
      class="verb"
      :style="{ left: STEPS[i].mid - STEPS[i].room / 2 + 'px', width: STEPS[i].room + 'px', top: ARROW_Y - 46 + 'px', ...rise(ch['l' + i], 6) }"
    >
      <span class="eyebrow">Step {{ i + 1 }}</span>
      <span class="vb">{{ t }}</span>
    </div>
    <div
      v-for="(h, i) in HOW"
      :key="h[0]"
      class="how"
      :style="{ left: STEPS[i].mid - STEPS[i].room / 2 + 'px', width: STEPS[i].room + 'px', top: ARROW_Y + 12 + 'px', ...vis(ch['l' + i]) }"
    >
      <span v-for="line in h" :key="line">{{ line }}</span>
    </div>

    <!-- the models -->
    <div class="model" :style="card(0)">
      <div class="tagrow"><span class="eyebrow">As published</span></div>
      <div class="mname">GLiNER2-PII</div>
      <div class="spec"><span>12 layers</span><span class="figure-num">1,244 MB</span></div>
      <p class="why">Misses about<br>1 entity in 5</p>
    </div>
    <div class="model" :style="card(1)">
      <div class="tagrow"><span class="ver">v1</span></div>
      <div class="mname">The teacher</div>
      <div class="spec"><span>12 layers</span><span class="figure-num">1,244 MB</span></div>
      <p class="why">Learns the types it misses: titles, ages</p>
    </div>
    <div class="model" :style="card(2)">
      <div class="tagrow"><span class="ver">v2</span></div>
      <div class="mname">The student</div>
      <div class="spec"><span>Fewer layers<br><span class="soft">6 in our estimate</span></span><span>Smaller dictionary</span></div>
    </div>
    <div class="model ship" :style="card(3)">
      <div class="tagrow"><span class="ver">v3</span></div>
      <div class="mname">The student we ship</div>
      <div class="goal eyebrow ink">Goal</div>
      <div class="spec goal-spec"><span>at least <span class="figure-num">8</span> times smaller</span><span>at most <span class="figure-num">155 MB</span></span></div>
    </div>

    <!-- the output, on the laptop -->
    <div class="out" :style="{ top: OUT_Y + 'px', ...rise(ch.out) }">
      <div class="out-head eyebrow ink">The output on the laptop</div>
      <p class="prompt">
        Write a contract reminder to
        <span class="w">Marie Dupont<span class="u" :style="under(0)" /><span class="ty" :style="rise(ch.ty, 6)">person</span><span class="chp" :style="pop(ch.ph)">&lt;PERSON_1&gt;</span></span>, AVS
        <span class="w">756.1234.5678.97<span class="u" :style="under(1)" /><span class="ty" :style="rise(ch.ty, 6)">AVS <span class="by">from our regex rules</span></span><span class="chp" :style="pop(ch.ph)">&lt;AVS_1&gt;</span></span>, ...
        <span class="rowlab ty-row eyebrow" :style="vis(ch.ty)">Type</span>
        <span class="rowlab ph-row eyebrow" :style="vis(ch.ph)">Sent</span>
      </p>
    </div>
  </div>
</template>

<style scoped>
.chain {
  position: relative;
  width: 1136px;
  margin-top: 22px;
}
.ink {
  color: var(--ink);
}

/* where each model runs: two zones and the dashed line between them, as on slide 2 */
.zone {
  position: absolute;
  top: 0;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--hair);
}
.zone .eyebrow {
  display: block;
}
.divide {
  position: absolute;
  top: 0;
  border-left: 1.5px dashed rgba(22, 22, 22, 0.3);
}

/* arrows */
.wires {
  position: absolute;
  left: 0;
  top: 0;
  overflow: visible;
}
.shaft {
  fill: none;
  stroke: var(--ink);
  stroke-width: 2;
  stroke-dasharray: 1;
}
.head {
  fill: none;
  stroke: var(--ink);
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

/* a step: never a box */
.verb {
  position: absolute;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  white-space: nowrap;
}
.vb {
  font-family: var(--mono);
  font-size: 16px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--ink);
}
.how {
  position: absolute;
  display: flex;
  flex-direction: column;
  align-items: center;
  font-size: 18px;
  line-height: 1.25;
  color: var(--muted);
  white-space: nowrap;
}

/* a model: a card */
.model {
  position: absolute;
  padding: 14px 14px;
  background: var(--card);
  border: 1px solid var(--hair);
  border-radius: 10px;
  box-shadow:
    0 1px 0 rgba(22, 22, 22, 0.04),
    0 18px 36px -22px rgba(22, 22, 22, 0.38);
}
/* the one we ship */
.model.ship {
  border: 2px solid var(--ink);
}
.tagrow {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 24px;
  white-space: nowrap;
}
.ver {
  font-family: var(--mono);
  font-size: 16px;
  line-height: 1;
  color: var(--ink);
  padding: 3px 7px 4px;
  border: 1px solid rgba(22, 22, 22, 0.4);
  border-radius: 4px;
}
.mname {
  margin-top: 6px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--hair);
  font-size: 22px;
  font-weight: 500;
  line-height: 1.15;
  letter-spacing: -0.01em;
  white-space: nowrap;
}
.spec {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-top: 8px;
  font-size: 19px;
  line-height: 1.25;
}
.spec .figure-num {
  font-size: 21px;
}
.soft {
  font-size: 18px;
  color: var(--muted);
}
/* step 1 in two lines, under a rule: what the published model misses, what the teacher learns */
.why {
  margin-top: 8px;
  padding-top: 7px;
  border-top: 1px solid var(--hair);
  font-size: 18px;
  line-height: 1.25;
}
/* the shipped student shows the O3 goal, not an estimate */
.goal {
  margin-top: 10px;
  line-height: 17px;
}
.goal-spec {
  margin-top: 2px;
}

/* the output */
.out {
  position: absolute;
  left: 0;
  width: 1136px;
  padding-top: 10px;
  border-top: 1px solid var(--ink);
}
.prompt {
  position: relative;
  margin-top: 14px;
  font-size: 21px;
  line-height: 30px;
  white-space: nowrap;
}
.w {
  position: relative;
  display: inline-block;
}
.u {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 1px;
  height: 2px;
  background: var(--ink);
  transform-origin: left center;
}
.ty {
  position: absolute;
  left: 0;
  top: 40px;
  font-family: var(--mono);
  font-size: 18px;
  line-height: 24px;
  color: var(--ink);
  white-space: nowrap;
}
.by {
  font-family: var(--sans);
  color: var(--muted);
}
/* the placeholder: an ink chip, like a redaction */
.chp {
  position: absolute;
  left: 0;
  top: 74px;
  font-family: var(--mono);
  font-size: 18px;
  line-height: 1;
  padding: 4px 6px;
  border-radius: 3px;
  background: var(--ink);
  color: var(--paper);
  white-space: nowrap;
  transform-origin: left center;
}
/* the names of the two rows, under the start of the prompt */
.rowlab {
  position: absolute;
  left: 0;
  line-height: 17px;
}
.ty-row {
  top: 44px;
}
.ph-row {
  top: 78px;
}
</style>
