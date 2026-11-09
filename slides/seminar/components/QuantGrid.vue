<script setup lang="ts">
// 40 weights with a normal shape (fixed quantiles, no randomness), quantized to b = 4 bits.
// The grid of 16 levels is shown from the start. step 1 snaps every weight to its level.
import { computed } from 'vue'

const props = withDefaults(defineProps<{ step?: number }>(), { step: 0 })
const s = computed(() => props.step)

// inverse normal CDF (Acklam's rational approximation)
function probit(p: number) {
  const a = [-39.69683028665376, 220.9460984245205, -275.9285104469687, 138.357751867269, -30.66479806614716, 2.506628277459239]
  const b = [-54.47609879822406, 161.5858368580409, -155.6989798598866, 66.80131188771972, -13.28068155288572]
  const c = [-0.007784894002430293, -0.3223964580411365, -2.400758277161838, -2.549732539343734, 4.374664141464968, 2.938163982698783]
  const d = [0.007784695709041462, 0.3224671290700398, 2.445134137142996, 3.754408661907416]
  const pl = 0.02425
  if (p < pl) {
    const q = Math.sqrt(-2 * Math.log(p))
    return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
  }
  if (p > 1 - pl) return -probit(1 - p)
  const q = p - 0.5
  const r = q * q
  return ((((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q) / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)
}

const N = 40
const bits = 4
const L = 2 ** bits
const xs = Array.from({ length: N }, (_, i) => 0.05 * probit((i + 0.5) / N) + 0.012)
const xmin = Math.min(...xs)
const xmax = Math.max(...xs)
const scale = (xmax - xmin) / (L - 1)
const zero = Math.round(-xmin / scale)
const quant = (x: number) => Math.min(Math.max(Math.round(x / scale) + zero, 0), L - 1)
const deq = (q: number) => scale * (q - zero)

const W = 760
const X0 = 56
const X1 = W - 16
const px = (x: number) => X0 + ((x - xmin) / (xmax - xmin)) * (X1 - X0)
const levels = Array.from({ length: L }, (_, q) => ({ q, x: px(deq(q)) }))

// stack the dots from the axis up, like a dot plot, so they do not overlap
const AXIS = 236
const placed: { x: number; row: number }[] = []
const dots = xs.map((x) => {
  const cx = px(x)
  let row = 0
  while (placed.some((p) => p.row === row && Math.abs(p.x - cx) < 46)) row++
  placed.push({ x: cx, row })
  return { x: cx, qx: px(deq(quant(x))), y: AXIS - 16 - row * 20 }
})
const zx = px(deq(zero))
const mid = Math.floor(L / 2)
</script>

<template>
  <svg class="qgrid" :viewBox="`0 0 ${W} 300`" :width="W" height="300">
    <!-- the integer grid -->
    <line v-for="l in levels" :key="l.q" :x1="l.x" :x2="l.x" y1="40" :y2="AXIS" stroke="var(--hairline)" stroke-width="1" />
    <text v-for="l in levels" :key="'t' + l.q" :x="l.x" :y="AXIS + 28" class="t-mono" text-anchor="middle">{{ l.q }}</text>
    <text :x="levels[0].x - 20" :y="AXIS + 28" class="t-mono muted-fill" text-anchor="end">q</text>
    <line :x1="X0 - 8" :x2="X1 + 8" :y1="AXIS" :y2="AXIS" stroke="var(--ink)" stroke-width="1" />
    <text :x="zx" :y="AXIS + 56" class="t-cap" text-anchor="middle">z stores 0.0</text>
    <line :x1="zx" :x2="zx" :y1="AXIS + 34" :y2="AXIS + 40" stroke="var(--graphite)" stroke-width="1" />

    <!-- step size s between two levels -->
    <path :d="`M ${levels[mid].x} 32 V 24 H ${levels[mid + 1].x} V 32`" fill="none" stroke="var(--ink)" stroke-width="1" />
    <text :x="(levels[mid].x + levels[mid + 1].x) / 2" y="16" class="t-mono" text-anchor="middle">s</text>

    <!-- errors, ghosts, weights -->
    <g v-for="(d, i) in dots" :key="i">
      <line class="err" :class="{ on: s >= 1 }" :x1="Math.min(d.x, d.qx)" :x2="Math.max(d.x, d.qx)" :y1="d.y" :y2="d.y" stroke="var(--ink)" stroke-width="2" />
      <circle class="ghost" :class="{ on: s >= 1 }" :cx="d.x" :cy="d.y" r="5" fill="none" stroke="var(--graphite)" stroke-width="1" />
      <circle class="dot" :style="{ transform: `translateX(${s >= 1 ? d.qx - d.x : 0}px)` }" :cx="d.x" :cy="d.y" r="5" fill="var(--graphite)" />
    </g>
  </svg>
</template>

<style scoped>
.qgrid {
  display: block;
  overflow: visible;
}
.t-mono {
  font-family: var(--mono);
  font-size: 15px;
  fill: var(--ink);
}
.t-cap {
  font-family: var(--sans);
  font-size: 15px;
  fill: var(--graphite);
}
.muted-fill {
  fill: var(--graphite);
}
.ghost,
.err {
  opacity: 0;
  transition: opacity var(--t-fast) var(--ease) 300ms;
}
.ghost.on,
.err.on {
  opacity: 1;
}
.dot {
  transition: transform var(--t-slow) var(--ease);
}
</style>
