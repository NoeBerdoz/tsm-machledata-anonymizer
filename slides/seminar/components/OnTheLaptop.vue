<script setup lang="ts">
// Slide 3: where our model runs, in three columns read left to right, one per state.
//   0  on the employee's laptop: the personal data (the prompt, the attached files) and our
//      model sit in the same card
//   1  on a normal laptop CPU: the spec card of the laptop we measure on
//      (docs/benchmark-protocol.md)
//   2  before every request: the time to check grows with the text, shown as an example;
//      the conclusion closes the slide
// The numbers 01 to 03 and their rules are there from the start; each click fills one column.
// The end state is the readable summary of the three.
import { useBeats, inOutCubic, linear, type Channels, type Seg } from './lib/beats'
import Callout from './Callout.vue'

const COLS = [
  { n: '01', head: "It runs on the employee's laptop" },
  { n: '02', head: 'It runs on a normal laptop CPU' },
  { n: '03', head: 'It runs before every request' },
]
const COL_W = 360
const GAP = 28
const colLeft = (i: number) => i * (COL_W + GAP)

// three of the file types our app takes (docs/architecture.md also lists TXT)
const TYPES = ['PDF', 'DOCX', 'CSV']
// the laptop we measure on (docs/benchmark-protocol.md)
const CORES = 4

// ---------- states ----------
function target(n: number): Channels {
  const c: Channels = {}
  for (let i = 0; i < 3; i++) {
    const on = i <= n ? 1 : 0
    c['r' + i] = on
    c['h' + i] = on
    c['k' + i] = on
  }
  Object.assign(c, {
    rows: 2, link: 1, lit: 1,
    cores: n >= 1 ? CORES : 0, mem: n >= 1 ? 1 : 0,
    barA: n >= 2 ? 1 : 0, barB: n >= 2 ? 1 : 0, close: n >= 2 ? 1 : 0,
  })
  return c
}
// One column: its rule draws, its line rises, then its card
const open = (i: number): Seg[] => [
  { k: 'r' + i, to: 1, at: 0, dur: 420, ease: inOutCubic },
  { k: 'h' + i, to: 1, at: 40, dur: 420 },
  { k: 'k' + i, to: 1, at: 180, dur: 460 },
]
const beats: Record<number, Seg[]> = {
  1: [
    ...open(1),
    { k: 'cores', to: CORES, at: 560, dur: 520, ease: linear },
    { k: 'mem', to: 1, at: 900, dur: 380 },
  ],
  2: [
    ...open(2),
    { k: 'barA', to: 1, at: 600, dur: 260 },
    { k: 'barB', to: 1, at: 760, dur: 1000, ease: inOutCubic },
    { k: 'close', to: 1, at: 1700, dur: 420 },
  ],
}
const { ch, fade } = useBeats({
  target,
  beats,
  entry: {
    from: { r0: 0, h0: 0, k0: 0, rows: 0, link: 0, lit: 0 },
    segs: [
      ...open(0),
      { k: 'rows', to: 2, at: 520, dur: 520, ease: linear },
      { k: 'link', to: 1, at: 1000, dur: 320, ease: inOutCubic },
      { k: 'lit', to: 1, at: 1240, dur: 380 },
    ],
  },
})

const clamp01 = (v: number) => Math.max(0, Math.min(1, v))
const vis = (v: number) => ({ opacity: v, visibility: v > 0.001 ? ('visible' as const) : ('hidden' as const) })
const rise = (v: number, d = 10) => ({ ...vis(v), transform: `translateY(${(1 - v) * d}px)` })
const card = (i: number) => ({ left: colLeft(i) + 'px', ...rise(ch['k' + i], 14) })
const coreOn = (i: number) => clamp01(ch.cores - i)
</script>

