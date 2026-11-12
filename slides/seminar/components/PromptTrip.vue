<script setup lang="ts">
// Slide 2: the trip of one prompt, told in five states, one per click.
//   0  someone types a prompt in an AI chat on the laptop; the personal values are red
//   1  Send: the prompt crosses to the cloud AI, which takes it in, values included
//   2  the key figure, with its caption and its source word for word, on its own
//   3  replay with our model between the chat and the cloud: it finds each value, our app
//      keeps the value on the laptop and sends a placeholder; the cloud gets placeholders only
//   4  the answer comes back with placeholders and is restored on the laptop side
// Nothing ever travels out of the cloud except the answer with placeholders: between takes,
// the scene is hidden and the cloud panel simply clears.
import { computed } from 'vue'
import { useBeats, inOutCubic, linear, type Channels, type Seg } from './lib/beats'
import Window from './Window.vue'
import Callout from './Callout.vue'
import BigStat from './BigStat.vue'

type Part = { t: string; v?: boolean; ph?: string }
const PROMPT: Part[] = [
  { t: 'Write a contract reminder to ' },
  { t: 'Marie Dupont', v: true, ph: '<PERSON_1>' },
  { t: ', AVS ' },
  { t: '756.1234.5678.97', v: true, ph: '<AVS_1>' },
  { t: ', ' },
  { t: 'Rue Centrale 4, 1003 Lausanne', v: true, ph: '<ADDRESS_1>' },
  { t: '.' },
]
const KEPT = PROMPT.filter((p) => p.v)
const TOTAL = PROMPT.reduce((n, p) => n + p.t.length, 0)

// ---------- states ----------
const ZERO: Channels = {
  typed: 1, inputFull: 1, bubble: 0, sendFlash: 0, cloud1: 0, dim: 1, fig: 0, count: 1, src: 0,
  replay: 0, model: 0, rows: 0, swap: 0, cloud2: 0, answer: 0, back: 0, restore: 0, reply: 0, close: 0,
  chipA: 0, chipB: 0, chipC: 0, chipD: 0, chipE: 0,
}
function target(n: number): Channels {
  const c = { ...ZERO }
  if (n >= 1) Object.assign(c, { inputFull: 0, bubble: 1, cloud1: 1 })
  if (n === 2) Object.assign(c, { dim: 0, fig: 1, src: 1 })
  if (n >= 3) Object.assign(c, { cloud1: 0, replay: 1, model: 1, rows: 3, swap: 3, cloud2: 1 })
  if (n >= 4) Object.assign(c, { answer: 1, back: 1, restore: 1, reply: 1, close: 1 })
  return c
}
// A chip runs 0 to 1 along its lane, then rests at 0, where it is hidden
const run = (k: string, at: number, dur: number): Seg[] => [
  { k, to: 1, at, dur, ease: inOutCubic },
  { k, to: 0, at: at + dur, dur: 0 },
]
const beats: Record<number, Seg[]> = {
  1: [
    { k: 'sendFlash', to: 1, at: 0, dur: 120 },
    { k: 'sendFlash', to: 0, at: 300, dur: 300 },
    { k: 'inputFull', to: 0, at: 0, dur: 320 },
    { k: 'bubble', to: 1, at: 60, dur: 380 },
    ...run('chipA', 300, 800),
    { k: 'cloud1', to: 1, at: 1000, dur: 420 },
  ],
  // the scene leaves first, then the figure arrives: the two never overlap
  2: [
    { k: 'dim', to: 0, at: 0, dur: 260 },
    { k: 'count', to: 0, at: 0, dur: 0 },
    { k: 'fig', to: 1, at: 260, dur: 480 },
    { k: 'count', to: 1, at: 300, dur: 1000 },
    { k: 'src', to: 1, at: 600, dur: 400 },
  ],
  // the figure leaves first; the scene, reset for the replay while hidden, comes back after it
  3: [
    { k: 'fig', to: 0, at: 0, dur: 200 },
    { k: 'src', to: 0, at: 0, dur: 200 },
    { k: 'cloud1', to: 0, at: 0, dur: 0 },
    { k: 'bubble', to: 0, at: 0, dur: 0 },
    { k: 'inputFull', to: 1, at: 0, dur: 0 },
    { k: 'replay', to: 1, at: 0, dur: 0 },
    { k: 'dim', to: 1, at: 210, dur: 300 },
    { k: 'model', to: 1, at: 450, dur: 400 },
    { k: 'sendFlash', to: 1, at: 800, dur: 120 },
    { k: 'sendFlash', to: 0, at: 1000, dur: 300 },
    { k: 'inputFull', to: 0, at: 820, dur: 240 },
    { k: 'bubble', to: 1, at: 850, dur: 300 },
    ...run('chipB', 860, 330),
    { k: 'rows', to: 3, at: 1150, dur: 400, ease: linear },
    { k: 'swap', to: 3, at: 1400, dur: 400, ease: linear },
    ...run('chipC', 1800, 340),
    { k: 'cloud2', to: 1, at: 2100, dur: 320 },
  ],
  4: [
    { k: 'answer', to: 1, at: 0, dur: 380 },
    { k: 'back', to: 1, at: 0, dur: 300 },
    ...run('chipD', 360, 480),
    { k: 'restore', to: 1, at: 780, dur: 320 },
    ...run('chipE', 980, 360),
    { k: 'reply', to: 1, at: 1260, dur: 360 },
    { k: 'close', to: 1, at: 1500, dur: 450 },
  ],
}
const { ch, fade } = useBeats({
  target,
  beats,
  entry: { from: { typed: 0 }, segs: [{ k: 'typed', to: 1, at: 250, dur: 2100, ease: linear }] },
})

