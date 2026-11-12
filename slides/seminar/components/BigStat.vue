<script setup lang="ts">
// One figure and its caption. The figure is set narrow with tabular digits; the caption sits
// beside or under it.
//   progress  0 to 1, how far the number has counted up; leave it out to show the value
//   alert     red, for a danger figure only
//   side      the caption beside the figure instead of under it
//   <BigStat :value="48" suffix="%" side>of employees report ...</BigStat>
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{ value: number; suffix?: string; decimals?: number; progress?: number; size?: number; alert?: boolean; side?: boolean }>(),
  { suffix: '', decimals: 0, progress: 1, size: 96, alert: false, side: false },
)
const shown = computed(() => (props.value * Math.max(0, Math.min(1, props.progress))).toFixed(props.decimals))
</script>

<template>
  <div class="stat" :class="{ side }">
    <div class="v" :class="{ alert }" :style="{ fontSize: size + 'px' }">
      <span class="n">{{ shown }}</span><span class="u">{{ suffix }}</span>
    </div>
    <div class="k"><slot /></div>
  </div>
</template>

<style scoped>
.stat {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.stat.side {
  flex-direction: row;
  align-items: center;
  gap: 32px;
}
.v {
  flex: none;
  font-family: var(--sans);
  font-weight: 500;
  font-stretch: var(--fig-stretch);
  line-height: 0.9;
  letter-spacing: -0.035em;
  color: var(--ink);
  font-variant-numeric: lining-nums tabular-nums;
}
.v.alert {
  color: var(--red);
}
.u {
  font-size: 0.62em;
  letter-spacing: 0;
  margin-left: 0.04em;
}
.k {
  font-family: var(--sans);
  font-size: 26px;
  line-height: 1.32;
  color: var(--ink);
}
</style>
