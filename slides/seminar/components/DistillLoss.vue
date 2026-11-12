<script setup lang="ts">
// Slide 7: the distillation loss of Hinton, Vinyals and Dean (2015), built term by term over
// the columns it compares. Each term of the formula sits over its two columns.
//   L = (1 - alpha) CE(y, p_S) + alpha tau^2 KL(p_T^tau || p_S^tau)
//   0  the student's answer p_S for Dupont
//   1  the first target: the ground truth y, and CE, which pulls the answer toward it
//   2  the second target: the teacher's soft labels at tau = 4, and KL, which pulls the
//      student's soft labels toward them; both columns start at tau = 1 and soften together
//   3  the weights: alpha mixes the two parts, tau^2 keeps the two parts balanced as tau changes
//   4  the control student: alpha = 0, so the teacher's part is off; distillation must beat it
// Same example as slide 6, with made-up scores:
//   teacher z_T = (4.0, 2.2, 0.6, 0.0)  tau 4  41.10 / 26.21 / 17.57 / 15.12 %
//   student z_S = (2.0, 0.0, 0.0, 0.0)  tau 1  71.12 / 9.63 / 9.63 / 9.63 %
//                                       tau 4  35.47 / 21.51 / 21.51 / 21.51 %
// The arrows give the sign of each pull on the student's values: up when the target is
// higher, down when it is lower. On LOCATION the two pulls disagree: CE down, KL up.
import { computed } from 'vue'
import { useBeats, inOutCubic, type Channels, type Seg } from './lib/beats'
import Callout from './Callout.vue'
import Tex from './Tex.vue'

const TYPES = ['PERSON', 'LOCATION', 'ORGANIZATION', 'NONE']
const ZT = [4.0, 2.2, 0.6, 0.0]
const ZS = [2.0, 0.0, 0.0, 0.0]
const TRUTH = [1, 0, 0, 0]
const HOT = 4

function softmax(z: number[], tau: number) {
  const e = z.map((v) => Math.exp(v / tau))
  const s = e.reduce((a, b) => a + b, 0)
  return e.map((v) => v / s)
}
const ANSWER = softmax(ZS, 1)
const T_HOT = softmax(ZT, HOT)
const S_HOT = softmax(ZS, HOT)
// the sign of each pull: +1 up, -1 down
const PULL_CE = ANSWER.map((p, i) => Math.sign(TRUTH[i] - p))
const PULL_KL = S_HOT.map((p, i) => Math.sign(T_HOT[i] - p))

// ---------- geometry ----------
// one column per distribution; each term of the formula sits over its pair of columns
const COL = [170, 398, 680, 908]
const PAIR_W = 442

// ---------- states ----------
function target(n: number): Channels {
  return {
    ce: n >= 1 ? 1 : 0, a: n >= 1 ? 1 : 0, aFill: n >= 1 ? 1 : 0, pullB: n >= 1 ? 1 : 0,
    kl: n >= 2 ? 1 : 0, cd: n >= 2 ? 1 : 0, tau: n >= 2 ? HOT : 1, pullD: n >= 2 ? 1 : 0, loc: n >= 2 ? 1 : 0,
    w: n >= 3 ? 1 : 0,
    ctl: n >= 4 ? 1 : 0, close: n >= 4 ? 1 : 0,
  }
}
const beats: Record<number, Seg[]> = {
  1: [
    { k: 'ce', to: 1, at: 0, dur: 380 },
    { k: 'a', to: 1, at: 100, dur: 300 },
    { k: 'aFill', to: 1, at: 200, dur: 650, ease: inOutCubic },
    { k: 'pullB', to: 1, at: 900, dur: 300 },
  ],
  // both soft columns start at tau = 1, then the temperature rises for both
  2: [
    { k: 'kl', to: 1, at: 0, dur: 380 },
    { k: 'cd', to: 1, at: 100, dur: 300 },
    { k: 'tau', to: HOT, at: 450, dur: 1100, ease: inOutCubic },
    { k: 'pullD', to: 1, at: 1600, dur: 300 },
    { k: 'loc', to: 1, at: 1600, dur: 400 },
  ],
  3: [{ k: 'w', to: 1, at: 0, dur: 450 }],
  4: [
    { k: 'ctl', to: 1, at: 0, dur: 600, ease: inOutCubic },
    { k: 'close', to: 1, at: 250, dur: 450 },
  ],
}
const { ch, fade, print } = useBeats({ target, beats })

