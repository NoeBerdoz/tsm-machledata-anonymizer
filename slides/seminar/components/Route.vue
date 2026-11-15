<script setup lang="ts">
// Slide 13: the roadmap set on the Poya path. The herd and its armailli stand at today's
// milestone and glide up the path one milestone per click:
//   0  baselines, today   1  the fine-tuned teacher   2  the pipeline   3  the students
//   4  the final talk
// Each milestone is named by what it delivers. When the herd reaches it, its label turns from
// grey to ink and the heart on its post pops red. A reached heart stays red: at click n, the
// hearts of stations 0 to n are red.
// Dates: docs/project-management.md (16 November, 30 November, around 10 December, and
// mid-December for the final talk, to confirm) and goal O5 (the pipeline by 7 December 2026).
import { computed } from 'vue'
import PoyaPath, { POYA_STATIONS } from './art/PoyaPath.vue'
import { useBeats, linear, type Channels, type Ease, type Seg } from './lib/beats'

// The CSS "ease" curve: the herd starts moving at once, speeds up, and settles at the station
const ease: Ease = (t) => {
  const x = (s: number) => 3 * 0.25 * s * (1 - s) ** 2 + 3 * 0.25 * s * s * (1 - s) + s ** 3
  const y = (s: number) => 3 * 0.1 * s * (1 - s) ** 2 + 3 * 1 * s * s * (1 - s) + s ** 3
  let lo = 0
  let hi = 1
  for (let i = 0; i < 24; i++) {
    const mid = (lo + hi) / 2
    if (x(mid) < t) lo = mid
    else hi = mid
  }
  return y((lo + hi) / 2)
}

const W = 1280
const H = (W * 260) / 1280

const stops = [
  { name: 'Baselines measured', date: '16 Nov., today' },
  { name: 'Teacher fine-tuned', date: '30 Nov.' },
  { name: 'Pipeline working', date: '7 Dec.' },
  { name: 'Student distilled, then quantized', date: 'About 10 Dec.' },
  { name: 'Final talk and report', date: 'Mid-Dec., to confirm' },
]
const LAST = stops.length - 1

function target(n: number): Channels {
  const k = Math.min(n, LAST)
  const c: Channels = { pos: k }
  stops.forEach((_, i) => {
    c['l' + i] = i <= k ? 1 : 0
    c['h' + i] = i <= k ? 1 : 0
  })
  return c
}
// One click: the herd glides to the next station, the label lights when it arrives, and the
// heart pops as the lead armailli stops: it peaks at 1,200 ms and is still by 1,800 ms
const beats: Record<number, Seg[]> = {}
for (let n = 1; n <= LAST; n++) {
  beats[n] = [
    { k: 'pos', to: n, at: 0, dur: 1400, ease },
    { k: 'l' + n, to: 1, at: 1000, dur: 400 },
    { k: 'h' + n, to: 1, at: 1050, dur: 750, ease: linear },
  ]
}
const { ch, fade } = useBeats({ target, beats })
const hearts = computed(() => stops.map((_, i) => ch['h' + i]))

// distance from a station down to the label row, in px
const drop = (i: number) => H - (POYA_STATIONS[i].top / 100) * H + 18
</script>

<template>
  <div class="route" :style="{ width: W + 'px', opacity: fade }">
    <PoyaPath :at="ch.pos" :hearts="hearts">
      <template #station="{ index }">
        <div class="label-wrap" :style="{ transform: `translateY(${drop(index)}px)`, opacity: 0.42 + 0.58 * ch['l' + index] }">
          <div class="name">{{ stops[index].name }}</div>
          <div class="date">{{ stops[index].date }}</div>
        </div>
      </template>
    </PoyaPath>
  </div>
</template>

<style scoped>
.route {
  position: relative;
  margin-left: calc(-1 * var(--margin));
  padding-bottom: 128px;
}
.label-wrap {
  width: 184px;
  text-align: center;
  color: var(--ink);
}
.name {
  font-size: 20px;
  font-weight: 500;
  line-height: 1.22;
  text-wrap: balance;
}
.date {
  margin-top: 4px;
  font-size: 18px;
  font-variant-numeric: lining-nums tabular-nums;
  color: var(--muted);
}
</style>
