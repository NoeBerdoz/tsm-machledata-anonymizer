<script setup lang="ts">
// Slide 14: the answer of slide 2 comes back from the cloud AI with a placeholder, and our app
// puts the real value back on the laptop.
//   0  "Dear <PERSON_1>, please sign and return your contract.", as the cloud AI wrote it
//   1  the placeholder gives way to the real name, in red: a real personal value
// The slot between the words takes the width of what it shows, so the line closes up smoothly.
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useBeats } from './lib/beats'

const { ch, fade } = useBeats({
  target: (n) => ({ v: n >= 1 ? 1 : 0 }),
  beats: { 1: [{ k: 'v', to: 1, at: 0, dur: 700 }] },
})

const chipEl = ref<HTMLElement>()
const realEl = ref<HTMLElement>()
const wChip = ref(0)
const wReal = ref(0)
function read() {
  wChip.value = chipEl.value?.offsetWidth ?? 0
  wReal.value = realEl.value?.offsetWidth ?? 0
}
// A slide that mounts while hidden reports zero widths until it is shown, so measure again
// whenever the spans get a size
let ro: ResizeObserver | undefined
onMounted(async () => {
  if (typeof document !== 'undefined' && document.fonts) await document.fonts.ready
  await nextTick()
  read()
  if (typeof ResizeObserver !== 'undefined') {
    ro = new ResizeObserver(read)
    if (chipEl.value) ro.observe(chipEl.value)
    if (realEl.value) ro.observe(realEl.value)
  }
})
onBeforeUnmount(() => ro?.disconnect())

const slotW = computed(() => (wChip.value && wReal.value ? `${wChip.value + (wReal.value - wChip.value) * ch.v}px` : undefined))
const on = (v: number) => ({ opacity: v, visibility: v > 0.001 ? ('visible' as const) : ('hidden' as const) })
</script>

<template>
  <div class="answer" :style="{ opacity: fade }">
    <p class="where eyebrow">
      <span :style="on(1 - ch.v)">The answer from the cloud AI</span>
      <span :style="on(ch.v)">The same answer, back on your laptop</span>
    </p>
    <p class="sentence">
      Dear
      <span class="slot" :style="{ width: slotW }"><span ref="chipEl" class="ph chip" :style="{ ...on(1 - ch.v), transform: `scale(${1 - 0.08 * ch.v})` }">&lt;PERSON_1&gt;</span><span ref="realEl" class="real" :style="on(ch.v)">Marie Dupont</span></span>, please sign<br />and return your contract.
    </p>
  </div>
</template>

<style scoped>
.where {
  position: relative;
  height: 18px;
  margin-bottom: 14px;
}
.where span {
  position: absolute;
  left: 0;
  top: 0;
  white-space: nowrap;
}
.sentence {
  font-size: var(--fs-head);
  line-height: 1.4;
  font-weight: 400;
  letter-spacing: -0.008em;
  color: var(--ink);
  max-width: 1080px;
}
.slot {
  position: relative;
  display: inline-block;
  white-space: nowrap;
  vertical-align: baseline;
}
.real {
  display: inline-block;
  color: var(--red);
}
.chip {
  position: absolute;
  left: 0;
  top: 52%;
  translate: 0 -50%;
  transform-origin: left center;
  line-height: 1.1;
}
</style>
