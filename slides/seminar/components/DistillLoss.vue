<script setup lang="ts">
// Hinton et al. (2015) loss with three short annotations, then the gold-label control of goal O1.
// step 1 draws the control.
import { computed } from 'vue'

const props = withDefaults(defineProps<{ step?: number }>(), { step: 0 })
const s = computed(() => props.step)
</script>

<template>
  <div class="distill">
    <div class="formula">
      <div class="term"><Tex e="\mathcal{L} \;=\;" /></div>
      <div class="term"><Tex e="\alpha\," /></div>
      <div class="term">
        <span class="ann up label">keeps the gradient scale</span>
        <Tex e="\tau^2" />
      </div>
      <div class="term">
        <Tex e="\,\mathrm{KL}\big(p_T^{\tau}\,\|\,p_S^{\tau}\big)" />
        <span class="ann down label">copy the teacher</span>
      </div>
      <div class="term">
        <Tex e="\;+\;(1-\alpha)\,\mathrm{CE}\big(y,\,p_S\big)" />
        <span class="ann down label shift">fit the gold labels</span>
      </div>
    </div>

    <div class="control" :class="{ on: s >= 1 }">
      <svg viewBox="0 0 1136 152" width="1136" height="152" class="lanes">
        <defs>
          <marker id="dl-ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto">
            <path d="M1 1 L9 5 L1 9" fill="none" stroke="var(--ink)" stroke-width="1.2" />
          </marker>
        </defs>
        <text x="0" y="26" class="t-lab">Teacher</text>
        <text x="0" y="122" class="t-lab">Gold labels</text>

        <path class="lane" d="M 112 20 H 476" marker-end="url(#dl-ah)" />
        <path class="lane" d="M 128 116 H 476" marker-end="url(#dl-ah)" />
        <path class="lane" d="M 176 116 V 56 H 476" marker-end="url(#dl-ah)" />
        <circle cx="176" cy="116" r="3" fill="var(--ink)" />

        <text x="492" y="44" class="t-lab">Distilled student</text>
        <text x="492" y="122" class="t-lab">Control student</text>

        <path d="M 684 18 H 692 V 130 H 684" fill="none" stroke="var(--ink)" stroke-width="1" />
        <text x="716" y="70" class="t-lab">Same architecture,</text>
        <text x="716" y="94" class="t-lab">data and budget</text>
      </svg>
      <p class="lede verdict">Distillation must beat the control.</p>
    </div>
  </div>
</template>

<style scoped>
.distill {
  width: 1136px;
  margin-top: 64px;
}
.formula {
  display: flex;
  align-items: baseline;
  font-size: var(--fs-head);
  padding: 48px 0 48px;
}
.term {
  position: relative;
}
.ann {
  position: absolute;
  left: 0;
  white-space: nowrap;
  color: var(--graphite);
  font-family: var(--sans);
  padding-left: 8px;
  border-left: 1px solid var(--hairline);
}
.ann.up {
  bottom: 100%;
  margin-bottom: 4px;
  left: 6px;
}
.ann.down {
  top: 100%;
  margin-top: 6px;
  left: 6px;
}
.ann.shift {
  left: 52px;
}
.control {
  margin-top: 24px;
  padding-top: 24px;
  border-top: 1px solid var(--hairline);
  opacity: 0;
  transition: opacity var(--t-fast) var(--ease);
}
.control.on {
  opacity: 1;
}
.lanes {
  display: block;
  overflow: visible;
}
.t-lab {
  font-family: var(--sans);
  font-size: var(--fs-label);
  fill: var(--ink);
}
.lane {
  fill: none;
  stroke: var(--ink);
  stroke-width: 1;
  stroke-dasharray: 380;
  stroke-dashoffset: 380;
  transition: stroke-dashoffset var(--t-slow) var(--ease) 100ms;
}
.on .lane {
  stroke-dashoffset: 0;
}
.verdict {
  margin-top: 24px;
}
</style>
