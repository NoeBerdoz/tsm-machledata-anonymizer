<script setup lang="ts">
// Slide 11: the first baselines, before any training, as one table with bars to scale.
//   0  T1 (OpenPII-1M, 1,000 texts): recall, character precision and size of four detectors;
//      GLiNER2-PII, our teacher, finds the most
//   1  a dashed extension shows where GLiNER2-PII stands without the 5 types it has no label for
//   2  our Swiss set: the regex and a model together, two more rows, pass the 99 % goal of O1
// Every bar starts at zero. Red is not used: the slide's one red is the headline's emphasis.
import { useBeats, inOutCubic, type Channels, type Seg } from './lib/beats'
import { detectors, gliner2KnownTypes, swissGoal } from '../data/baseline'

const singles = detectors.filter((d) => !d.combo)
const combos = detectors.filter((d) => d.combo)
const rows = [...singles, ...combos]

function target(n: number): Channels {
  return { ghost: n >= 1 ? 1 : 0, legend: n >= 1 ? 1 : 0, swiss: n >= 2 ? 1 : 0, grow: n >= 2 ? 1 : 0, combos: n >= 2 ? 1 : 0, checks: n >= 2 ? 1 : 0 }
}
const beats: Record<number, Seg[]> = {
  1: [
    { k: 'ghost', to: 1, at: 0, dur: 600 },
    { k: 'legend', to: 1, at: 200, dur: 420 },
  ],
  2: [
    { k: 'swiss', to: 1, at: 0, dur: 300 },
    { k: 'combos', to: 1, at: 0, dur: 380 },
    { k: 'grow', to: 1, at: 150, dur: 900, ease: inOutCubic },
    { k: 'checks', to: 1, at: 1050, dur: 300 },
  ],
}
const { ch, fade } = useBeats({ target, beats })

const TRACK = 210
const SW_TRACK = 170
const pct = (v: number) => v.toFixed(1) + ' %'
const mb = (v: number | null) => (v == null ? 'rules only' : v.toLocaleString('en-US') + ' MB')
const vis = (v: number) => ({ opacity: v, visibility: v > 0.001 ? ('visible' as const) : ('hidden' as const) })
const rowStyle = (combo?: boolean) => (combo ? { ...vis(ch.combos), transform: `translateY(${(1 - ch.combos) * 8}px)` } : {})
const passes = (v: number) => v >= swissGoal
</script>

<template>
  <div class="base" :style="{ opacity: fade }">
    <!-- the two groups of columns -->
    <div class="grid groups">
      <span />
      <span class="group">T1 candidate: 1,000 public texts, OpenPII-1M</span>
      <span class="group" :style="vis(ch.swiss)">Swiss set: 781 fake Swiss IDs</span>
      <span />
    </div>
    <div class="grid head">
      <span />
      <span class="eyebrow">Recall</span>
      <span class="eyebrow">Character precision</span>
      <span class="eyebrow" :style="vis(ch.swiss)">Recall, goal {{ swissGoal }} %</span>
      <span class="eyebrow size-h">Size</span>
    </div>

    <div v-for="d in rows" :key="d.key" class="grid row" :class="{ lead: d.key === 'gliner2', combo: d.combo }" :style="rowStyle(d.combo)">
      <span class="name">{{ d.name }}</span>
      <span class="cell t1">
        <span class="track" :style="{ width: TRACK + 'px' }">
          <span class="fill" :style="{ width: (d.openpii.recall / 100) * TRACK + 'px' }" />
          <span
            v-if="d.key === 'gliner2'"
            class="ghost"
            :style="{
              left: (d.openpii.recall / 100) * TRACK + 'px',
              width: ((gliner2KnownTypes - d.openpii.recall) / 100) * TRACK + 'px',
              transform: `scaleX(${ch.ghost})`,
              opacity: ch.ghost > 0.001 ? 1 : 0,
            }"
          />
        </span>
        <span class="num">{{ pct(d.openpii.recall) }}</span>
      </span>
      <span class="num cp">{{ pct(d.openpii.charPrecision) }}</span>
      <span class="cell" :style="vis(ch.swiss)">
        <span class="track" :style="{ width: SW_TRACK + 'px' }">
          <span class="fill" :class="{ pass: passes(d.swiss.all) }" :style="{ width: (d.swiss.all / 100) * SW_TRACK * ch.grow + 'px' }" />
          <span class="goal" :style="{ left: (swissGoal / 100) * SW_TRACK + 'px' }" />
        </span>
        <span class="num">{{ pct(d.swiss.all) }}</span>
        <svg class="tick" :style="{ opacity: passes(d.swiss.all) ? ch.checks : 0 }" width="16" height="16" viewBox="0 0 14 14" aria-hidden="true"><path d="M2 7.6l3.3 3.2L12.2 3.4" /></svg>
      </span>
      <span class="num size">{{ mb(d.sizeMB) }}</span>
    </div>

    <p class="legend" :style="{ ...vis(ch.legend), transform: `translateY(${(1 - ch.legend) * 8}px)` }">
      <span class="swatch" />
      GLiNER2-PII: {{ gliner2KnownTypes }} % without the 5 types it has no label for, like age and title
    </p>
  </div>
</template>

<style scoped>
.base {
  position: relative;
  width: 1136px;
  margin-top: 34px;
}
.grid {
  display: grid;
  grid-template-columns: 240px 310px 140px 310px 1fr;
  column-gap: 0;
  align-items: center;
}
.groups {
  align-items: end;
}
.group {
  font-size: 18px;
  line-height: 1.3;
  color: var(--ink);
  padding-bottom: 8px;
  margin-right: 24px;
  border-bottom: 1px solid var(--ink);
}
.groups .group:nth-child(2) {
  grid-column: 2 / span 2;
}
.head {
  padding: 10px 0 6px;
  border-bottom: 1px solid var(--hair);
}
.row {
  height: 46px;
  border-bottom: 1px solid rgba(22, 22, 22, 0.07);
}
.name {
  font-size: 20px;
  color: var(--ink);
}
.cell {
  display: flex;
  align-items: center;
  gap: 12px;
}
.track {
  position: relative;
  display: block;
  height: 12px;
  background: var(--wash);
  border-radius: 2px;
}
.fill {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  border-radius: 2px;
  background: rgba(22, 22, 22, 0.4);
}
.lead .t1 .fill,
.fill.pass {
  background: var(--ink);
}
.ghost {
  position: absolute;
  top: -3px;
  bottom: -3px;
  border: 1.5px dashed var(--ink);
  border-left: none;
  border-radius: 0 2px 2px 0;
  transform-origin: left center;
}
.goal {
  position: absolute;
  top: -6px;
  bottom: -6px;
  width: 0;
  border-left: 2px solid var(--ink);
  transform: translateX(-1px);
}
.num {
  font-family: var(--sans);
  font-size: 20px;
  font-variant-numeric: lining-nums tabular-nums;
  color: var(--ink);
  white-space: nowrap;
}
.cell .num {
  min-width: 64px;
}
.tick {
  flex: none;
  margin-left: -4px;
  fill: none;
  stroke: var(--ink);
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.size-h {
  justify-self: end;
}
.size {
  justify-self: end;
  color: var(--muted);
}
.legend {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 14px;
  font-size: 18px;
  color: var(--ink);
}
.swatch {
  display: inline-block;
  width: 26px;
  height: 14px;
  border: 1.5px dashed var(--ink);
  border-radius: 2px;
}
</style>
