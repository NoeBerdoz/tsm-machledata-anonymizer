<script setup lang="ts">
// GLiNER2-PII, measured from its safetensors header.
// step 1 shows where the parameters are.
import { computed } from 'vue'

const props = withDefaults(defineProps<{ step?: number }>(), { step: 0 })
const s = computed(() => props.step)

const total = 307
const emb = 192
const W = 1136
const embW = Math.round((W * emb) / total)
</script>

<template>
  <div class="teacher">
    <div class="grid12 facts">
      <div class="fact" style="grid-column: 1 / span 3">
        <div class="num">307M</div>
        <div class="label muted">parameters</div>
      </div>
      <div class="fact" style="grid-column: 4 / span 3">
        <div class="num">1.23 GB</div>
        <div class="label muted">in float32</div>
      </div>
      <div class="fact" style="grid-column: 7 / span 3">
        <div class="num">42</div>
        <div class="label muted">entity types</div>
      </div>
      <div class="caption src" style="grid-column: 10 / span 3">Read from the safetensors header</div>
    </div>

    <div class="split">
      <div class="seg-labels label">
        <span class="step" :class="{ on: s >= 1 }" :style="{ width: embW + 'px' }">Word embeddings <span class="mono">192M, 63 %</span></span>
        <span class="step" :class="{ on: s >= 1 }">Encoder and heads <span class="mono">115M</span></span>
      </div>
      <div class="bar">
        <span class="fill" :class="{ on: s >= 1 }" :style="{ width: embW + 'px' }" />
        <span class="tick" :class="{ on: s >= 1 }" :style="{ left: embW + 'px' }" />
      </div>
      <div class="caption step" :class="{ on: s >= 1 }">Vocabulary of <span class="mono">250,112</span> tokens</div>
    </div>

    <p class="point lede step" :class="{ on: s >= 1 }">Most of the model is a dictionary.</p>
  </div>
</template>

<style scoped>
.teacher {
  width: 1136px;
  margin-top: 80px;
}
.facts {
  align-items: end;
}
.num {
  font-size: var(--fs-cover);
  line-height: 1;
  font-weight: 400;
  letter-spacing: -0.02em;
}
.fact .label {
  margin-top: 8px;
}
.src {
  align-self: end;
  padding-bottom: 4px;
}
.split {
  margin-top: 104px;
}
.seg-labels {
  display: flex;
  margin-bottom: 8px;
}
.seg-labels > span + span {
  padding-left: 8px;
}
.seg-labels .mono {
  margin-left: 8px;
  color: var(--graphite);
}
.bar {
  position: relative;
  height: 40px;
  border: 1px solid var(--ink);
}
.fill {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  background: var(--graphite);
  transform-origin: left center;
  transform: scaleX(0);
  transition: transform var(--t-slow) var(--ease);
}
.fill.on {
  transform: scaleX(1);
}
.tick {
  position: absolute;
  top: -16px;
  bottom: -1px;
  border-left: 1px solid var(--ink);
  opacity: 0;
  transition: opacity var(--t-fast) var(--ease);
}
.tick.on {
  opacity: 1;
}
.split > .caption {
  margin-top: 8px;
}
.point {
  margin-top: 56px;
}
</style>
