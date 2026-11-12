<script setup lang="ts">
// Slide 12: our planned MLOps pipeline as a trail of six steps, built one step per click.
// Each step shows the real thing it produces, in a card that hangs under its station.
//   0  Version  the DVC hash of the data, and the GitHub Actions tests on each merge
//   1  Train    MLflow's loss curves for models A and B, trained on Google Cloud
//   2  Gate     the table on T2-dev: A's recall stops under its goal line, so A is refused;
//               B passes every line
//   3  Deliver  the registry tags B as version 4; the app's status line moves from 3 to 4
//   4  Monitor  Sentry's chart of the pseudonymization time; the p95 crosses the alert line
//   5  Review   star feedback; people review it and plan the next run
//   6  the trail closes into a loop, Review back to Version, over one line per step
// The ink line fills from station to station as the pipeline moves on. Values are examples.
// The lede shows on the first and the last state only, so the steps in between stay light.
import { computed } from 'vue'
import { useBeats, inOutCubic, linear, type Channels, type Seg } from './lib/beats'
import StepTrail from './StepTrail.vue'
import Bar from './Bar.vue'

defineProps<{ lede?: string }>()

const STEPS = ['Version', 'Train', 'Gate', 'Deliver', 'Monitor', 'Review']
const W = 1136
const INSET = 120
const nodeX = (i: number) => INSET + (i * (W - 2 * INSET)) / (STEPS.length - 1)
const CARD_W = [640, 660, 820, 660, 800, 640]
const cardLeft = (i: number) => Math.max(0, Math.min(W - CARD_W[i], nodeX(i) - CARD_W[i] / 2))

// ---------- states ----------
function target(n: number): Channels {
  const c: Channels = {
    fill: Math.min(n, 5), sum: n >= 6 ? 1 : 0, loop: n >= 6 ? 1 : 0, lift: n >= 6 ? 1 : 0,
    lede: n === 0 || n >= 6 ? 1 : 0,
    hash: 1, check: 1, curves: 1, gA: 4, refuse: 1, gB: 4, pass: 1,
    tag: 1, flip: 1, only: 1, chart: 1, alert: 1, notes: 1, stars: 4, review: 1,
  }
  STEPS.forEach((_, i) => (c['c' + i] = i === n ? 1 : 0))
  return c
}
const reset = (...ks: string[]): Seg[] => ks.map((k) => ({ k, to: 0, at: 0, dur: 0 }))
// One step forward: the card of the past step leaves to the left, the ink line runs on
// to the next station, and the new card arrives from the right
const step = (n: number): Seg[] => [
  { k: 'c' + (n - 1), to: 0, at: 0, dur: 280 },
  { k: 'fill', to: n, at: 0, dur: 650, ease: inOutCubic },
  { k: 'c' + n, to: 1, at: 380, dur: 420 },
]
const beats: Record<number, Seg[]> = {
  1: [...step(1), { k: 'lede', to: 0, at: 0, dur: 250 }, ...reset('curves'), { k: 'curves', to: 1, at: 620, dur: 1200 }],
  2: [
    ...step(2),
    ...reset('gA', 'refuse', 'gB', 'pass'),
    { k: 'gA', to: 4, at: 640, dur: 680, ease: linear },
    { k: 'refuse', to: 1, at: 1320, dur: 260 },
    { k: 'gB', to: 4, at: 1520, dur: 600, ease: linear },
    { k: 'pass', to: 1, at: 2120, dur: 260 },
  ],
  3: [
    ...step(3),
    ...reset('tag', 'flip', 'only'),
    { k: 'tag', to: 1, at: 640, dur: 340 },
    { k: 'flip', to: 1, at: 1060, dur: 420 },
    { k: 'only', to: 1, at: 1420, dur: 420 },
  ],
  4: [
    ...step(4),
    ...reset('chart', 'alert', 'notes'),
    { k: 'chart', to: 1, at: 600, dur: 1100, ease: linear },
    { k: 'notes', to: 1, at: 900, dur: 450 },
    { k: 'alert', to: 1, at: 1700, dur: 300 },
  ],
  5: [
    ...step(5),
    ...reset('stars', 'review'),
    { k: 'stars', to: 4, at: 600, dur: 560, ease: linear },
    { k: 'review', to: 1, at: 1100, dur: 420 },
  ],
  6: [
    { k: 'c5', to: 0, at: 0, dur: 280 },
    { k: 'lift', to: 1, at: 0, dur: 700, ease: inOutCubic },
    { k: 'loop', to: 1, at: 450, dur: 1300, ease: inOutCubic },
    { k: 'sum', to: 1, at: 500, dur: 650 },
    { k: 'lede', to: 1, at: 500, dur: 450 },
  ],
}
const { ch, fade, clicks } = useBeats({
  target,
  beats,
  entry: {
    from: { hash: 0, check: 0 },
    segs: [
      { k: 'hash', to: 1, at: 350, dur: 520, ease: linear },
      { k: 'check', to: 1, at: 760, dur: 380 },
    ],
  },
})

