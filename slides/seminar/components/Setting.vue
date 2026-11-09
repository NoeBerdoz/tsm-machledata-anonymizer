<script setup lang="ts">
// Device | privacy boundary | cloud. step follows the slide clicks:
// 1 the values are replaced and the pairs go into the mapping table,
// 2 the pseudonymized prompt crosses the boundary,
// 3 the answer comes back, and only once it is on the device are the values restored.
import { computed, ref, watch } from 'vue'

const props = withDefaults(defineProps<{ step?: number }>(), { step: 0 })
const s = computed(() => props.step)

const promptState = computed(() => (s.value >= 1 ? 3 : 0))

// Restoration waits for the end of the trip back (450 ms) plus a short pause.
const restored = ref(s.value >= 3)
let timer: ReturnType<typeof setTimeout> | undefined
watch(s, (v, old) => {
  clearTimeout(timer)
  if (v >= 3 && (old ?? 0) < 3) timer = setTimeout(() => (restored.value = true), 560)
  else restored.value = v >= 3
})
const answerState = computed(() => (restored.value ? 0 : 3))

const H = 336
const BX = 580
</script>

<template>
  <div class="setting" :style="{ height: H + 'px' }">
    <ArtSlot name="Contours" class="contours" :w="1136 - BX - 24" :h="H - 32" :width="1136 - BX - 24" :height="H - 32" />

    <svg class="wires" :viewBox="`0 0 1136 ${H}`" width="1136" :height="H">
      <defs>
        <marker id="set-ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">
          <path d="M1 1 L9 5 L1 9" fill="none" stroke="var(--ink)" stroke-width="1.2" />
        </marker>
      </defs>
      <line :x1="BX" :x2="BX" y1="0" :y2="H" stroke="var(--ink)" stroke-width="1" />
      <path class="draw" :class="{ on: s >= 2 }" d="M 564 88 H 692" stroke="var(--ink)" stroke-width="1" fill="none" marker-end="url(#set-ah)" />
      <path class="draw" :class="{ on: s >= 3 }" d="M 692 300 H 564" stroke="var(--ink)" stroke-width="1" fill="none" marker-end="url(#set-ah)" />
    </svg>

    <div class="caption zone" style="left: 0">Device</div>
    <div class="caption zone" :style="{ left: BX + 12 + 'px' }">Privacy boundary</div>
    <div class="caption zone" style="right: 0">Cloud</div>

    <div class="card prompt">
      Remind <Pii :state="promptState" chip="<PERSON_1>">Marie Dupont</Pii> to pay into
      <Pii :state="promptState" chip="<IBAN_1>">CH93 0076 2011 6238 5295 7</Pii>.
    </div>

    <div class="map step" :class="{ on: s >= 1 }">
      <div class="caption">Stays on the device</div>
      <div class="mrow"><span class="chip-inline">&lt;PERSON_1&gt;</span><span class="mono">Marie Dupont</span></div>
      <div class="mrow"><span class="chip-inline">&lt;IBAN_1&gt;</span><span class="mono">CH93 0076 2011 6238 5295 7</span></div>
    </div>

    <div class="card packet out" :class="{ on: s >= 2 }">
      Remind <span class="chip-inline">&lt;PERSON_1&gt;</span> to pay into <span class="chip-inline">&lt;IBAN_1&gt;</span>.
    </div>

    <div class="card packet back" :class="{ on: s >= 3 }">
      Dear <Pii :state="answerState" chip="<PERSON_1>">Marie Dupont</Pii>, please pay into
      <Pii :state="answerState" chip="<IBAN_1>">CH93 0076 2011 6238 5295 7</Pii>.
    </div>
  </div>
</template>

<style scoped>
.setting {
  position: relative;
  width: 1136px;
  font-size: var(--fs-label);
  line-height: 1.5;
  --chip-size: 0.84em;
}
.contours {
  position: absolute;
  left: 604px;
  top: 32px;
}
.wires {
  position: absolute;
  left: 0;
  top: 0;
  overflow: visible;
}
.zone {
  position: absolute;
  top: 0;
  line-height: 1;
}
.card {
  position: absolute;
  background: var(--paper);
  border: 1px solid var(--hairline);
  padding: 12px 16px 14px;
}
.prompt {
  left: 0;
  top: 40px;
  width: 556px;
}
.map {
  position: absolute;
  left: 0;
  top: 136px;
  width: 556px;
}
.map .caption {
  margin-bottom: 6px;
}
.mrow {
  display: grid;
  grid-template-columns: 168px 1fr;
  align-items: center;
  height: 36px;
  border-top: 1px solid var(--hairline);
  font-size: var(--fs-caption);
}
.mrow:last-child {
  border-bottom: 1px solid var(--hairline);
}
.mrow .chip-inline {
  justify-self: start;
  font-size: var(--fs-caption);
}
.packet {
  width: 440px;
  transition:
    transform var(--t-slow) var(--ease),
    opacity var(--t-fast) var(--ease),
    width var(--t-slow) var(--ease);
}
.packet.out {
  left: 696px;
  top: 40px;
  opacity: 0;
  transform: translateX(-696px);
}
.packet.out.on {
  opacity: 1;
  transform: none;
}
.packet.back {
  left: 696px;
  top: 252px;
  opacity: 0;
}
.packet.back.on {
  opacity: 1;
  left: 0;
  width: 556px;
  transition:
    left var(--t-slow) var(--ease) 120ms,
    width var(--t-slow) var(--ease) 120ms,
    opacity var(--t-fast) var(--ease);
}
.draw {
  stroke-dasharray: 140;
  stroke-dashoffset: 140;
  opacity: 0;
  transition: stroke-dashoffset var(--t-mid) var(--ease), opacity 1ms linear;
}
.draw.on {
  stroke-dashoffset: 0;
  opacity: 1;
}
</style>
