<script setup lang="ts">
// One line of an attached CSV file, one true entity, three ways to mask it. Recall and character
// precision are computed from the character offsets below, so the numbers match the drawing.
// Red has one meaning here: the characters that leak, and the verdict that names them.
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
// The line cut into pieces, so the characters that stay visible inside the entity print in red
function pieces(c: Case) {
  if (!c.leak) return [{ t: line, leak: false }]
  const a = c.mask[1]
  return [
    { t: line.slice(0, a), leak: false },
    { t: line.slice(a, g1), leak: true },
    { t: line.slice(g1), leak: false },
  ]
}
const rows = cases.map((c) => ({ ...c, m: metrics(c), parts: pieces(c) }))
const step = computed(() => props.step)
</script>

<template>
  <div class="leak">
    <div class="head">
      <span>Example: payments.csv, in a prompt</span><span /><span>Recall</span><span>Character precision<span class="k-sub">personal / masked</span></span>
    </div>

    <div class="row gold">
      <div class="text">
        <span class="txt">{{ line }}</span>
        <span class="cutbox" :style="{ left: g0 + 'ch', width: g1 - g0 + 'ch' }" />
      </div>
      <div class="gloss">True entity: Swiss IBAN, {{ iban.length }} characters</div>
    </div>

    <div v-for="r in rows" :key="r.key" class="row" :class="{ on: step >= r.from }">
      <div class="text">
        <span class="txt"><span v-for="(p, i) in r.parts" :key="i" :class="{ leaked: p.leak }">{{ p.t }}</span></span>
        <span class="inkbar" :style="{ left: r.mask[0] + 'ch', width: r.mask[1] - r.mask[0] + 'ch' }" />
        <span v-if="r.leak" class="leakbox" :style="{ left: r.mask[1] + 'ch', width: g1 - r.mask[1] + 'ch' }" />
      </div>
      <div class="verdict" :class="{ bad: r.leak }">{{ r.verdict }}</div>
      <div class="num">{{ r.m.recall }}</div>
      <div class="num">{{ r.m.prec }}</div>
    </div>
  </div>
</template>

<style scoped>
.leak {
  width: 1136px;
  margin-top: 44px;
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
  font-size: var(--fs-label);
  line-height: 1.3;
  color: var(--muted-2);
}
.row {
  height: 72px;
  border-bottom: 1px solid var(--hair);
  opacity: 0;
  transition: opacity var(--t-fast) var(--ease);
}
.row.gold,
.row.on {
  opacity: 1;
}
/* the true entity's description spans the three empty cells of its row */
.gloss {
  grid-column: 2 / span 3;
  font-size: var(--fs-label);
  color: var(--muted-2);
  white-space: nowrap;
}
.text {
  position: relative;
  font-family: var(--mono);
  font-size: var(--fs-label);
  white-space: pre;
  line-height: 1;
}
.leaked {
  color: var(--red);
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
.verdict {
  font-size: var(--fs-label);
}
.num {
  font-family: var(--mono);
  font-size: var(--fs-label);
}
.bad {
  color: var(--red);
  font-weight: 500;
}
/* reduced motion: the mask appears with its row's fade, without sweeping */
@media (prefers-reduced-motion: reduce) {
  .inkbar {
    transition: none;
  }
}
.k-sub {
  display: block;
  color: var(--muted);
}
</style>
