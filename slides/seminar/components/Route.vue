<script setup lang="ts">
// The roadmap set on the poya path. Milestones from docs/smart-goals.md.
// The labels hang from the station slot of the drawing and line up in one row under it.
import PoyaPath, { POYA_STATIONS } from './art/PoyaPath.vue'

const props = withDefaults(defineProps<{ progress?: number }>(), { progress: 0 })

const W = 1280
const H = (W * 260) / 1280

const stops = [
  { v: 'v0', date: '16 Nov.', what: 'Baselines, T2 built and split' },
  { v: 'v1', date: 'end of Nov.', what: 'Fine-tuned teacher' },
  { v: 'Pipeline', date: '7 Dec.', what: 'Gate and monitoring work' },
  { v: 'v2, v3', date: 'about 10 Dec.', what: 'Distilled, then quantized student' },
  { v: 'Final', date: 'mid-Dec.', what: 'Final talk, then the report' },
]

// distance from a station down to the label row, in px
const drop = (i: number) => H - (POYA_STATIONS[i].top / 100) * H + 16
</script>

<template>
  <div class="route" :style="{ width: W + 'px' }">
    <PoyaPath :progress="props.progress">
      <template #station="{ index, reached }">
        <div class="label-wrap" :class="{ reached }" :style="{ transform: `translateY(${drop(index)}px)` }">
          <div class="v label">{{ stops[index].v }}</div>
          <div class="date mono">{{ stops[index].date }}</div>
          <div class="what caption">{{ stops[index].what }}</div>
        </div>
      </template>
    </PoyaPath>
  </div>
</template>

<style scoped>
.route {
  position: relative;
  margin-left: calc(-1 * var(--margin));
  padding-bottom: 112px;
}
.label-wrap {
  width: 184px;
  text-align: center;
  color: var(--graphite);
}
.label-wrap.reached {
  color: var(--ink);
}
.label-wrap .v {
  font-weight: 500;
}
.date {
  font-size: var(--fs-caption);
  margin-top: 2px;
}
.what {
  margin-top: 4px;
  color: inherit;
}
</style>
