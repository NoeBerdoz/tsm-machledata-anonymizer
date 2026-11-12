<script setup lang="ts">
// Slide 13: the roadmap set on the Poya path. The herd and its armailli stand at v0, where we
// are today, and glide up the path one milestone per click:
//   0  v0, today      1  v1      2  the pipeline      3  v2 and v3      4  the final talk
// Each station's label turns from grey to ink when the herd reaches it. The red heart stays on
// today's station: the path shows the plan, today is v0.
// Dates: the GitHub milestones (v0 16.11, v1 30.11, v2 and v3 10.12, final 18.12, to confirm)
// and goal O5 (the pipeline, the gate and the monitoring work by 7 December 2026).
import PoyaPath, { POYA_STATIONS } from './art/PoyaPath.vue'
import { useBeats, type Channels, type Ease, type Seg } from './lib/beats'

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
  { v: 'v0', date: '16 Nov., today', what: 'Baselines measured' },
  { v: 'v1', date: '30 Nov.', what: 'Fine-tuned teacher' },
  { v: 'Pipeline', date: '7 Dec.', what: 'Gate and monitoring work' },
  { v: 'v2, v3', date: '10 Dec.', what: 'Distilled, then quantized student' },
  { v: 'Final', date: '18 Dec.', what: 'Final talk and report, date to confirm' },
]
const LAST = stops.length - 1

function target(n: number): Channels {
  const k = Math.min(n, LAST)
  const c: Channels = { pos: k }
  stops.forEach((_, i) => (c['l' + i] = i <= k ? 1 : 0))
  return c
}
// One click: the herd glides to the next station, and the label lights when it arrives
const beats: Record<number, Seg[]> = {}
for (let n = 1; n <= LAST; n++) {
  beats[n] = [
    { k: 'pos', to: n, at: 0, dur: 1400, ease },
    { k: 'l' + n, to: 1, at: 1000, dur: 400 },
  ]
}
const { ch, fade } = useBeats({ target, beats })

// distance from a station down to the label row, in px
const drop = (i: number) => H - (POYA_STATIONS[i].top / 100) * H + 18
</script>

<template>
  <div class="route" :style="{ width: W + 'px', opacity: fade }">
    <PoyaPath :at="ch.pos" :mark="0">
      <template #station="{ index }">
        <div class="label-wrap" :style="{ transform: `translateY(${drop(index)}px)`, opacity: 0.42 + 0.58 * ch['l' + index] }">
          <div class="v">{{ stops[index].v }}</div>
          <div class="date">{{ stops[index].date }}</div>
          <div class="what">{{ stops[index].what }}</div>
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
.v {
  font-size: 22px;
  font-weight: 500;
  line-height: 1.2;
}
.date {
  margin-top: 2px;
  font-size: 18px;
  font-variant-numeric: lining-nums tabular-nums;
  color: var(--muted);
}
.what {
  margin-top: 6px;
  font-size: 18px;
  line-height: 1.3;
  text-wrap: balance;
}
</style>
