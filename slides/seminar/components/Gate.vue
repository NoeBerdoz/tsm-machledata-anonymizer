<script setup lang="ts">
// Train, evaluate, the quality gate, then the registry and the device.
// step 1 model A reaches the gate, fails and drops out. step 2 the gate opens and model B goes through.
import { computed } from 'vue'

const props = withDefaults(defineProps<{ step?: number }>(), { step: 0 })
const s = computed(() => props.step)

const nodes = [
  { x: 0, w: 200, label: 'Train in the cloud' },
  { x: 248, w: 200, label: 'Evaluate on T2-dev' },
  { x: 748, w: 168, label: 'Registry' },
  { x: 948, w: 188, label: 'Device app' },
]
const GX = 476
const GW = 240

const a = computed(() => {
  if (s.value >= 1) return { transform: `translate(${GX - 92}px, 0)`, opacity: 1 }
  return { transform: 'translate(268px, 0)', opacity: 0 }
})
const aDrop = computed(() => (s.value >= 1 ? { transform: 'translate(0, 152px)' } : {}))
const b = computed(() => {
  if (s.value >= 2) return { transform: 'translate(964px, 0)', opacity: 1 }
  return { transform: 'translate(268px, 0)', opacity: 0 }
})
</script>

<template>
  <div class="gate">
    <svg class="wires" viewBox="0 0 1136 320" width="1136" height="320">
      <defs>
        <marker id="g-ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto">
          <path d="M1 1 L9 5 L1 9" fill="none" stroke="var(--ink)" stroke-width="1.2" />
        </marker>
      </defs>
      <path d="M 200 148 H 244" stroke="var(--ink)" fill="none" marker-end="url(#g-ah)" />
      <path :d="`M ${GX + GW} 148 H 744`" stroke="var(--ink)" fill="none" marker-end="url(#g-ah)" />
      <path d="M 916 148 H 944" stroke="var(--ink)" fill="none" marker-end="url(#g-ah)" />
    </svg>

    <div v-for="n in nodes" :key="n.label" class="node label" :style="{ left: n.x + 'px', width: n.w + 'px' }">{{ n.label }}</div>

    <ArtSlot name="AlpGate" class="alp" :w="GW" :h="GW / 2" :width="GW" :open="s >= 2" />

    <div class="verdict fail label" :class="{ on: s >= 1 }">Fail</div>
    <div class="verdict pass label" :class="{ on: s >= 2 }">Pass</div>

    <div class="token-wrap" :style="a">
      <div class="token mono" :class="{ red: s >= 1 }" :style="aDrop">model A</div>
    </div>
    <div class="token-wrap" :style="b">
      <div class="token mono">model B</div>
    </div>
  </div>
</template>

<style scoped>
.gate {
  position: relative;
  width: 1136px;
  height: 320px;
  margin-top: 48px;
}
.wires {
  position: absolute;
  inset: 0;
  overflow: visible;
}
.node {
  position: absolute;
  top: 120px;
  height: 56px;
  display: flex;
  align-items: center;
  padding: 0 16px;
  border: 1px solid var(--hairline);
  background: var(--paper);
}
.alp {
  position: absolute;
  left: 476px;
  top: 76px;
}
.verdict {
  position: absolute;
  top: 216px;
  opacity: 0;
  transition: opacity var(--t-fast) var(--ease);
}
.verdict.on {
  opacity: 1;
}
.fail {
  left: 516px;
  color: var(--red);
  font-weight: 500;
}
.pass {
  left: 628px;
}
.token-wrap {
  position: absolute;
  left: 0;
  top: 72px;
  transition:
    transform var(--t-slow) var(--ease),
    opacity var(--t-fast) var(--ease);
}
.token {
  font-size: var(--fs-label);
  transition:
    transform var(--t-slow) var(--ease) 500ms,
    color var(--t-fast) var(--ease) 400ms;
}
</style>