// ---------- what each state shows ----------
// The prompt as typed so far, cut into parts so the personal values stay red while typing
const typedParts = computed(() => {
  let left = Math.round(ch.typed * TOTAL)
  return PROMPT.map((p) => {
    const t = p.t.slice(0, Math.max(0, left))
    left -= p.t.length
    return { ...p, t }
  }).filter((p) => p.t.length)
})
const typing = computed(() => ch.typed < 1)
const vis = (v: number) => ({ opacity: v, visibility: v > 0.001 ? ('visible' as const) : ('hidden' as const) })
const rise = (v: number, d = 10) => ({ ...vis(v), transform: `translateY(${(1 - v) * d}px)` })
const rowOn = (i: number) => Math.max(0, Math.min(1, ch.rows - i))
const swapOn = (i: number) => Math.max(0, Math.min(1, ch.swap - i))

// lanes between the windows, in figure coordinates
const CHAT_R = 392
const MODEL_L = 420
const MODEL_R = 760
const CLOUD_L = 816
const GO_Y = 208
const BACK_Y = 242
const chip = (v: number, x0: number, x1: number, y: number) => ({
  left: x0 + (x1 - x0) * v - 13 + 'px',
  top: y - 6 + 'px',
  opacity: v > 0 && v < 1 ? Math.min(1, v * 8, (1 - v) * 8) : 0,
})
</script>

