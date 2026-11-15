<script setup lang="ts">
// One prompt, one true entity, three ways to mask it. Recall and character precision are
// computed from the character offsets below, so the numbers match the drawing. As in our
// evaluation, spaces are never counted. The name is the one of slide 2: our regex finds no
// names, so only the model can protect it.
// Red has one meaning here: the characters that leak, and the verdict that names them.
import { computed } from 'vue'

const props = withDefaults(defineProps<{ step?: number }>(), { step: 0 })

const line = 'Write a contract reminder to Marie Dupont.'
const gold = 'Marie Dupont'
const g0 = line.indexOf(gold)
const g1 = g0 + gold.length

type Case = { key: string; mask: [number, number]; verdict: string; leak?: boolean; from: number }
const cases: Case[] = [
  { key: 'Fully masked', mask: [g0, g1], verdict: 'Protected', from: 1 },
  { key: 'Surname visible', mask: [g0, g0 + 'Marie'.length], verdict: 'Leak', leak: true, from: 2 },
  { key: 'Whole line masked', mask: [0, line.length], verdict: 'Over-masked', from: 3 },
]

// the non-whitespace characters of line[a, b)
const solid = (a: number, b: number) => (b > a ? line.slice(a, b).replace(/\s/g, '').length : 0)
const goldSolid = solid(g0, g1)

function metrics(c: Case) {
  const [m0, m1] = c.mask
  const masked = solid(m0, m1)
  const goldMasked = solid(Math.max(m0, g0), Math.min(m1, g1))
  return {
    recall: goldMasked === goldSolid ? '1 / 1' : '0 / 1',
    prec: `${goldMasked} / ${masked} = ${(goldMasked / masked).toFixed(2)}`,
  }
}
// where the visible part of the entity starts: after the mask, without the space
function leakFrom(c: Case) {
  const rest = line.slice(c.mask[1], g1)
  return c.mask[1] + rest.length - rest.trimStart().length
}
// The line cut into pieces, so the characters that stay visible inside the entity print in red
function pieces(c: Case) {
  if (!c.leak) return [{ t: line, leak: false }]
  const a = leakFrom(c)
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
      <span>Example: from the prompt of slide 2</span><span /><span>Recall</span><span>Character precision<span class="k-sub">personal / masked</span></span>
    </div>

    <div class="row gold">
      <div class="text">
        <span class="txt">{{ line }}</span>
        <span class="cutbox" :style="{ left: g0 + 'ch', width: g1 - g0 + 'ch' }" />
      </div>
      <div class="gloss">True entity: a person. Spaces do not count.</div>
    </div>

    <div v-for="r in rows" :key="r.key" class="row" :class="{ on: step >= r.from }">
      <div class="text">
        <span class="txt"><span v-for="(p, i) in r.parts" :key="i" :class="{ leaked: p.leak }">{{ p.t }}</span></span>
        <span class="inkbar" :style="{ left: r.mask[0] + 'ch', width: r.mask[1] - r.mask[0] + 'ch' }" />
        <span v-if="r.leak" class="leakbox" :style="{ left: leakFrom(r) + 'ch', width: g1 - leakFrom(r) + 'ch' }" />
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
/* the red box frames the visible part with the same air as the dashed box of the true entity */
.leakbox {
  border: 1.5px solid var(--red);
  margin-left: -4px;
  padding-right: 6px;
  box-sizing: content-box;
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