// ---------- what each state shows ----------
const tHot = computed(() => softmax(ZT, ch.tau))
const sHot = computed(() => softmax(ZS, ch.tau))
const pct = (v: number) => `${Math.round(v * 100)} %`
const tauText = computed(() => (Math.abs(ch.tau - Math.round(ch.tau)) < 0.005 ? String(Math.round(ch.tau)) : ch.tau.toFixed(1)))
const vis = (v: number) => ({ opacity: v, visibility: v > 0.001 ? ('visible' as const) : ('hidden' as const) })
const rise = (v: number, d = 8) => ({ ...vis(v), transform: `translateY(${(1 - v) * d}px)` })
const bar = (v: number) => ({ transform: `scaleX(${Math.max(0, Math.min(1, v))})` })
// the teacher's part fades back when alpha = 0. In print the page keeps the whole formula at
// full strength, so the PDF never looks half rendered; the control callout says the rest.
const klDim = computed(() => (print.value ? 1 : 1 - 0.62 * ch.ctl))
const klPart = (v: number, d = 8) => ({ ...rise(v, d), opacity: v * klDim.value })
const at = (x: number) => ({ left: x + 'px' })
</script>

<template>
  <div class="loss" :style="{ opacity: fade }">
    <!-- the formula, built term by term; each term over the two columns it compares -->
    <div class="lhs" :style="rise(ch.ce)">
      <Tex e="\mathcal{L} \;=" />
    </div>
    <div class="half" :style="{ ...at(COL[0]), ...rise(ch.ce) }">
      <span class="wt" :style="vis(ch.w)"><Tex e="(1-\alpha)" /></span>
      <Tex e="\mathrm{CE}\big(y,\,p_S\big)" />
    </div>
    <div class="plus" :style="klPart(ch.kl)"><Tex e="+" /></div>
    <div class="half" :style="{ ...at(COL[2]), ...klPart(ch.kl) }">
      <span class="wt" :style="vis(ch.w)"><Tex e="\alpha\,\tau^2" /></span>
      <Tex e="\mathrm{KL}\big(p_T^{\tau}\,\|\,p_S^{\tau}\big)" />
    </div>

    <!-- what each part does -->
    <p class="loss-name" :style="rise(ch.ce)">the loss</p>
    <div class="bracket" :style="{ ...at(COL[0]), ...rise(ch.ce, 4) }" />
    <div class="bracket" :style="{ ...at(COL[2]), ...klPart(ch.kl, 4) }" />
    <div class="says" :style="{ ...at(COL[0]), ...rise(ch.ce) }">
      <span class="eyebrow ink">CE: cross-entropy</span>
      <p>pulls the answer toward the ground truth</p>
    </div>
    <div class="says" :style="{ ...at(COL[2]), ...klPart(ch.kl) }">
      <span class="eyebrow ink">KL: Kullback-Leibler divergence</span>
      <p>pulls the soft labels toward the teacher's</p>
    </div>

    <!-- the weights -->
    <p class="legend" :style="rise(ch.w)">
      <span><Tex e="\alpha" /> mixes the two parts, from 0 to 1</span>
      <span><Tex e="\tau^2" /> keeps the two parts balanced when the temperature <Tex e="\tau" /> changes</span>
    </p>

    <!-- the four distributions -->
    <div class="tab">
      <div class="head">
        <span class="eyebrow ex">Same example,<br>simplified,<br>made-up scores</span>
        <div class="h" :style="{ ...at(COL[0]), ...rise(ch.a) }"><Tex e="y" /><span>ground truth</span></div>
        <div class="h" :style="at(COL[1])"><Tex e="p_S" /><span>student's answer</span></div>
        <div class="h" :style="{ ...at(COL[2]), ...klPart(ch.cd) }"><Tex e="p_T^{\tau}" /><span>teacher, <Tex :e="`\\tau = ${tauText}`" /></span></div>
        <div class="h" :style="{ ...at(COL[3]), ...klPart(ch.cd) }"><Tex e="p_S^{\tau}" /><span>student, <Tex :e="`\\tau = ${tauText}`" /></span></div>
      </div>
      <div v-for="(t, i) in TYPES" :key="t" class="row" :style="{ '--lit': i === 1 ? ch.loc : 0 }">
        <span class="mono cname">{{ t }}</span>
        <span class="cell" :style="{ ...at(COL[0]), ...vis(ch.a) }">
          <span class="track"><span class="fill" :style="bar(TRUTH[i] * ch.aFill)" /></span>
          <span class="num">{{ pct(TRUTH[i] * ch.aFill) }}</span>
        </span>
        <span class="cell st" :style="at(COL[1])">
          <span class="track"><span class="fill" :style="bar(ANSWER[i])" /></span>
          <span class="num">{{ pct(ANSWER[i]) }}</span>
          <svg class="pull" :style="vis(ch.pullB)" width="12" height="12" viewBox="0 0 12 12" aria-hidden="true">
            <path :d="PULL_CE[i] > 0 ? 'M6 1 L11 10 L1 10 Z' : 'M6 11 L11 2 L1 2 Z'" />
          </svg>
        </span>
        <span class="cell" :style="{ ...at(COL[2]), opacity: ch.cd * klDim, visibility: ch.cd > 0.001 ? 'visible' : 'hidden' }">
          <span class="track"><span class="fill" :style="bar(tHot[i])" /></span>
          <span class="num">{{ pct(tHot[i]) }}</span>
        </span>
        <span class="cell st" :style="{ ...at(COL[3]), opacity: ch.cd * klDim, visibility: ch.cd > 0.001 ? 'visible' : 'hidden' }">
          <span class="track"><span class="fill" :style="bar(sHot[i])" /></span>
          <span class="num">{{ pct(sHot[i]) }}</span>
          <svg class="pull" :style="vis(ch.pullD)" width="12" height="12" viewBox="0 0 12 12" aria-hidden="true">
            <path :d="PULL_KL[i] > 0 ? 'M6 1 L11 10 L1 10 Z' : 'M6 11 L11 2 L1 2 Z'" />
          </svg>
        </span>
      </div>
    </div>

    <Callout class="close" :style="rise(ch.close, 10)">
      The control student uses <Tex e="\alpha = 0" />: no teacher. Distillation must beat it (goal O1).
    </Callout>
  </div>