const current = computed(() => (clicks.value <= 5 ? clicks.value : STEPS.length))
const card = (i: number) => {
  const v = ch['c' + i]
  const dir = i >= current.value ? 1 : -1
  return {
    left: cardLeft(i) + 'px',
    width: CARD_W[i] + 'px',
    opacity: v,
    visibility: v > 0.001 ? ('visible' as const) : ('hidden' as const),
    transform: `translateX(${(1 - v) * 22 * dir}px)`,
  }
}
const stem = (i: number) => ({ left: nodeX(i) - cardLeft(i) + 'px' })
const on = (v: number) => ({ opacity: v, visibility: v > 0.001 ? ('visible' as const) : ('hidden' as const) })
const clamp01 = (v: number) => Math.max(0, Math.min(1, v))

// Version: the hash types itself
const HASH = '3f9a1c'
const hashText = computed(() => HASH.slice(0, Math.round(ch.hash * HASH.length)))

// Train: loss per training step, A stays high, B goes low (example curves)
const curve = (loss: (t: number) => number) =>
  Array.from({ length: 41 }, (_, i) => {
    const t = i / 40
    return `${i === 0 ? 'M' : 'L'} ${(t * 480).toFixed(1)} ${(150 - loss(t) * 146).toFixed(1)}`
  }).join(' ')
const CURVE_A = curve((t) => 0.9 - 0.42 * (1 - Math.exp(-t * 3.2)) + 0.018 * Math.sin(t * 19))
const CURVE_B = curve((t) => 0.9 - 0.78 * (1 - Math.exp(-t * 4.2)) + 0.014 * Math.sin(t * 23))

// Gate: values on T2-dev, as examples. Every bar starts at zero; the line is the goal.
type Row = { name: string; goal: string; g: number; min: number; max: number; a: number; b: number; da: string; db: string; ex?: boolean }
const GATE: Row[] = [
  { name: 'O1 Recall vs teacher', goal: '95 %', g: 95, min: 0, max: 100, a: 88, b: 97, da: '88 %', db: '97 %' },
  { name: 'O2 Character precision', goal: 'example', g: 0.8, min: 0, max: 1, a: 0.84, b: 0.86, da: '0.84', db: '0.86', ex: true },
  { name: 'O3 Times smaller', goal: '12x', g: 12, min: 0, max: 16, a: 13, b: 13, da: '13x', db: '13x' },
  { name: 'O3 Times faster', goal: '4x', g: 4, min: 0, max: 6, a: 5, b: 5, da: '5x', db: '5x' },
]
const grow = (v: number, i: number) => clamp01(v - i)
const toneA = (r: Row, i: number) => (r.a < r.g && ch.gA >= i + 1 ? 'fail' : ch.gA >= i + 1 ? 'pass' : 'plain')
const toneB = (i: number) => (ch.gB >= i + 1 ? 'pass' : 'plain')

