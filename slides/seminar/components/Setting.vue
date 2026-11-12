<script setup lang="ts">
// Appendix: where each part of our app runs, for a reader who asks where the real values
// come back. A static figure, with no clicks.
//   the laptop: our app runs the engine (rules and our model) and keeps the mapping table;
//   the cloud: our backend (FastAPI) calls the OpenAI Responses API; only placeholders
//   cross the border
// Names follow docs/architecture.md, values follow slide 2.
import Window from './Window.vue'

const ROWS = [
  { v: 'Marie Dupont', ph: '<PERSON_1>' },
  { v: '756.1234.5678.97', ph: '<AVS_1>' },
  { v: 'Rue Centrale 4, 1003 Lausanne', ph: '<ADDRESS_1>' },
]
const SENT = ROWS.map((r) => r.ph)

// the wire between the app and the backend, in figure coordinates
const APP_R = 724
const CLOUD_L = 796
const GO_Y = 112
const BACK_Y = 144
</script>

<template>
  <div class="setting">
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
          <div class="det model">
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
    <Window class="w-cloud w-back" title="Our backend (FastAPI)" tone="dark" icon="cloud">
      <div class="got">
        <span v-for="p in SENT" :key="p" class="ph dark">{{ p }}</span>
      </div>
    </Window>
    <Window class="w-cloud w-ai" title="OpenAI Responses API" tone="dark" icon="cloud">
      <div class="got">
        <span v-for="p in SENT" :key="p" class="ph dark">{{ p }}</span>
      </div>
    </Window>

  </div>
</template>

<style scoped>
.setting {
  position: relative;
  width: 1136px;
  height: 450px;
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
/* our model: the ink frame of slide 2's model card */
.det.model {
  border-color: var(--ink);
  box-shadow: inset 0 0 0 1px var(--ink);
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
</style>