<template>
  <div class="trip" :style="{ opacity: fade }">
    <div class="scene" :style="{ opacity: ch.dim, visibility: ch.dim > 0.001 ? 'visible' : 'hidden' }">
      <!-- where things run -->
      <div class="zone laptop"><span class="eyebrow">Your laptop</span></div>
      <div class="zone cloud"><span class="eyebrow">The cloud</span></div>
      <div class="border" />

      <!-- the wire: out to the cloud above, back from it below -->
      <svg class="lanes" width="1136" height="420" aria-hidden="true">
        <defs>
          <marker id="trip-ah" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M1 1 L9 5 L1 9" fill="none" stroke="currentColor" stroke-width="1.6" />
          </marker>
        </defs>
        <line :x1="CHAT_R + 6" :y1="GO_Y" :x2="CLOUD_L - 8" :y2="GO_Y" class="lane" marker-end="url(#trip-ah)" />
        <line :x1="CLOUD_L - 6" :y1="BACK_Y" :x2="CHAT_R + 8" :y2="BACK_Y" class="lane" marker-end="url(#trip-ah)" :style="{ opacity: ch.back }" />
      </svg>
      <span class="chip red" :style="chip(ch.chipA, CHAT_R, CLOUD_L, GO_Y)" />
      <span class="chip red" :style="chip(ch.chipB, CHAT_R, MODEL_L + 20, GO_Y)" />
      <span class="chip ink" :style="chip(ch.chipC, MODEL_R - 20, CLOUD_L, GO_Y)" />
      <span class="chip ink" :style="chip(ch.chipD, CLOUD_L, MODEL_R - 20, BACK_Y)" />
      <span class="chip red" :style="chip(ch.chipE, MODEL_L + 20, CHAT_R, BACK_Y)" />

      <!-- the chat, on the laptop -->
      <Window class="w-chat" title="AI chat">
        <template #bar>
          <span class="replay-tag" :style="vis(ch.replay)">Replay</span>
        </template>
        <div class="convo">
          <div class="bub me" :style="rise(ch.bubble)">
            <template v-for="(p, i) in PROMPT" :key="i"><span :class="{ val: p.v }">{{ p.t }}</span></template>
          </div>
          <div class="bub ai" :style="rise(ch.reply)">
            Dear <span class="val">Marie Dupont</span>, please sign and return your contract.
          </div>
        </div>
        <div class="input" :class="{ full: ch.inputFull > 0.5 }">
          <div class="input-text" :style="{ opacity: ch.inputFull }">
            <template v-for="(p, i) in typedParts" :key="i"><span :class="{ val: p.v }">{{ p.t }}</span></template><span class="caret" :class="{ blink: !typing }" />
          </div>
          <span class="send" :style="{ background: `rgba(22, 22, 22, ${0.08 + ch.sendFlash * 0.92})`, color: ch.sendFlash > 0.5 ? '#fff' : 'var(--ink)' }">
            <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true"><path d="M7 11.5V2.5M3 6.5l4-4 4 4" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" /></svg>
          </span>
        </div>
      </Window>
      <p class="gloss"><span class="mono">AVS</span>: Swiss social security number</p>

      <!-- our model, on the laptop, between the chat and the cloud -->
      <div class="model" :style="rise(ch.model, 16)">
        <div class="model-head eyebrow">Our model</div>
        <div class="cols"><span>Kept here</span><span>Sent</span></div>
        <div v-for="(p, i) in KEPT" :key="p.ph" class="row" :style="{ '--lit': i === 0 ? ch.restore : 0 }">
          <span class="row-v val" :style="{ opacity: rowOn(i), transform: `translateX(${(1 - rowOn(i)) * -10}px)` }">{{ p.t }}</span>
          <span class="row-ph" :style="{ opacity: swapOn(i), transform: `translateX(${(1 - swapOn(i)) * -10}px)` }">{{ p.ph }}</span>
        </div>
      </div>

      <!-- the cloud AI -->
      <Window class="w-cloud" title="Cloud AI" tone="dark">
        <div class="cloud-body">
          <div class="take" :style="vis(ch.cloud1)">
            <div class="ck">Received</div>
            <p class="ct" :style="rise(ch.cloud1, 8)">
              <template v-for="(p, i) in PROMPT" :key="i"><span :class="{ val: p.v }">{{ p.t }}</span></template>
            </p>
          </div>
          <div class="take" :style="vis(ch.cloud2)">
            <div class="ck">Received</div>
            <p class="ct" :style="rise(ch.cloud2, 8)">
              <template v-for="(p, i) in PROMPT" :key="i"><span v-if="p.v" class="ph">{{ p.ph }}</span><span v-else>{{ p.t }}</span></template>
            </p>
            <p class="ct ct2" :style="rise(ch.answer, 8)">Dear <span class="ph">&lt;PERSON_1&gt;</span>, please sign and return your contract.</p>
          </div>
        </div>
      </Window>

      <Callout class="close" :style="rise(ch.close, 10)">This time, the AI only saw placeholders.</Callout>
    </div>

    <!-- the key figure, on its own beat, with its source -->
    <div class="fig" :style="rise(ch.fig, 18)">
      <BigStat :value="48" suffix="%" :progress="ch.count" :size="168" side>
        of employees report that they have uploaded company information, such as financial, sales, or customer information, into public AI tools.
      </BigStat>
    </div>
    <p class="src" :style="vis(ch.src)">
      University of Melbourne and KPMG (2025), Trust, attitudes and use of AI: a global study 2025, p. 75. Online survey of 48,340 people in 47 countries, Switzerland included.
    </p>
  </div>
</template>

<style scoped>
.trip {
  position: relative;
  width: 1136px;
  height: 546px;
  margin-top: 10px;
}
.val {
  color: var(--red);
  white-space: nowrap;
}

.scene {
  position: absolute;
  inset: 0;
}
.zone {
  position: absolute;
  top: 14px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--hair);
}
.zone.laptop {
  left: 0;
  width: 760px;
}
.zone.cloud {
  left: 816px;
  width: 320px;
}
.border {
  position: absolute;
  left: 788px;
  top: 14px;
  height: 384px;
  border-left: 1.5px dashed rgba(22, 22, 22, 0.3);
}

.lanes {
  position: absolute;
  left: 0;
  top: 0;
  color: rgba(22, 22, 22, 0.45);
}
.lane {
  stroke: currentColor;
  stroke-width: 1.4;
}
.chip {
  position: absolute;
  z-index: 1;
  width: 26px;
  height: 12px;
  border-radius: 6px;
}
.chip.red {
  background: var(--red);
}
/* a message that carries placeholders only: the ink of a placeholder chip */
.chip.ink {
  background: var(--ink);
}