// Monitor: p95 of the pseudonymization time per window, as an example series
const P95 = [38, 41, 37, 40, 43, 41, 44, 46, 45, 49, 52, 55, 61, 68]
const ALERT = 58
const mx = (i: number) => 8 + (i * 352) / (P95.length - 1)
const my = (v: number) => 166 - (v - 30) * 3.4
const P95_PATH = P95.map((v, i) => `${i === 0 ? 'M' : 'L'} ${mx(i).toFixed(1)} ${my(v).toFixed(1)}`).join(' ')
const CROSS = { x: mx(12), y: my(61) }

// Review: four of five stars
const STAR = 'M8 0.9l2.1 4.4 4.8.6-3.5 3.3.9 4.8L8 11.6 3.7 14l.9-4.8L1.1 5.9l4.8-.6z'

// Summary, one line per station
const SUMMARY = ['DVC,\nGitHub Actions', 'Google Cloud,\nMLflow', 'A refused,\nB passes', 'Laptop runs\nversion 4', 'Sentry alerts\nwhen slow', 'People plan\nthe next run']

// The loop: from Review, round the right side, back along the bottom, up into Version
const LOOP_Y = 168
// On the last click the closed loop settles in the middle of the page
const LIFT = 96
const LOOP = `M ${nodeX(5) + 16} 12 H ${W - 38} Q ${W - 14} 12 ${W - 14} 36 V ${LOOP_Y - 24} Q ${W - 14} ${LOOP_Y} ${W - 38} ${LOOP_Y} H 38 Q 14 ${LOOP_Y} 14 ${LOOP_Y - 24} V 36 Q 14 12 38 12 H ${nodeX(0) - 18}`
</script>