</template>

<style scoped>
.loss {
  position: relative;
  width: 1136px;
  height: 470px;
  margin-top: 16px;
}
.ink {
  color: var(--ink);
}
.ex {
  position: absolute;
  left: 8px;
  bottom: 10px;
  line-height: 1.2;
  white-space: nowrap;
}

/* the formula */
.lhs,
.half,
.plus {
  position: absolute;
  top: 18px;
  height: 56px;
  display: flex;
  align-items: center;
  font-size: 34px;
  white-space: nowrap;
}
.lhs {
  left: 0;
  width: 150px;
  justify-content: flex-end;
}
.half {
  width: 442px;
  justify-content: center;
  gap: 8px;
}
.plus {
  left: 612px;
  width: 68px;
  justify-content: center;
}
.loss-name {
  position: absolute;
  left: 0;
  top: 94px;
  width: 150px;
  text-align: right;
  font-size: 20px;
}
.bracket {
  position: absolute;
  top: 78px;
  width: 442px;
  height: 9px;
  border: 1.5px solid var(--ink);
  border-top: none;
}
.says {
  position: absolute;
  top: 96px;
  width: 442px;
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.says p {
  font-size: 20px;
  line-height: 1.25;
}
.legend {
  position: absolute;
  left: 170px;
  top: 156px;
  display: flex;
  gap: 40px;
  font-size: 19px;
  color: var(--muted);
  white-space: nowrap;
}
.legend :deep(.katex) {
  margin-right: 4px;
  font-size: 1.15em;
}

/* the table */
.tab {
  position: absolute;
  left: 0;
  top: 196px;
  width: 1136px;
}
.head {
  position: relative;
  height: 60px;
  border-bottom: 1px solid var(--ink);
}
.h {
  position: absolute;
  bottom: 8px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 18px;
  color: var(--ink);
}
.h > :first-child :deep(.katex) {
  font-size: 23px;
}
.h span :deep(.katex) {
  font-size: 18px;
}
.row {
  position: relative;
  height: 38px;
  border-bottom: 1px solid var(--hair);
  background: rgba(22, 22, 22, calc(var(--lit, 0) * 0.06));
}
.cname {
  position: absolute;
  left: 8px;
  top: 8px;
  font-size: 18px;
}
.cell {
  position: absolute;
  top: 0;
  height: 38px;
  display: flex;
  align-items: center;
  gap: 10px;
}
.track {
  position: relative;
  width: 136px;
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
/* the student: graphite bars, so the two targets stay ink */
.st .fill {
  background: var(--muted-2);
}
.num {
  min-width: 50px;
  font-size: 20px;
  font-variant-numeric: lining-nums tabular-nums;
}
.pull {
  margin-left: -2px;
  fill: var(--ink);
}

.close {
  position: absolute;
  left: 0;
  top: 424px;
}
.close :deep(.text) {
  font-size: 24px;
}
</style>
