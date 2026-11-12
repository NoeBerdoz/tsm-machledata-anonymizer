<script setup lang="ts">
// The footer rail: one station per part of the talk. Parts already covered are filled in
// ink, the current part carries the red marker, the parts to come wait as open circles.
// all: every station lit and quiet, for the closing slide.
import { computed } from 'vue'
import { PARTS } from './parts'

const props = withDefaults(defineProps<{ current?: number; all?: boolean }>(), { current: 0, all: false })

const N = PARTS.length
const PITCH = 36
const X0 = 6
const x = (i: number) => X0 + i * PITCH
const lit = computed(() => (props.all ? N : props.current))
</script>

<template>
  <svg class="rail" :class="{ all }" :width="x(N - 1) + X0" height="14" :viewBox="`0 0 ${x(N - 1) + X0} 14`" aria-hidden="true">
    <line :x1="x(0)" y1="7" :x2="x(N - 1)" y2="7" class="track" />
    <line v-if="lit > 1" :x1="x(0)" y1="7" :x2="x(lit - 1)" y2="7" class="done" />
    <g v-for="(p, i) in PARTS" :key="p">
      <circle v-if="!all && i + 1 === current" :cx="x(i)" cy="7" r="6" class="halo" />
      <circle :cx="x(i)" cy="7" :r="!all && i + 1 === current ? 3.6 : 2.6" :class="[i + 1 <= lit ? 'on' : 'off', { here: !all && i + 1 === current }]" />
    </g>
  </svg>
</template>

<style scoped>
.rail {
  display: block;
  overflow: visible;
}
.rail.all {
  opacity: 0.5;
}
.track {
  stroke: var(--hair);
  stroke-width: 1;
}
.done {
  stroke: var(--ink);
  stroke-width: 1.2;
  opacity: 0.55;
}
.on {
  fill: var(--ink);
}
/* the part we are in: the red marker */
.on.here {
  fill: var(--red);
}
.off {
  fill: var(--paper);
  stroke: rgba(22, 22, 22, 0.32);
  stroke-width: 1.2;
}
.halo {
  fill: var(--red-soft);
}
</style>
