<script setup lang="ts">
// One horizontal bar against a goal line, for a measure that must reach a threshold.
//   value, max   the bar is value / max of the track
//   goal         where the goal line stands, in the same unit; dashed when the goal is an example
//   tone         "pass" ink with a check mark, "fail" red, "plain" grey while it grows
//   grow         0 to 1, how far the bar has grown; an animated figure drives it
//   <Bar :value="88" :max="100" :goal="95" tone="fail" display="88 %" />
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{ value: number; max: number; goal?: number; goalDashed?: boolean; tone?: 'pass' | 'fail' | 'plain'; grow?: number; display?: string; width?: number }>(),
  { tone: 'plain', grow: 1, goalDashed: false, width: 160 },
)
const pct = (v: number) => Math.max(0, Math.min(100, (v / (props.max || 1)) * 100))
const fillW = computed(() => (pct(props.value) * props.grow) / 100)
</script>

<template>
  <div class="bar" :class="tone">
    <div class="track" :style="{ width: width + 'px' }">
      <div class="fill" :style="{ transform: `scaleX(${fillW})` }" />
      <div v-if="goal !== undefined" class="goal" :class="{ dashed: goalDashed }" :style="{ left: pct(goal) + '%' }" />
    </div>
    <span class="val" :style="{ opacity: grow > 0.6 ? 1 : 0 }">
      <span class="num">{{ display ?? value }}</span>
      <svg v-if="tone === 'pass'" class="tick" width="14" height="14" viewBox="0 0 14 14" aria-hidden="true"><path d="M2 7.6l3.3 3.2L12.2 3.4" /></svg>
    </span>
  </div>
</template>

<style scoped>
.bar {
  display: flex;
  align-items: center;
  gap: 12px;
}
.track {
  position: relative;
  height: 12px;
  background: var(--wash);
  border-radius: 2px;
}
.fill {
  position: absolute;
  inset: 0;
  transform-origin: left center;
  border-radius: 2px;
  background: rgba(22, 22, 22, 0.4);
}
.pass .fill {
  background: var(--ink);
}
.fail .fill {
  background: var(--red);
}
.goal {
  position: absolute;
  top: -6px;
  bottom: -6px;
  width: 0;
  border-left: 2px solid var(--ink);
  transform: translateX(-1px);
}
.goal.dashed {
  border-left-style: dashed;
}
.val {
  display: flex;
  align-items: center;
  gap: 6px;
  font-family: var(--sans);
  font-size: 20px;
  font-variant-numeric: lining-nums tabular-nums;
  color: var(--ink);
  transition: opacity 0.2s;
}
.num {
  min-width: 50px;
}
.fail .val {
  color: var(--red);
}
.tick {
  flex: none;
  fill: none;
  stroke: var(--ink);
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}
</style>
