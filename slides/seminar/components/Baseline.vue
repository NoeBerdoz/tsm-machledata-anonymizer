<script setup lang="ts">
// The v0 baselines on T2-dev, as a quiet table. Missing values read "pending".
// The recall against character precision plot appears once a baseline has real values.
import { computed } from 'vue'
import { baselines } from '../data/baseline'

const items = baselines.map((b) => ({
  ...b,
  real: !b.placeholder && b.recall != null && b.charPrecision != null,
}))
const plotted = computed(() => items.filter((b) => b.real))
const hasPlot = computed(() => plotted.value.length > 0)
const fmt = (v: number | null) => (v == null ? null : v.toFixed(2))

const P = { x0: 48, x1: 344, y0: 280, y1: 16 }
const sx = (v: number) => P.x0 + v * (P.x1 - P.x0)
const sy = (v: number) => P.y0 - v * (P.y0 - P.y1)
const ticks = [0, 0.5, 1]
</script>

<template>
  <div class="base" :class="{ split: hasPlot }">
    <div class="tbl">
      <div class="thead caption">
        <span>Baseline</span><span>Recall</span><span>Char. precision</span><span>Size</span><span>p95 latency</span>
      </div>
      <div v-for="b in items" :key="b.name" class="trow">
        <div>
          <div class="bname">{{ b.name }}</div>
          <div class="caption">{{ b.detail }}</div>
        </div>
        <span class="mono val" :class="{ pending: fmt(b.recall) == null }">{{ fmt(b.recall) ?? 'pending' }}</span>
        <span class="mono val" :class="{ pending: fmt(b.charPrecision) == null }">{{ fmt(b.charPrecision) ?? 'pending' }}</span>
        <span class="mono val" :class="{ pending: !b.size }">{{ b.size ?? 'pending' }}</span>
        <span class="mono val" :class="{ pending: !b.p95 }">{{ b.p95 ?? 'pending' }}</span>
      </div>
    </div>

    <svg v-if="hasPlot" class="plot" viewBox="0 0 368 320" width="368" height="320">
      <g v-for="t in ticks" :key="t">
        <line :x1="sx(t)" :x2="sx(t)" :y1="P.y0" :y2="P.y1" stroke="var(--hairline)" stroke-width="1" />
        <line :x1="P.x0" :x2="P.x1" :y1="sy(t)" :y2="sy(t)" stroke="var(--hairline)" stroke-width="1" />
        <text :x="sx(t)" :y="P.y0 + 20" class="t-mono" text-anchor="middle">{{ t.toFixed(1) }}</text>
        <text :x="P.x0 - 8" :y="sy(t) + 5" class="t-mono" text-anchor="end">{{ t.toFixed(1) }}</text>
      </g>
      <text :x="P.x1" :y="P.y0 + 40" class="t-cap" text-anchor="end">Character precision</text>
      <text :transform="`translate(${P.x0 - 36} ${P.y1}) rotate(-90)`" class="t-cap" text-anchor="end">Recall</text>
      <g v-for="b in plotted" :key="b.name">
        <circle :cx="sx(b.charPrecision!)" :cy="sy(b.recall!)" r="5" fill="var(--graphite)" />
        <text :x="sx(b.charPrecision!) - 10" :y="sy(b.recall!) + 5" class="t-cap ink" text-anchor="end">{{ b.name }}</text>
      </g>
    </svg>
  </div>
</template>

<style scoped>
.base {
  width: 1136px;
  margin-top: 48px;
}
.base.split {
  display: grid;
  grid-template-columns: calc(8 * var(--col) + 7 * var(--gutter)) 1fr;
  column-gap: var(--gutter);
}
.thead,
.trow {
  display: grid;
  grid-template-columns:
    calc(4 * var(--col) + 3 * var(--gutter))
    repeat(4, 1fr);
  column-gap: var(--gutter);
  align-items: center;
}
.split .thead,
.split .trow {
  grid-template-columns: calc(3 * var(--col) + 2 * var(--gutter)) repeat(4, 1fr);
}
.thead {
  padding-bottom: 8px;
  border-bottom: 1px solid var(--ink);
}
.trow {
  height: 80px;
  border-bottom: 1px solid var(--hairline);
}
.bname {
  font-size: var(--fs-body);
}
.val {
  font-size: var(--fs-label);
}
.val.pending {
  color: var(--graphite);
  font-family: var(--sans);
  font-size: var(--fs-caption);
}
.plot {
  display: block;
  overflow: visible;
}
.t-mono {
  font-family: var(--mono);
  font-size: 15px;
  fill: var(--graphite);
}
.t-cap {
  font-family: var(--sans);
  font-size: 15px;
  fill: var(--graphite);
}
.t-cap.ink {
  fill: var(--ink);
}
</style>
