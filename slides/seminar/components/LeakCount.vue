<script setup lang="ts">
// One line of an attached CSV file, one gold entity, three ways to mask it. Recall and character precision
// are computed from the character offsets below, so the numbers match the drawing.
import { computed } from 'vue'

const props = withDefaults(defineProps<{ step?: number }>(), { step: 0 })

const line = '2026-11-02;INV-4471;CH93 0076 2011 6238 5295 7;1200.00'
const iban = 'CH93 0076 2011 6238 5295 7'
const g0 = line.indexOf(iban)
const g1 = g0 + iban.length

type Case = { key: string; mask: [number, number]; verdict: string; leak?: boolean; from: number }
const cases: Case[] = [
  { key: 'Fully masked', mask: [g0, g1], verdict: 'Protected', from: 1 },
  { key: 'Last digits visible', mask: [g0, g1 - 4], verdict: 'Leak', leak: true, from: 2 },
  { key: 'Whole line masked', mask: [0, line.length], verdict: 'Over-masked', from: 3 },
]

function metrics(c: Case) {
  const [m0, m1] = c.mask
  const masked = m1 - m0
  const goldMasked = Math.max(0, Math.min(m1, g1) - Math.max(m0, g0))
  const protectedAll = m0 <= g0 && m1 >= g1
  return {
    recall: protectedAll ? '1 / 1' : '0 / 1',
    prec: `${goldMasked} / ${masked} = ${(goldMasked / masked).toFixed(2)}`,
  }
}
const rows = cases.map((c) => ({ ...c, m: metrics(c) }))
const step = computed(() => props.step)
</script>

<template>
  <div class="leak">
    <div class="head caption">
      <span>payments.csv, attached to a prompt</span><span /><span>Recall</span><span>Character precision</span>
    </div>

    <div class="row gold">
      <div class="text">
        <span class="txt">{{ line }}</span>
        <span class="cutbox" :style="{ left: g0 + 'ch', width: g1 - g0 + 'ch' }" />
      </div>
      <div class="verdict caption">Gold, Swiss IBAN, <span class="mono">{{ iban.length }}</span> characters</div>
      <div />
      <div />
    </div>

    <div v-for="r in rows" :key="r.key" class="row" :class="{ on: step >= r.from }">
      <div class="text">
        <span class="txt">{{ line }}</span>
        <span class="inkbar" :style="{ left: r.mask[0] + 'ch', width: r.mask[1] - r.mask[0] + 'ch' }" />
        <span v-if="r.leak" class="leakbox" :style="{ left: r.mask[1] + 'ch', width: g1 - r.mask[1] + 'ch' }" />
      </div>
      <div class="verdict label" :class="{ bad: r.leak }">{{ r.verdict }}</div>
      <div class="mono num" :class="{ bad: r.leak }">{{ r.m.recall }}</div>
      <div class="mono num">{{ r.m.prec }}</div>
    </div>
  </div>
</template>

<style scoped>
.leak {
  width: 1136px;
  margin-top: 48px;
}
.head,
.row {
  display: grid;
  grid-template-columns:
    calc(7 * var(--col) + 6 * var(--gutter))
    calc(2 * var(--col) + var(--gutter))
    var(--col)
    calc(2 * var(--col) + var(--gutter));
  align-items: center;
  column-gap: var(--gutter);
}
.head {
  padding-bottom: 8px;
  border-bottom: 1px solid var(--ink);
}
.row {
  height: 72px;
  border-bottom: 1px solid var(--hairline);
  opacity: 0;
  transition: opacity var(--t-fast) var(--ease);
}
.row.gold,
.row.on {
  opacity: 1;
}
.text {
  position: relative;
  font-family: var(--mono);
  font-size: var(--fs-label);
  white-space: pre;
  line-height: 1;
}
.inkbar,
.cutbox,
.leakbox {
  position: absolute;
  top: -6px;
  bottom: -6px;
}
.inkbar {
  background: var(--ink);
  transform-origin: left center;
  transform: scaleX(0);
  transition: transform var(--t-slow) var(--ease) 100ms;
}
.on .inkbar {
  transform: scaleX(1);
}
.cutbox {
  border: 1.25px dashed var(--ink);
  margin-left: -4px;
  padding-right: 6px;
  box-sizing: content-box;
}
.leakbox {
  border: 1.5px solid var(--red);
  margin-left: 1px;
}
.num {
  font-size: var(--fs-label);
}
.bad {
  color: var(--red);
  font-weight: 500;
}
</style>
