<script setup lang="ts">
// Slide 3: where each part runs. Slide 2 told the trip of one prompt, so this slide does not
// retell it. It shows the parts and their place, with the values of slide 2.
//   0  the laptop: our app runs the engine (rules and our model) and keeps the mapping
//      table; the cloud: our backend (FastAPI) calls the OpenAI Responses API; only
//      placeholders cross the border
//   1  the engine runs on every request, on the laptop CPU: our model is lit, and the
//      consequence closes the slide
// Names follow docs/architecture.md.
import { useBeats, type Channels, type Seg } from './lib/beats'
import Window from './Window.vue'
import Callout from './Callout.vue'

const ROWS = [
  { v: 'Marie Dupont', ph: '<PERSON_1>' },
  { v: '756.1234.5678.97', ph: '<AVS_1>' },
  { v: 'Rue Centrale 4, 1003 Lausanne', ph: '<ADDRESS_1>' },
]
const SENT = ROWS.map((r) => r.ph)

function target(n: number): Channels {
  return { lit: n >= 1 ? 1 : 0, close: n >= 1 ? 1 : 0 }
}
const beats: Record<number, Seg[]> = {
  1: [
    { k: 'lit', to: 1, at: 0, dur: 360 },
    { k: 'close', to: 1, at: 160, dur: 420 },
  ],
}
const { ch, fade } = useBeats({ target, beats })

const rise = (v: number, d = 10) => ({
  opacity: v,
  visibility: v > 0.001 ? ('visible' as const) : ('hidden' as const),
  transform: `translateY(${(1 - v) * d}px)`,
})

// the wire between the app and the backend, in figure coordinates
const APP_R = 724
const CLOUD_L = 796
const GO_Y = 112
const BACK_Y = 144
</script>

<template>
  <div class="setting" :style="{ opacity: fade }">
    <div class="zone laptop"><span class="eyebrow">Your laptop</span></div>
    <div class="zone cloud"><span class="eyebrow">The cloud</span></div>
    <div class="border" />

    <svg class="lanes" width="1136" height="400" aria-hidden="true">
      <defs>
        <marker id="set-ah" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M1 1 L9 5 L1 9" fill="none" stroke="currentColor" stroke-width="1.6" />
        </marker>
      </defs>
      <line :x1="APP_R + 6" :y1="GO_Y" :x2="CLOUD_L - 8" :y2="GO_Y" class="lane" marker-end="url(#set-ah)" />
      <line :x1="CLOUD_L - 6" :y1="BACK_Y" :x2="APP_R + 8" :y2="BACK_Y" class="lane" marker-end="url(#set-ah)" />
      <line x1="966" y1="188" x2="966" y2="212" class="lane" marker-end="url(#set-ah)" />
    </svg>

    <!-- the laptop: our app, the engine and the mapping table -->
    <Window class="w-app" title="Our app">
      <div class="app">
        <div class="engine">
          <div class="det">
            <div class="det-name">Rules</div>
            <div class="det-what">Fixed formats, such as Swiss social security (AVS) numbers</div>
          </div>
          <div class="det model" :style="{ '--lit': ch.lit }">
            <div class="det-name">Our model</div>
            <div class="det-what">What needs context, such as names and addresses</div>
          </div>
        </div>
        <div class="map-head eyebrow">Mapping table</div>
        <div v-for="r in ROWS" :key="r.ph" class="mrow">
          <span class="val">{{ r.v }}</span>
          <span class="dash" aria-hidden="true" />
          <span class="ph">{{ r.ph }}</span>
        </div>
      </div>
    </Window>
    <p class="legal">
      The table puts the real values back. So this is pseudonymization, not anonymization.
    </p>

    <!-- the cloud: our backend calls the OpenAI Responses API -->
    <Window class="w-cloud w-back" title="Our backend (FastAPI)" tone="dark">
      <div class="got">
        <span v-for="p in SENT" :key="p" class="ph dark">{{ p }}</span>
      </div>
    </Window>
    <Window class="w-cloud w-ai" title="OpenAI Responses API" tone="dark">
      <div class="got">
        <span v-for="p in SENT" :key="p" class="ph dark">{{ p }}</span>
      </div>
    </Window>

    <Callout class="close" :style="rise(ch.close)">So it must be small and fast.</Callout>
  </div>
</template>

<style scoped>
.setting {
  position: relative;
  width: 1136px;
  height: 500px;
  margin-top: 18px;
}

.zone {
  position: absolute;
  top: 0;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--hair);
}
.zone.laptop {
  left: 0;
  width: 724px;
}
.zone.cloud {
  left: 796px;
  width: 340px;
}
.border {
  position: absolute;
  left: 760px;
  top: 0;
  height: 368px;
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

/* the windows: a larger title bar, so the window names read at 18 px */
.w-app,
.w-cloud {
  position: absolute;
  z-index: 2;
  --win-bar: 46px;
  --win-title: 18px;
}
.w-app {
  left: 0;
  top: 38px;
  width: 724px;
  height: 330px;
}
.w-cloud {
  left: 796px;
  width: 340px;
}
.w-back {
  top: 38px;
  height: 148px;
}
.w-ai {
  top: 216px;
  height: 152px;
}

.app {
  padding: 18px 18px 0;
}
.engine {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}
.det {
  padding: 10px 14px 12px;
  border: 1px solid var(--hair);
  border-radius: 8px;
}
/* our model, lit on the click: the ink frame of slide 2's model card */
.det.model {
  border-color: rgba(22, 22, 22, calc(0.16 + var(--lit) * 0.84));
  box-shadow:
    inset 0 0 0 calc(var(--lit) * 1px) var(--ink),
    0 14px 30px -22px rgba(22, 22, 22, calc(var(--lit) * 0.5));
}
.det-name {
  font-size: 20px;
  font-weight: 500;
  line-height: 1.3;
}
.det-what {
  margin-top: 2px;
  font-size: 18px;
  line-height: 1.32;
  color: var(--muted);
}
.map-head {
  margin: 20px 0 4px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--hair);
  color: var(--ink);
}
.mrow {
  display: grid;
  grid-template-columns: 290px 64px 1fr;
  align-items: center;
  gap: 12px;
  height: 36px;
  border-bottom: 1px solid var(--hair);
}
.val {
  font-size: 18px;
  color: var(--red);
  white-space: nowrap;
}
.dash {
  height: 0;
  border-top: 1px solid rgba(22, 22, 22, 0.3);
}
/* the placeholder: an ink chip, like a redaction */
.ph {
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
/* on the dark panel the ink chip keeps a light edge, so it still reads as a chip */
.ph.dark {
  background: #0d0d0d;
  color: var(--on-dark);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.3);
}
.got {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  padding: 16px 16px;
}

.legal {
  position: absolute;
  left: 0;
  top: 406px;
  width: 1000px;
  font-size: 18px;
  line-height: 1.4;
  color: var(--muted);
}
.close {
  position: absolute;
  left: 0;
  top: 442px;
}
</style>
