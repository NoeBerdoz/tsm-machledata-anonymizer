<script setup lang="ts">
// The size path, as a cumulative waterfall. Only the fp32 size is measured.
// The rest are estimates from parameter counts. step n shows rows 0..n.
import { computed } from 'vue'

const props = withDefaults(defineProps<{ step?: number }>(), { step: 0 })

const rows = [
  { name: 'fp32 teacher', mb: 1230, label: '1.23 GB', measured: true, note: '' },
  { name: 'int8', mb: 307, label: 'about 0.31 GB', measured: false, note: '' },
  { name: '+ pruned vocabulary', mb: 150, label: 'about 150 MB', measured: false, note: '' },
  { name: '+ six-layer student', mb: 100, label: 'about 100 MB', measured: false, note: 'O3 target, needs the pruned vocabulary', target: true },
  { name: '+ int4', mb: 55, label: 'about 55 MB', measured: false, note: 'option' },
]
const MAX = 459
const w = (mb: number) => Math.max(2, (mb / 1230) * MAX)
const shown = computed(() => rows.map((_, i) => props.step >= i))
</script>

<template>
  <div class="path">
    <div v-for="(r, i) in rows" :key="r.name" class="row" :class="{ on: shown[i], target: r.target }">
      <div class="name label">{{ r.name }}</div>
      <div class="barcell">
        <span class="bar" :class="r.measured ? 'solid' : 'dashed'" :style="{ width: w(r.mb) + 'px' }" />
        <span class="size mono" :style="{ left: w(r.mb) + 16 + 'px' }">{{ r.label }}</span>
      </div>
      <div class="note caption">{{ r.note }}</div>
    </div>
    <div class="legend caption">
      <span class="sw solid" />measured
      <span class="sw dashed" />estimate
    </div>
  </div>
</template>

<style scoped>
.path {
  width: 1136px;
}
.row {
  display: grid;
  grid-template-columns: calc(3 * var(--col) + 3 * var(--gutter)) calc(5 * var(--col) + 5 * var(--gutter)) 1fr;
  align-items: center;
  height: 64px;
  border-top: 1px solid var(--hairline);
  opacity: 0;
  transition: opacity var(--t-fast) var(--ease);
}
.row.on {
  opacity: 1;
}
.row:nth-last-child(2) {
  border-bottom: 1px solid var(--hairline);
}
.barcell {
  position: relative;
  height: 32px;
}
.bar {
  position: absolute;
  left: 0;
  top: 0;
  height: 32px;
  box-sizing: border-box;
}
.bar {
  transform-origin: left center;
  transform: scaleX(1);
  transition: transform var(--t-slow) var(--ease);
}
.row:not(.on) .bar {
  transform: scaleX(0);
}
.bar.solid {
  background: var(--graphite);
}
.bar.dashed {
  border: 1px dashed var(--ink);
}
.size {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  font-size: var(--fs-body);
  white-space: nowrap;
}
.note {
  text-align: right;
}
.target .note {
  color: var(--ink);
}
.legend {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 24px;
}
.sw {
  display: inline-block;
  width: 24px;
  height: 12px;
  box-sizing: border-box;
}
.sw.solid {
  background: var(--graphite);
}
.sw.dashed {
  border: 1px dashed var(--ink);
  margin-left: 16px;
}
</style>
