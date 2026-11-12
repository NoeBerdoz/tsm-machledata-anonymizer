<script setup lang="ts">
// Slide 10: the five goals as five columns, read left to right. The slide opens on the five
// names; each click fills one goal with its target figure and what the figure means.
//   0  O1 to O5, names only
//   n  goal n gets its rule, its figure, its caption and its second condition (n = 1 to 5)
// The end state is the readable summary of all five targets.
import { useBeats, inOutCubic, type Channels, type Seg } from './lib/beats'
import { goals } from '../data/goals'

const N = goals.length

function target(n: number): Channels {
  const c: Channels = {}
  for (let i = 0; i < N; i++) {
    const on = i < n ? 1 : 0
    c['r' + i] = on
    c['f' + i] = on
    c['c' + i] = on
    c['m' + i] = on
  }
  return c
}
// One goal: the rule draws under its name, then the figure, the caption and the second line
// rise in, all within a second
const fill = (i: number): Seg[] => [
  { k: 'r' + i, to: 1, at: 0, dur: 420, ease: inOutCubic },
  { k: 'f' + i, to: 1, at: 40, dur: 460 },
  { k: 'c' + i, to: 1, at: 240, dur: 420 },
  { k: 'm' + i, to: 1, at: 420, dur: 420 },
]
const beats: Record<number, Seg[]> = {}
for (let i = 0; i < N; i++) beats[i + 1] = fill(i)

const { ch, fade } = useBeats({ target, beats })

const split = (s: string) => {
  const m = s.match(/^(\d+)\s?(.*)$/)
  return m ? { n: m[1], u: m[2] } : { n: s, u: '' }
}
const figs = goals.map((g) => split(g.figure))
const rise = (v: number, d = 12) => ({
  opacity: v,
  visibility: v > 0.001 ? ('visible' as const) : ('hidden' as const),
  transform: `translateY(${(1 - v) * d}px)`,
})
</script>

<template>
  <div class="goals" :style="{ opacity: fade }">
    <div v-for="(g, i) in goals" :key="g.id" class="goal">
      <div class="id mono">{{ g.id }}</div>
      <div class="name">{{ g.name }}</div>
      <div class="rule"><span class="ink" :style="{ transform: `scaleX(${ch['r' + i]})` }" /></div>
      <div class="fig figure-num" :style="rise(ch['f' + i], 18)">
        <span class="n">{{ figs[i].n }}</span><span v-if="figs[i].u" class="u">{{ figs[i].u }}</span>
      </div>
      <p class="cap" :style="rise(ch['c' + i])">{{ g.caption }}</p>
      <p v-if="g.more" class="more" :style="rise(ch['m' + i], 8)">{{ g.more }}</p>
    </div>
  </div>
</template>

<style scoped>
.goals {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  column-gap: 24px;
  width: 1136px;
  margin-top: 72px;
}
.id {
  font-size: 15px;
  letter-spacing: 0.12em;
  color: var(--muted-2);
}
.name {
  margin-top: 4px;
  font-size: 26px;
  font-weight: 500;
  line-height: 1.15;
  letter-spacing: -0.008em;
  color: var(--ink);
}
.rule {
  position: relative;
  height: 2px;
  margin: 16px 0 22px;
  background: var(--hair);
}
.rule .ink {
  position: absolute;
  inset: 0;
  background: var(--ink);
  transform-origin: left center;
}
.fig {
  font-size: 92px;
  line-height: 0.9;
  letter-spacing: -0.035em;
  color: var(--ink);
  white-space: nowrap;
}
.fig .u {
  font-size: 0.5em;
  letter-spacing: 0;
  margin-left: 0.08em;
}
.cap {
  margin-top: 18px;
  font-size: 20px;
  line-height: 1.3;
  color: var(--ink);
  text-wrap: balance;
}
.more {
  margin-top: 10px;
  font-size: 18px;
  line-height: 1.3;
  color: var(--muted);
}
</style>