<template>
  <div class="pipe" :style="{ opacity: fade }">
    <p class="lede lede-row" :style="on(ch.lede)">{{ lede }}</p>
    <span class="eyebrow examples">Values are examples</span>

    <div class="track" :style="{ transform: `translateY(${ch.lift * LIFT}px)` }">
    <!-- the loop that closes the trail at the end -->
    <svg class="loop" :width="W" height="260" aria-hidden="true">
      <defs>
        <marker id="pipe-ah" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="5" markerHeight="5" orient="auto">
          <path d="M1 1 L9 5 L1 9 z" fill="var(--ink)" />
        </marker>
      </defs>
      <path :d="LOOP" pathLength="1" class="loop-path" :style="{ strokeDashoffset: 1 - ch.loop, opacity: ch.loop > 0.001 ? 1 : 0 }" :marker-end="ch.loop > 0.97 ? 'url(#pipe-ah)' : undefined" />
      <path :d="`M ${W / 2 + 6} ${LOOP_Y - 8} L ${W / 2 - 4} ${LOOP_Y} L ${W / 2 + 6} ${LOOP_Y + 8}`" class="loop-chev" :style="on(clamp01(ch.loop * 4 - 2))" />
    </svg>

    <StepTrail class="trail" :steps="STEPS" :current="current" :fill="ch.fill" size="lg" :width="W" :inset="INSET" />

    <!-- 6 the summary under the closed loop -->
    <div v-for="(s, i) in SUMMARY" :key="s" class="sum" :style="{ left: nodeX(i) - 84 + 'px', ...on(clamp01(ch.sum * 1.6 - i * 0.12)) }">{{ s }}</div>
    </div>

    <!-- 0 Version -->
    <div class="card" :style="card(0)">
      <span class="stem" :style="stem(0)" />
      <div class="ck">DVC</div>
      <div class="kv">
        <span class="mono path">data/prepared</span>
        <span class="mono hash">md5 {{ hashText }}<span class="tcaret" :style="on(ch.hash < 1 ? 1 : 0)" /></span>
      </div>
      <div class="sep" />
      <div class="ck">GitHub Actions</div>
      <div class="kv">
        <span>tests on each merge</span>
        <span class="ok">
          <span class="mono" :style="on(ch.check)">passed</span>
          <svg class="tick" width="16" height="16" viewBox="0 0 14 14" aria-hidden="true"><path d="M2 7.6l3.3 3.2L12.2 3.4" pathLength="1" :style="{ strokeDashoffset: 1 - ch.check }" /></svg>
        </span>
      </div>
    </div>

    <!-- 1 Train -->
    <div class="card" :style="card(1)">
      <span class="stem" :style="stem(1)" />
      <div class="ck"><span>MLflow</span><span class="ck-r">Runs on Google Cloud</span></div>
      <svg class="chart" width="604" height="196" viewBox="-48 -16 604 196" aria-hidden="true">
        <line x1="0" y1="-8" x2="0" y2="150" class="axis" />
        <line x1="0" y1="150" x2="492" y2="150" class="axis" />
        <text x="-10" y="4" class="ax" text-anchor="end">loss</text>
        <text x="492" y="174" class="ax" text-anchor="end">training step</text>
        <path :d="CURVE_A" pathLength="1" class="curve a" :style="{ strokeDashoffset: 1 - ch.curves, opacity: ch.curves > 0.001 ? 1 : 0 }" />
        <path :d="CURVE_B" pathLength="1" class="curve b" :style="{ strokeDashoffset: 1 - ch.curves, opacity: ch.curves > 0.001 ? 1 : 0 }" />
        <text x="490" y="84" class="lab-a" :style="on(clamp01(ch.curves * 3 - 2))">model A</text>
        <text x="490" y="138" class="lab-b" :style="on(clamp01(ch.curves * 3 - 2))">model B</text>
      </svg>
    </div>

    <!-- 2 Gate -->
    <div class="card gate" :style="card(2)">
      <span class="stem" :style="stem(2)" />
      <div class="ck">T2-dev, our development set</div>
      <div class="grid head">
        <span />
        <span class="eyebrow">Goal</span>
        <span class="eyebrow">Model A</span>
        <span class="eyebrow">Model B</span>
      </div>
      <div v-for="(r, i) in GATE" :key="r.name" class="grid row">
        <span class="name">{{ r.name }}</span>
        <span class="mono goal">{{ r.goal }}</span>
        <Bar :value="r.a - r.min" :max="r.max - r.min" :goal="r.g - r.min" :goal-dashed="r.ex" :grow="grow(ch.gA, i)" :tone="toneA(r, i)" :display="r.da" :width="98" />
        <Bar :value="r.b - r.min" :max="r.max - r.min" :goal="r.g - r.min" :goal-dashed="r.ex" :grow="grow(ch.gB, i)" :tone="toneB(i)" :display="r.db" :width="98" />
      </div>
      <div class="grid verdict">
        <span />
        <span />
        <span class="stamp fail" :style="{ ...on(ch.refuse), transform: `scale(${1.25 - 0.25 * ch.refuse})` }">Refused</span>
        <span class="stamp pass" :style="{ ...on(ch.pass), transform: `scale(${1.25 - 0.25 * ch.pass})` }">Passes</span>
      </div>
    </div>

    <!-- 3 Deliver -->
    <div class="card" :style="card(3)">
      <span class="stem" :style="stem(3)" />
      <div class="ck">MLflow registry</div>
      <div class="kv reg">
        <span class="big">model B</span>
        <span class="vtag" :style="{ ...on(ch.tag), transform: `scale(${1.2 - 0.2 * ch.tag})` }">version 4</span>
      </div>
      <div class="sep" />
      <div class="ck">On the laptop</div>
      <div class="status">
        <span class="dot" />
        <span>Model: version</span>
        <span class="old" :class="{ gone: ch.flip > 0.5 }">3</span>
        <span class="new" :style="{ opacity: ch.flip, transform: `translateY(${(1 - ch.flip) * 10}px)` }">4</span>
      </div>
      <p class="note" :style="on(ch.only)">Only the model reaches the laptop.</p>
    </div>

    <!-- 4 Monitor -->
    <div class="card monitor" :style="card(4)">
      <span class="stem" :style="stem(4)" />
      <div class="ck"><span>Sentry</span><span class="ck-r">Pseudonymization time</span></div>
      <div class="mon">
        <svg class="chart" width="404" height="206" viewBox="-36 -12 404 206" aria-hidden="true">
          <line x1="0" y1="-6" x2="0" y2="174" class="axis" />
          <line x1="0" y1="174" x2="364" y2="174" class="axis" />
          <text x="-8" y="8" class="ax" text-anchor="end">ms</text>
          <text x="364" y="192" class="ax" text-anchor="end">time</text>
          <line x1="0" :y1="my(ALERT)" x2="364" :y2="my(ALERT)" class="alert-line" />
          <text x="0" :y="my(ALERT) - 8" class="ax red">alert line</text>
          <path :d="P95_PATH" pathLength="1" class="p95" :style="{ strokeDashoffset: 1 - ch.chart }" />
          <text :x="mx(5)" :y="my(41) + 22" class="ax ink" :style="on(ch.chart)">p95</text>
          <text :x="CROSS.x - 12" :y="CROSS.y - 12" class="ax red" text-anchor="end" :style="on(ch.alert)">Alert</text>
          <circle :cx="CROSS.x" :cy="CROSS.y" r="6" class="cross" :style="{ ...on(ch.alert), transformOrigin: `${CROSS.x}px ${CROSS.y}px`, transform: `scale(${2 - ch.alert})` }" />
        </svg>
        <div class="mon-notes" :style="on(ch.notes)">
          <p><b class="mono">p95</b>: 95 of 100 requests are faster than this.</p>
          <p>Sentry never sees the prompt or the answer.</p>
        </div>
      </div>
    </div>

    <!-- 5 Review -->
    <div class="card" :style="card(5)">
      <span class="stem" :style="stem(5)" />
      <div class="ck">Feedback in the app</div>
      <div class="rate">
        <span>Rate this answer</span>
        <span class="stars">
          <svg v-for="k in 5" :key="k" width="30" height="30" viewBox="0 0 16 15" aria-hidden="true">
            <path :d="STAR" stroke-width="1" :fill="ch.stars >= k - 0.01 ? 'var(--ink)' : 'none'" :stroke="ch.stars >= k - 0.01 ? 'var(--ink)' : 'rgba(22, 22, 22, 0.35)'" />
          </svg>
        </span>
      </div>
      <p class="review" :style="{ ...on(ch.review), transform: `translateY(${(1 - ch.review) * 8}px)` }">People review the feedback, then plan the next run.</p>
    </div>
  </div>
