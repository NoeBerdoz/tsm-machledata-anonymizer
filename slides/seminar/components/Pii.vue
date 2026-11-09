<script setup lang="ts">
// One sensitive span with the three marks of the deck.
// state 0 = plain text, 1 = detected (dashed cut line drawn around it),
// 2 = cut out (ink bar), 3 = replaced (mono chip).
// leak = the cut line is drawn in signal red.
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'

const props = withDefaults(defineProps<{ state?: number; chip: string; leak?: boolean }>(), {
  state: 0,
  leak: false,
})

const real = ref<HTMLElement>()
const chipEl = ref<HTMLElement>()
const wReal = ref(0)
const wChip = ref(0)

// Measure again whenever the spans get a size: a slide that mounts while hidden
// reports zero widths until it is shown.
function read() {
  wReal.value = real.value?.offsetWidth ?? 0
  wChip.value = chipEl.value?.offsetWidth ?? 0
}
let ro: ResizeObserver | undefined
onMounted(async () => {
  if (typeof document !== 'undefined' && document.fonts) await document.fonts.ready
  await nextTick()
  read()
  if (typeof ResizeObserver !== 'undefined') {
    ro = new ResizeObserver(read)
    if (real.value) ro.observe(real.value)
    if (chipEl.value) ro.observe(chipEl.value)
  }
})
onBeforeUnmount(() => ro?.disconnect())

const width = computed(() => {
  if (!wReal.value || !wChip.value) return undefined
  return `${props.state >= 3 ? wChip.value : wReal.value}px`
})
</script>

<template>
  <span class="pii" :class="[`s${state}`, { leak }]" :style="{ width }">
    <span ref="real" class="real"><slot /></span>
    <svg class="cut" aria-hidden="true"><rect x="1" y="1" rx="2" /></svg>
    <span class="bar" aria-hidden="true" />
    <span ref="chipEl" class="chip">{{ chip }}</span>
  </span>
</template>

<style scoped>
.pii {
  position: relative;
  display: inline-block;
  white-space: nowrap;
  vertical-align: baseline;
  transition: width var(--t-mid) var(--ease);
}
.real {
  position: relative;
  z-index: 1;
  display: inline-block;
  transition: opacity var(--t-fast) var(--ease);
}
.cut {
  position: absolute;
  left: -0.14em;
  top: 0.06em;
  width: calc(100% + 0.28em);
  height: calc(100% - 0.02em);
  overflow: visible;
  pointer-events: none;
  clip-path: inset(-4px 100% -4px -4px);
  transition: clip-path var(--t-mid) var(--ease), opacity var(--t-fast) var(--ease);
}
.cut rect {
  width: calc(100% - 2px);
  height: calc(100% - 2px);
  fill: none;
  stroke: currentColor;
  stroke-width: 1.25;
  stroke-dasharray: 4 3;
}
.bar {
  position: absolute;
  left: -0.08em;
  right: -0.08em;
  top: 0.14em;
  bottom: 0.04em;
  background: var(--ink);
  z-index: 2;
  transform-origin: left center;
  transform: scaleX(0);
  pointer-events: none;
  transition: transform var(--t-mid) var(--ease), opacity var(--t-fast) var(--ease);
}
.chip {
  position: absolute;
  left: 0;
  top: 50%;
  z-index: 3;
  transform: translateY(-46%);
  font-family: var(--mono);
  font-size: var(--chip-size, 0.62em);
  font-weight: 400;
  line-height: 1;
  padding: 0.3em 0.42em 0.28em;
  border: 1px solid var(--ink);
  border-radius: 3px;
  background: var(--paper);
  color: var(--ink);
  opacity: 0;
  transition: opacity var(--t-fast) var(--ease);
}

.s1 .cut { clip-path: inset(-4px -4px -4px -4px); }
.s2 .cut { clip-path: inset(-4px -4px -4px -4px); opacity: 0; }
.s2 .bar { transform: scaleX(1); }
.s2 .real { opacity: 0; transition-delay: 120ms; }
.s3 .real { opacity: 0; }
.s3 .bar { transform: scaleX(1); opacity: 0; }
.s3 .chip { opacity: 1; transition-delay: 80ms; }

.leak .cut { color: var(--red); }
</style>