<template>
  <div class="laptop" :style="{ opacity: fade }">
    <!-- the three columns: number, the line to say, rule -->
    <div v-for="(c, i) in COLS" :key="c.n" class="col" :style="{ left: colLeft(i) + 'px', width: COL_W + 'px' }">
      <div class="num mono">{{ c.n }}</div>
      <div class="head" :style="rise(ch['h' + i])">{{ c.head }}</div>
      <div class="rule"><span class="ink" :style="{ transform: `scaleX(${ch['r' + i]})` }" /></div>
    </div>

    <!-- 01 the personal data and our model, on the same laptop -->
    <div class="card" :style="card(0)">
      <div class="ck eyebrow">The personal data</div>
      <div class="item" :style="rise(clamp01(ch.rows), 6)">
        <svg class="ico" width="20" height="20" viewBox="0 0 20 20" aria-hidden="true">
          <path d="M3.5 4.5h13a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1H9l-3.5 3v-3h-2a1 1 0 0 1-1-1v-7a1 1 0 0 1 1-1z" />
        </svg>
        <span>The prompt</span>
      </div>
      <div class="item" :style="rise(clamp01(ch.rows - 1), 6)">
        <svg class="ico" width="20" height="20" viewBox="0 0 20 20" aria-hidden="true">
          <path d="M5 2.5h7l4 4v11H5z" />
          <path d="M12 2.5v4h4" />
        </svg>
        <span>Attached files</span>
        <span class="types">
          <span v-for="t in TYPES" :key="t" class="type mono">{{ t }}</span>
        </span>
      </div>
      <svg class="link" width="20" height="30" viewBox="0 0 20 30" aria-hidden="true">
        <path d="M10 1 V26" pathLength="1" :style="{ strokeDashoffset: 1 - ch.link }" />
        <path d="M5 21 L10 27 L15 21" :style="vis(clamp01(ch.link * 4 - 3))" />
      </svg>
      <div class="model" :style="{ '--lit': ch.lit }">
        <span class="model-name eyebrow">Our model</span>
        <span class="model-what">checks it here</span>
      </div>
    </div>

    <!-- 02 the laptop we measure on: an ordinary one -->
    <div class="card" :style="card(1)">
      <div class="ck eyebrow">The laptop we measure on</div>
      <div class="lab">Processor (CPU)</div>
      <div class="cpu figure-num">Intel Core i5-1130G7</div>
      <div class="cores">
        <span v-for="i in CORES" :key="i" class="core" :style="{ '--on': coreOn(i - 1) }" />
        <span class="cores-n">{{ CORES }} cores</span>
      </div>
      <div class="mem" :style="rise(ch.mem, 6)">
        <span class="lab">Memory</span>
        <span class="mem-v figure-num">16 GB</span>
      </div>
    </div>

    <!-- 03 the check runs before each request: a long file takes longer -->
    <div class="card" :style="card(2)">
      <div class="ck eyebrow">
        <span>Time to check</span>
        <span class="ex">Example</span>
      </div>
      <div class="send">
        <span class="send-btn" aria-hidden="true">
          <svg width="12" height="12" viewBox="0 0 14 14"><path d="M7 11.5V2.5M3 6.5l4-4 4 4" /></svg>
        </span>
        <span>Send</span>
      </div>
      <span class="origin" />
      <div class="bar-lab lab-a">A short prompt</div>
      <div class="bar bar-a"><span :style="{ transform: `scaleX(${ch.barA})` }" /></div>
      <div class="bar-lab lab-b">A long file</div>
      <div class="bar bar-b"><span :style="{ transform: `scaleX(${ch.barB})` }" /></div>
    </div>

    <Callout class="close" :style="rise(ch.close)">So our model must be small and fast.</Callout>
  </div>
</template>

<style scoped>
.laptop {
  position: relative;
  width: 1136px;
  height: 506px;
  margin-top: 44px;
}

/* the columns */
.col {
  position: absolute;
  top: 0;
}
.num {
  font-size: 15px;
  letter-spacing: 0.12em;
  color: var(--muted-2);
}
.rule {
  position: relative;
  height: 2px;
  margin: 16px 0 0;
  background: var(--hair);
}
.rule .ink {
  position: absolute;
  inset: 0;
  background: var(--ink);
  transform-origin: left center;
}
/* number, line to say, then the rule: the column head of slide 11's goals */
.head {
  margin-top: 4px;
  font-size: 24px;
  font-weight: 500;
  line-height: 1.22;
  letter-spacing: -0.008em;
  color: var(--ink);
  white-space: nowrap;
}

