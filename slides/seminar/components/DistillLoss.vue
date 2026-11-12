<script setup lang="ts">
// Slide 6: the distillation loss of Hinton, Vinyals and Dean (2015), each part named, and what
// it does to the student, computed.
//   L = alpha tau^2 KL(p_T^tau || p_S^tau) + (1 - alpha) CE(y, p_S)
// The chart uses slide 5's made-up scores z = (4.0, 2.2, 0.6, 0.0) at tau = 1, where the
// teacher gives 82.2 / 13.6 / 2.7 / 1.5 %. At tau = 1 the loss is smallest exactly when the
// student gives alpha x teacher + (1 - alpha) x ground truth, so the student's bars are that mix:
//   alpha 0.5  91.1 / 6.8 / 1.4 / 0.8 %
//   0  the formula, each part named
//   1  the student's best answer, between its two targets; alpha moves from 0 to 0.5
//   2  the control student of goal O1: alpha = 0, the ground truth only
import { computed } from 'vue'
import { useBeats, inOutCubic, type Channels, type Seg } from './lib/beats'
import Callout from './Callout.vue'

const CLASSES = ['PERSON', 'LOCATION', 'ORGANIZATION', 'NONE']
const Z = [4.0, 2.2, 0.6, 0.0]
const TRUTH = [1, 0, 0, 0]
const ALPHA = 0.5
const e = Z.map((v) => Math.exp(v))
const TEACH = e.map((v) => v / e.reduce((a, b) => a + b, 0))

function target(n: number): Channels {
  return { chart: n >= 1 ? 1 : 0, a: n >= 1 ? ALPHA : 0, ctrl: n >= 2 ? 1 : 0 }
}
const beats: Record<number, Seg[]> = {
  1: [
    { k: 'chart', to: 1, at: 0, dur: 420 },
    { k: 'a', to: ALPHA, at: 450, dur: 1300, ease: inOutCubic },
  ],
  2: [{ k: 'ctrl', to: 1, at: 0, dur: 450 }],
}
const { ch, fade } = useBeats({ target, beats })

const student = computed(() => TEACH.map((t, i) => ch.a * t + (1 - ch.a) * TRUTH[i]))
const pct = (v: number) => `${Math.round(v * 100)} %`
const aText = computed(() => ch.a.toFixed(1))
const BAR = 190
const on = (v: number, d = 10) => ({
  opacity: v,
  visibility: v > 0.001 ? ('visible' as const) : ('hidden' as const),
  transform: `translateY(${(1 - v) * d}px)`,
})

// the dial runs under the student, from the ground truth column to the teacher column
const COL = [200, 512, 824] // left edge of each column: ground truth, student, teacher
const DIAL_L = COL[0] + BAR / 2
const DIAL_R = COL[2] + BAR / 2
const dialX = (a: number) => DIAL_L + (DIAL_R - DIAL_L) * a
// the label of the alpha = 0 end makes room while the knob's own label passes over it
const endZero = computed(() => Math.max(0, Math.min(1, (dialX(ch.a) - DIAL_L - 110) / 60)))
</script>

<template>
  <div class="loss" :style="{ opacity: fade }">
    <!-- the formula, each part named under it -->
    <div class="formula">
      <div class="piece lhs"><Tex e="\mathcal{L} \;=\;" /><p class="says">the loss</p></div>
      <div class="term">
        <Tex e="\alpha\,\tau^2\,\mathrm{KL}\big(p_T^{\tau}\,\|\,p_S^{\tau}\big)" />
        <div class="brace" />
        <p class="says">KL: pulls the student's soft labels toward the teacher's</p>
      </div>
      <div class="piece"><Tex e="\;+\;" /></div>
      <div class="term">
        <Tex e="(1-\alpha)\,\mathrm{CE}\big(y,\,p_S\big)" />
        <div class="brace" />
        <p class="says">CE: pulls the student's answer toward the ground truth <Tex e="y" /></p>
      </div>
    </div>
    <div class="legend">
      <p><Tex e="p_T,\,p_S" /> teacher and student probabilities</p>
      <p><Tex e="\alpha" /> mixes the two parts</p>
      <p><Tex e="\tau^2" /> keeps the pull steady when the temperature <Tex e="\tau" /> changes</p>
    </div>

    <!-- what the loss does: the student's best answer sits between its two targets -->
    <div class="chart" :style="on(ch.chart, 14)">
      <div class="heads">
        <span class="eyebrow ex">Example of slide 5</span>
        <span class="eyebrow ink" :style="{ left: COL[0] + 'px' }">Ground truth <Tex e="y" /></span>
        <span class="eyebrow ink" :style="{ left: COL[1] + 'px' }">Student's answer</span>
        <span class="eyebrow ink" :style="{ left: COL[2] + 'px' }">Teacher, <Tex e="\tau = 1" /></span>
      </div>
      <div v-for="(c, i) in CLASSES" :key="c" class="row">
        <span class="mono cname">{{ c }}</span>
        <span class="cell" :style="{ left: COL[0] + 'px' }">
          <span class="track" :style="{ width: BAR + 'px' }"><span class="fill" :style="{ transform: `scaleX(${TRUTH[i]})` }" /></span>
          <span class="num">{{ pct(TRUTH[i]) }}</span>
        </span>
        <span class="cell" :style="{ left: COL[1] + 'px' }">
          <span class="track" :style="{ width: BAR + 'px' }"><span class="fill" :style="{ transform: `scaleX(${student[i]})` }" /></span>
          <span class="num">{{ pct(student[i]) }}</span>
        </span>
        <span class="cell" :style="{ left: COL[2] + 'px' }">
          <span class="track" :style="{ width: BAR + 'px' }"><span class="fill" :style="{ transform: `scaleX(${TEACH[i]})` }" /></span>
          <span class="num">{{ pct(TEACH[i]) }}</span>
        </span>
      </div>

      <!-- the dial: alpha = 0 copies the ground truth, alpha = 1 copies the teacher -->
      <div class="dial">
        <div class="rail" :style="{ left: DIAL_L + 'px', width: DIAL_R - DIAL_L + 'px' }" />
        <span class="end" :style="{ left: DIAL_L + 'px', opacity: endZero }"><Tex e="\alpha = 0" /></span>
        <span class="end" :style="{ left: DIAL_R + 'px' }"><Tex e="\alpha = 1" /></span>
        <span class="knob" :style="{ left: dialX(ch.a) + 'px' }" />
        <span class="knob-label" :style="{ left: dialX(ch.a) + 'px' }"><Tex :e="`\\alpha = ${aText}`" /></span>
        <span class="knob ctrl" :style="{ left: DIAL_L + 'px', ...on(ch.ctrl, 0) }" />
      </div>
    </div>

    <Callout class="close" :style="on(ch.ctrl)">
      The control student uses <Tex e="\alpha = 0" />, with the same setup.<br>Distillation must beat this control (goal O1).
    </Callout>
  </div>
