<script setup lang="ts">
// Slide 5: hard label against soft labels, for the first "Dupont" of an example sentence.
// The teacher's scores are made up for the example: z = (4.0, 2.2, 0.6, 0.0) for PERSON,
// LOCATION, ORGANIZATION and NONE. Its probabilities are softmax(z / tau), computed here:
//   tau 1  82.2 / 13.6 / 2.7 / 1.5 %
//   tau 2  58.0 / 23.6 / 10.6 / 7.8 %
//   tau 4  41.1 / 26.2 / 17.6 / 15.1 %
// The ground truth is PERSON at 100 %.
//   0  tau = 1: who gives the target (ground truth or teacher) and its form (hard or soft)
//   1  tau = 2: the scores are divided by the temperature, the soft labels get flatter
//   2  tau = 4: LOCATION 26 %, so the student learns that Dupont can be a place
import { computed } from 'vue'
import { useBeats, inOutCubic, type Channels, type Seg } from './lib/beats'
import Callout from './Callout.vue'

const CLASSES = ['PERSON', 'LOCATION', 'ORGANIZATION', 'NONE']
const Z = [4.0, 2.2, 0.6, 0.0]
const TRUTH = [1, 0, 0, 0]
const TAUS = [1, 2, 4]

function softmax(z: number[], tau: number) {
  const e = z.map((v) => Math.exp(v / tau))
  const s = e.reduce((a, b) => a + b, 0)
  return e.map((v) => v / s)
}

function target(n: number): Channels {
  const i = Math.min(Math.max(n, 0), 2)
  return { tau: TAUS[i], sel: i, c0: i === 0 ? 1 : 0, c1: i === 1 ? 1 : 0, c2: i === 2 ? 1 : 0, loc: i === 2 ? 1 : 0 }
}
const step = (n: number, extra: Seg[] = []): Seg[] => [
  { k: 'sel', to: n, at: 0, dur: 320, ease: inOutCubic },
  { k: 'tau', to: TAUS[n], at: 0, dur: 900, ease: inOutCubic },
  { k: 'c' + (n - 1), to: 0, at: 0, dur: 200 },
  { k: 'c' + n, to: 1, at: 260, dur: 420 },
  ...extra,
]
const beats: Record<number, Seg[]> = {
  1: step(1),
  2: step(2, [{ k: 'loc', to: 1, at: 700, dur: 400 }]),
}
const { ch, fade } = useBeats({ target, beats })

const probs = computed(() => softmax(Z, ch.tau))
const pct = (v: number) => `${Math.round(v * 100)} %`
const score = (i: number) => (Z[i] / ch.tau).toFixed(2)
const BAR = 280
const on = (v: number, d = 8) => ({
  opacity: v,
  visibility: v > 0.001 ? ('visible' as const) : ('hidden' as const),
  transform: `translateY(${(1 - v) * d}px)`,
})
</script>

<template>
  <div class="soft" :style="{ opacity: fade }">
    <div class="top">
      <p class="line">Send the contract to Mrs <span class="val">Dupont</span>, Rue Dupont 4, Lausanne.</p>
      <span class="eyebrow">Example with made-up scores</span>
    </div>

    <div class="table">
      <!-- headers: who gives the target, then its form -->
      <div class="h" />
      <div class="h">
        <div class="eyebrow ink">Ground truth</div>
        <div class="form">hard label</div>
      </div>
      <div class="h sc">
        <div class="eyebrow">Score</div>
        <div class="form">/ <Tex e="\tau" /></div>
      </div>
      <div class="h teach">
        <div>
          <div class="eyebrow ink">The teacher's prediction</div>
          <div class="form">soft labels</div>
        </div>
        <div class="temp">
          <div class="eyebrow">Temperature <Tex class="tau" e="\tau" /></div>
          <div class="switch">
            <span class="knob" :style="{ transform: `translateX(${ch.sel * 48}px)` }" />
            <span v-for="(t, i) in TAUS" :key="t" class="opt" :class="{ act: Math.round(ch.sel) === i }">{{ t }}</span>
          </div>
        </div>
      </div>

      <div v-for="(c, i) in CLASSES" :key="c" class="row" :style="{ '--lit': i === 1 ? ch.loc : 0 }">
        <span class="mono cname">{{ c }}</span>
        <span class="cell">
          <span class="track" :style="{ width: BAR + 'px' }"><span class="fill" :style="{ transform: `scaleX(${TRUTH[i]})` }" /></span>
          <span class="num">{{ pct(TRUTH[i]) }}</span>
        </span>
        <span class="score">{{ score(i) }}</span>
        <span class="cell">
          <span class="track" :style="{ width: BAR + 'px' }"><span class="fill" :style="{ transform: `scaleX(${probs[i]})` }" /></span>
          <span class="num">{{ pct(probs[i]) }}</span>
        </span>
      </div>
    </div>

    <div class="notes">
      <Callout class="note" :style="on(ch.c0)">Hard or soft is the form of the target. Ground truth or prediction is who gives it.</Callout>
      <Callout class="note" :style="on(ch.c1)">The temperature <Tex e="\tau" /> divides each score before it becomes a probability. A higher <Tex e="\tau" /> brings the probabilities closer together.</Callout>
      <Callout class="note" :style="on(ch.c2)">The student is trained to copy all four values, so LOCATION gets 26 % too.<br>It learns that Dupont can also be a place.</Callout>
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
.top {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}
.line {
  font-size: 24px;
}
.val {
  color: var(--red);
  text-decoration: underline;
  text-decoration-thickness: 1.5px;
  text-underline-offset: 5px;
}

/* the table: class, ground truth, score, teacher */
.table {
  display: grid;
  grid-template-columns: 200px 400px 100px 1fr;
  margin-top: 22px;
}
.h {
  padding-bottom: 10px;
  border-bottom: 1px solid var(--ink);
  align-self: end;
}
.form {
  margin-top: 4px;
  font-size: 20px;
  color: var(--muted);
}
.sc {
  text-align: right;
  padding-right: 22px;
}
.teach {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
}
.temp {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
}
/* the eyebrows are uppercase: the math in them must keep its own case */
.tau :deep(.katex) {
  font-size: 20px;
  color: var(--ink);
  text-transform: none;
}
.form :deep(.katex) {
  font-size: 20px;
}
.switch {
  position: relative;
  display: flex;
  border: 1px solid var(--hair);
  border-radius: 6px;
  background: var(--card);
}
.knob {
  position: absolute;
  left: -1px;
  top: -1px;
  width: 48px;
  height: calc(100% + 2px);
  border-radius: 6px;
  background: var(--ink);
}
.opt {
  position: relative;
  width: 48px;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-variant-numeric: lining-nums tabular-nums;
  color: var(--muted-2);
  transition: color 0.2s;
}
.opt.act {
  color: var(--paper);
}
.row {
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: 200px 400px 100px 1fr;
  align-items: center;
  height: 46px;
  border-bottom: 1px solid var(--hair);
  background: rgba(22, 22, 22, calc(var(--lit) * 0.06));
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
.score {
  text-align: right;
  padding-right: 22px;
  font-size: 20px;
  font-variant-numeric: lining-nums tabular-nums;
  color: var(--muted);
}
.track {
  position: relative;
  height: 14px;
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
  min-width: 60px;
  font-size: 20px;
  font-variant-numeric: lining-nums tabular-nums;
}

.notes {
  position: relative;
  height: 84px;
  margin-top: 30px;
}
.note {
  position: absolute;
  left: 0;
  top: 0;
  max-width: 1080px;
}
</style>
