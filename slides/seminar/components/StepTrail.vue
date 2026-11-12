<script setup lang="ts">
// A process as a trail of steps on one line, read left to right. Steps already done are
// filled in ink, the current step carries the red marker, the steps to come wait.
//   current  index of the current step, from 0; -1 shows every step waiting
//   fill     where the ink line has reached, from 0 to the last index; it follows current
//            unless an animated figure drives it, so the line can flow from step to step
//   size     "sm" for a trail beside a headline, "lg" when the trail is the figure itself
//   inset    distance from each end of the trail to its first and last station
//   <StepTrail :steps="['Version', 'Train', 'Gate']" :current="1" />
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{ steps: string[]; current?: number; fill?: number; size?: 'sm' | 'lg'; width?: number; inset?: number }>(),
  { current: -1, size: 'sm' },
)

const W = computed(() => props.width ?? (props.size === 'lg' ? 1136 : 440))
const n = computed(() => props.steps.length)
// node centres: inset by half a label width so the end labels stay inside the trail
const inset = computed(() => props.inset ?? (props.size === 'lg' ? 56 : 26))
const x = (i: number) => inset.value + (i * (W.value - 2 * inset.value)) / Math.max(1, n.value - 1)
const reach = computed(() => Math.max(0, Math.min(n.value - 1, props.fill ?? props.current)))
const fillX = computed(() => (props.current < 0 && props.fill === undefined ? x(0) : x(0) + (x(1) - x(0)) * reach.value))
const state = (i: number) => {
  if (props.current < 0 && props.fill === undefined) return 'todo'
  if (i === props.current && reach.value >= i - 0.02) return 'now'
  return reach.value >= i - 0.02 ? 'done' : 'todo'
}
const Y = computed(() => (props.size === 'lg' ? 12 : 7))
const R = computed(() => (props.size === 'lg' ? 7 : 4.5))
</script>

<template>
  <div class="trail" :class="size" :style="{ width: W + 'px' }">
    <svg :width="W" :height="Y * 2" :viewBox="`0 0 ${W} ${Y * 2}`" aria-hidden="true">
      <line :x1="x(0)" :y1="Y" :x2="x(n - 1)" :y2="Y" class="track" />
      <line :x1="x(0)" :y1="Y" :x2="fillX" :y2="Y" class="fill" />
      <g v-for="(s, i) in steps" :key="s">
        <circle v-if="state(i) === 'now'" :cx="x(i)" :cy="Y" :r="R + (size === 'lg' ? 7 : 4.5)" class="halo" />
        <circle :cx="x(i)" :cy="Y" :r="R" class="node" :class="state(i)" />
      </g>
    </svg>
    <span v-for="(s, i) in steps" :key="'l' + s" class="lab" :class="state(i)" :style="{ left: x(i) + 'px' }">{{ s }}</span>
  </div>
</template>

<style scoped>
.trail {
  position: relative;
  flex: none;
}
.trail svg {
  display: block;
  overflow: visible;
}
.track {
  stroke: var(--hair);
  stroke-width: 1.2;
}
.fill {
  stroke: var(--ink);
  stroke-width: 2;
}
.lg .track {
  stroke-width: 2;
}
.lg .fill {
  stroke-width: 3.5;
  stroke-linecap: round;
}
.node {
  fill: var(--paper);
  stroke: rgba(22, 22, 22, 0.32);
  stroke-width: 1.4;
  transition: fill 0.25s, stroke 0.25s;
}
.lg .node {
  stroke-width: 2;
}
.node.done {
  fill: var(--ink);
  stroke: var(--ink);
}
/* the step we are on: the red marker */
.node.now {
  fill: var(--red);
  stroke: var(--red);
}
.halo {
  fill: var(--red-soft);
}
.lab {
  position: absolute;
  transform: translateX(-50%);
  white-space: nowrap;
  font-family: var(--mono);
  text-transform: uppercase;
  color: var(--muted-2);
  transition: color 0.25s;
}
.sm .lab {
  top: 20px;
  font-size: 11px;
  letter-spacing: 0.12em;
}
.lg .lab {
  top: 38px;
  font-size: 18px;
  letter-spacing: 0.1em;
}
.lab.done {
  color: var(--ink);
}
.lab.now {
  color: var(--ink);
}
</style>