/* the windows: a larger title bar, so the window names read at 18 px */
.w-chat,
.w-cloud {
  position: absolute;
  z-index: 2;
  top: 52px;
  height: 346px;
  --win-bar: 46px;
  --win-title: 18px;
}
.w-chat {
  left: 0;
  width: 392px;
}
.w-cloud {
  left: 816px;
  width: 320px;
}
.replay-tag {
  font-family: var(--mono);
  font-size: 15px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--ink);
  border: 1px solid rgba(22, 22, 22, 0.4);
  border-radius: 4px;
  padding: 1px 7px;
}
.convo {
  position: absolute;
  left: 14px;
  right: 14px;
  top: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.bub {
  max-width: 360px;
  padding: 10px 13px 11px;
  border-radius: 12px;
  font-size: 18px;
  line-height: 1.38;
}
.bub.me {
  align-self: flex-end;
  background: var(--ui);
  border-bottom-right-radius: 4px;
}
.bub.ai {
  align-self: flex-start;
  background: #f5f4f1;
  border-bottom-left-radius: 4px;
}
.input {
  position: absolute;
  left: 14px;
  right: 14px;
  bottom: 14px;
  min-height: 46px;
  padding: 10px 12px 10px 14px;
  border: 1px solid var(--hair);
  border-radius: 12px;
  background: var(--card);
}
.input-text {
  font-size: 18px;
  line-height: 1.38;
  min-height: 24px;
}
.input:not(.full) .input-text {
  height: 24px;
  overflow: hidden;
}
.caret {
  display: inline-block;
  width: 2px;
  height: 21px;
  margin-left: 1px;
  vertical-align: -4px;
  background: var(--ink);
}
.caret.blink {
  animation: trip-blink 1.1s steps(2, start) infinite;
}
@keyframes trip-blink {
  50% {
    opacity: 0;
  }
}
.send {
  position: absolute;
  right: 9px;
  bottom: 9px;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}
.gloss {
  position: absolute;
  left: 0;
  top: 410px;
  font-size: 18px;
  color: var(--muted);
}
.gloss .mono {
  color: var(--ink);
}

/* our model */
.model {
  position: absolute;
  z-index: 2;
  left: 420px;
  top: 104px;
  width: 340px;
  padding: 14px 16px 12px;
  border: 2px solid var(--ink);
  border-radius: 10px;
  background: var(--card);
  box-shadow: 0 18px 36px -22px rgba(22, 22, 22, 0.42);
}
.model-head {
  padding-bottom: 10px;
  border-bottom: 1px solid var(--hair);
  color: var(--ink);
  font-size: 15px;
}
.cols {
  display: grid;
  grid-template-columns: 1fr 132px;
  gap: 10px;
  margin: 10px 0 4px;
  font-size: 18px;
  color: var(--muted);
}
.row {
  display: grid;
  grid-template-columns: 1fr 132px;
  align-items: start;
  gap: 10px;
  padding: 6px 6px;
  margin: 0 -6px;
  border-radius: 6px;
  background: rgba(22, 22, 22, calc(var(--lit) * 0.07));
}
.row-v {
  font-size: 18px;
  line-height: 1.3;
  white-space: normal;
}
/* the placeholder: an ink chip, like a redaction */
.row-ph {
  justify-self: start;
  font-family: var(--mono);
  font-size: 18px;
  line-height: 1;
  padding: 4px 6px;
  border-radius: 3px;
  background: var(--ink);
  color: var(--paper);
  white-space: nowrap;
}

/* the cloud AI */
.cloud-body {
  position: absolute;
  inset: 0;
}
.take {
  position: absolute;
  left: 16px;
  right: 16px;
  top: 16px;
}
.ck {
  font-family: var(--mono);
  font-size: 14px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--on-dark-2);
  margin-bottom: 8px;
}
.ct {
  font-size: 18px;
  line-height: 1.42;
  color: var(--on-dark);
}
.ct .val {
  color: var(--red-on-dark);
}
/* on the dark panel the ink chip keeps a light edge, so it still reads as a chip */
.ct .ph {
  font-family: var(--mono);
  font-size: 18px;
  padding: 1px 5px;
  border-radius: 3px;
  background: #0d0d0d;
  color: var(--on-dark);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.3);
  white-space: nowrap;
}
.ct2 {
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

/* the figure */
.fig {
  position: absolute;
  left: 0;
  top: 120px;
  width: 1100px;
}
.fig :deep(.k) {
  max-width: 760px;
  font-size: 30px;
  line-height: 1.3;
}

.close {
  position: absolute;
  left: 0;
  top: 456px;
}
.src {
  position: absolute;
  left: 0;
  top: 502px;
  width: 940px;
  font-family: var(--sans);
  font-size: 14px;
  line-height: 1.45;
  color: var(--muted-2);
}

@media (prefers-reduced-motion: reduce) {
  .caret.blink {
    animation: none;
  }
}
</style>