/* the cards: things on the laptop, drawn crisp */
.card {
  position: absolute;
  top: 112px;
  width: 360px;
  height: 252px;
  padding: 16px 18px;
  border: 1px solid var(--hair);
  border-radius: 10px;
  background: var(--card);
  box-shadow:
    0 1px 0 rgba(22, 22, 22, 0.04),
    0 18px 36px -22px rgba(22, 22, 22, 0.38);
}
.ck {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding-bottom: 10px;
  margin-bottom: 12px;
  border-bottom: 1px solid var(--hair);
}
.lab {
  font-size: 18px;
  line-height: 1.3;
  color: var(--muted);
}

/* 01 */
.item {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 42px;
  margin-bottom: 8px;
  padding: 0 12px;
  border-radius: 8px;
  background: var(--ui);
  font-size: 18px;
}
.ico {
  flex: none;
  fill: none;
  stroke: var(--muted);
  stroke-width: 1.5;
  stroke-linejoin: round;
}
.types {
  display: flex;
  gap: 4px;
  margin-left: auto;
}
.type {
  font-size: 14px;
  letter-spacing: 0.06em;
  padding: 2px 4px 1px;
  border: 1px solid rgba(22, 22, 22, 0.28);
  border-radius: 3px;
  color: var(--muted);
}
.link {
  display: block;
  margin: 0 auto;
  fill: none;
  stroke: rgba(22, 22, 22, 0.5);
  stroke-width: 1.5;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.link path:first-child {
  stroke-dasharray: 1;
}
/* our model: the ink frame of slide 2's model card, lit when it arrives */
.model {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-top: 2px;
  padding: 12px 14px;
  border-radius: 8px;
  border: 1px solid var(--hair);
  box-shadow: inset 0 0 0 calc(var(--lit) * 2px) var(--ink);
}
.model-name {
  font-size: 15px;
  color: var(--ink);
}
.model-what {
  font-size: 18px;
  color: var(--muted);
}

/* 02 */
.cpu {
  margin-top: 2px;
  font-size: 30px;
  line-height: 1.15;
  font-stretch: 100%;
  letter-spacing: -0.012em;
}
.cores {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 14px;
}
.core {
  width: 26px;
  height: 26px;
  border-radius: 2px;
  border: 1px solid rgba(22, 22, 22, calc(0.2 + var(--on) * 0.8));
  background: rgba(22, 22, 22, calc(var(--on) * 0.9));
}
.cores-n {
  margin-left: 8px;
  font-size: 18px;
  color: var(--ink);
}
.mem {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-top: 18px;
  padding-top: 12px;
  border-top: 1px solid var(--hair);
}
.mem-v {
  font-size: 24px;
  font-stretch: 100%;
}

/* 03 */
.ex {
  letter-spacing: 0.14em;
  color: var(--ink);
  border: 1px solid rgba(22, 22, 22, 0.35);
  border-radius: 4px;
  padding: 0 6px;
}
/* the start of the check: the Send button of slide 2's chat */
.send {
  position: absolute;
  left: 7px;
  top: 58px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  line-height: 1;
  color: var(--muted);
}
.send-btn {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--ink);
  display: flex;
  align-items: center;
  justify-content: center;
}
.send-btn svg {
  fill: none;
  stroke: var(--paper);
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.origin {
  position: absolute;
  left: 18px;
  top: 82px;
  height: 146px;
  border-left: 1.5px solid var(--ink);
}
.bar-lab {
  position: absolute;
  left: 30px;
  font-size: 18px;
  color: var(--ink);
}
.lab-a {
  top: 96px;
}
.lab-b {
  top: 164px;
}
.bar {
  position: absolute;
  left: 19px;
  height: 16px;
}
.bar span {
  display: block;
  height: 100%;
  background: var(--ink);
  border-radius: 0 3px 3px 0;
  transform-origin: left center;
}
.bar-a {
  top: 126px;
  width: 34px;
}
.bar-b {
  top: 194px;
  width: 300px;
}

.close {
  position: absolute;
  left: 0;
  top: 424px;
}
</style>