</template>

<style scoped>
.pipe {
  position: relative;
  width: 1136px;
  height: 452px;
  margin-top: 66px;
}
.lede-row {
  position: absolute;
  left: 0;
  top: -54px;
  margin: 0;
}
.examples {
  position: absolute;
  right: 0;
  top: -48px;
}
.track {
  position: absolute;
  left: 0;
  top: 0;
  width: 1136px;
}
.trail {
  position: absolute;
  left: 0;
  top: 0;
}
.loop {
  position: absolute;
  left: 0;
  top: 0;
  overflow: visible;
}
.loop-chev {
  fill: none;
  stroke: var(--ink);
  stroke-width: 3;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.loop-path {
  fill: none;
  stroke: var(--ink);
  stroke-width: 3;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-dasharray: 1;
}

/* the artefact cards */
.card {
  position: absolute;
  top: 110px;
  padding: 20px 28px 22px;
  background: var(--card);
  border: 1px solid var(--hair);
  border-radius: 10px;
  box-shadow:
    0 1px 0 rgba(22, 22, 22, 0.04),
    0 18px 36px -22px rgba(22, 22, 22, 0.38);
}
.stem {
  position: absolute;
  top: -42px;
  height: 42px;
  width: 0;
  border-left: 1.5px solid var(--ink);
}
.stem::after {
  content: '';
  position: absolute;
  left: -4.5px;
  bottom: -4px;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--ink);
}
.ck {
  display: flex;
  justify-content: space-between;
  font-family: var(--mono);
  font-size: 14px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--ink);
  margin-bottom: 10px;
}
.ck-r {
  color: var(--muted-2);
}
.sep {
  height: 1px;
  background: var(--hair);
  margin: 18px 0;
}
.kv {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  font-size: 22px;
}
.mono {
  font-family: var(--mono);
}
.path {
  font-size: 22px;
}
.hash {
  font-size: 22px;
  color: var(--ink);
}
.tcaret {
  display: inline-block;
  width: 2px;
  height: 18px;
  margin-left: 2px;
  vertical-align: -2px;
  background: var(--ink);
}
/* a value that passes: ink, then the deck's check mark, which draws itself */
.ok {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 20px;
  color: var(--ink);
}
.tick {
  flex: none;
  fill: none;
  stroke: var(--ink);
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-dasharray: 1;
}