</template>

<style scoped>
.loss {
  position: relative;
  width: 1136px;
  margin-top: 16px;
}
.ink {
  color: var(--ink);
}

/* the formula */
.formula {
  display: flex;
  align-items: flex-start;
  font-size: 40px;
}
.piece,
.term {
  flex: none;
}
/* the loss is named under its symbol, on the line of the two bracket labels */
.lhs {
  display: flex;
  flex-direction: column;
}
.lhs .says {
  margin-top: 19px;
}
.term {
  display: flex;
  flex-direction: column;
}
.brace {
  height: 9px;
  margin: 2px 4px 0;
  border: 1.5px solid var(--ink);
  border-top: none;
}
.says {
  max-width: 330px;
  margin: 8px 4px 0;
  font-size: 20px;
  line-height: 1.3;
}
.says :deep(.katex) {
  font-size: 1.1em;
}
.legend {
  display: flex;
  gap: 28px;
  margin-top: 16px;
  font-size: 19px;
  color: var(--muted);
}
/* one row: each symbol and its name stay together */
.legend p {
  flex: none;
  white-space: nowrap;
}
.legend :deep(.katex) {
  margin-right: 8px;
  font-size: 1.15em;
}

/* the chart */
.chart {
  position: relative;
  margin-top: 18px;
  padding-top: 10px;
  border-top: 1px solid var(--hair);
}
.heads {
  position: relative;
  height: 34px;
  border-bottom: 1px solid var(--ink);
}
.heads .eyebrow {
  position: absolute;
  top: 6px;
}
.heads .ex {
  left: 0;
}
/* the eyebrows are uppercase: the math in them must keep its own case */
.heads :deep(.katex) {
  font-size: 18px;
  letter-spacing: 0;
  text-transform: none;
}
.row {
  position: relative;
  height: 33px;
  border-bottom: 1px solid var(--hair);
}
.cname {
  position: absolute;
  left: 8px;
  top: 6px;
  font-size: 18px;
}
.cell {
  position: absolute;
  top: 0;
  height: 33px;
  display: flex;
  align-items: center;
  gap: 12px;
}
.track {
  position: relative;
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
  min-width: 56px;
  font-size: 20px;
  font-variant-numeric: lining-nums tabular-nums;
}

.dial {
  position: relative;
  height: 52px;
  font-size: 18px;
}
.rail {
  position: absolute;
  top: 18px;
  height: 0;
  border-top: 1.5px solid var(--ink);
}
.end {
  position: absolute;
  top: 26px;
  transform: translateX(-50%);
  color: var(--muted);
}
.end :deep(.katex),
.knob-label :deep(.katex) {
  font-size: 18px;
}
.knob {
  position: absolute;
  top: 10px;
  width: 16px;
  height: 16px;
  margin-left: -8px;
  border-radius: 50%;
  background: var(--ink);
}
/* the control student: an open ring at alpha = 0 */
.knob.ctrl {
  background: var(--paper);
  border: 2px solid var(--ink);
}
.knob-label {
  position: absolute;
  top: 26px;
  transform: translateX(-50%);
  white-space: nowrap;
}

.close {
  margin-top: 4px;
}
.close :deep(.text) {
  font-size: 22px;
}
</style>