/* charts */
.chart {
  display: block;
  overflow: visible;
}
.axis {
  stroke: var(--hair);
  stroke-width: 1.4;
}
.ax {
  font-family: var(--mono);
  font-size: 18px;
  fill: var(--muted-2);
}
.ax.red {
  fill: var(--red);
}
.ax.ink {
  fill: var(--ink);
}
.curve {
  fill: none;
  stroke-width: 3;
  stroke-linecap: round;
  stroke-dasharray: 1;
}
.curve.a {
  stroke: #a3a29c;
}
.curve.b {
  stroke: var(--ink);
}
.lab-a,
.lab-b {
  font-family: var(--sans);
  font-size: 20px;
}
.lab-a {
  fill: var(--muted-2);
}
.lab-b {
  fill: var(--ink);
}

/* gate */
.grid {
  display: grid;
  grid-template-columns: 262px 96px 1fr 1fr;
  align-items: center;
  column-gap: 8px;
}
.head {
  padding-bottom: 6px;
  border-bottom: 1px solid var(--hair);
}
.row {
  padding: 9px 0;
  border-bottom: 1px solid rgba(22, 22, 22, 0.07);
}
.name {
  font-size: 20px;
}
.goal {
  font-family: var(--sans);
  font-size: 20px;
  font-variant-numeric: lining-nums tabular-nums;
}
.verdict {
  padding-top: 10px;
}
.stamp {
  justify-self: start;
  font-family: var(--mono);
  font-size: 18px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  padding: 3px 8px;
  border: 1.5px solid currentColor;
  border-radius: 4px;
}
.stamp.fail {
  color: var(--red);
}
.stamp.pass {
  color: var(--ink);
}

/* deliver */
.reg {
  justify-content: flex-start;
}
.big {
  font-size: 26px;
  font-weight: 500;
}
.vtag {
  font-family: var(--mono);
  font-size: 20px;
  color: var(--paper);
  background: var(--ink);
  border-radius: 5px;
  padding: 3px 10px;
}
.status {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: var(--ui);
  border: 1px solid var(--hair);
  border-radius: 8px;
  font-family: var(--mono);
  font-size: 21px;
}
.status .dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--ink);
}
.old {
  color: var(--ink);
  transition: color 0.3s;
}
.old.gone {
  color: var(--muted-2);
  text-decoration: line-through;
  text-decoration-thickness: 2px;
}
.new {
  display: inline-block;
  color: var(--ink);
}
.note {
  margin-top: 18px;
  font-size: 22px;
}

/* monitor */
.mon {
  display: flex;
  gap: 22px;
  align-items: flex-start;
}
.alert-line {
  stroke: var(--red);
  stroke-width: 1.6;
  stroke-dasharray: 6 5;
}
.p95 {
  fill: none;
  stroke: var(--ink);
  stroke-width: 2.6;
  stroke-linejoin: round;
  stroke-dasharray: 1;
}
.cross {
  fill: var(--red);
}
.mon-notes {
  flex: 1;
  font-size: 20px;
  line-height: 1.35;
}
.mon-notes p + p {
  margin-top: 14px;
}
.mon-notes b {
  font-weight: 400;
}
.alert-msg {
  color: var(--red);
  font-size: 17px;
}

/* review */
.rate {
  display: flex;
  align-items: center;
  gap: 18px;
  font-size: 22px;
}
.stars {
  display: flex;
  gap: 4px;
}
.review {
  margin-top: 18px;
  font-size: 26px;
  text-wrap: balance;
  line-height: 1.3;
}

/* summary */
.sum {
  position: absolute;
  top: 78px;
  width: 168px;
  text-align: center;
  font-size: 22px;
  line-height: 1.25;
  color: var(--ink);
  white-space: pre-line;
}
</style>
