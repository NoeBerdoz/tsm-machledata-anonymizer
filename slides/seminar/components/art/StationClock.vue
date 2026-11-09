<script setup lang="ts">
// Quantization as a station clock: the minute hand can only stop on one of the 60 marks,
// as a quantized weight can only take a level of the grid. The hand jumps, it never glides.
import { computed } from 'vue'

const props = withDefaults(defineProps<{ minute?: number; hour?: number; size?: number; ink?: string; paper?: string }>(), {
  minute: 0,
  hour: 10,
  size: 140,
  ink: '#161616',
  paper: '#F6F5F1',
})
const m = computed(() => ((Math.round(props.minute) % 60) + 60) % 60)
const minuteAngle = computed(() => m.value * 6)
const hourAngle = computed(() => (props.hour % 12) * 30 + m.value * 0.5)
</script>

<template>
  <svg class="station-clock" viewBox="0 0 140 140" :width="size" :height="size" :style="{ '--pa-ink': ink, '--pa-hole': paper }" role="img" :aria-label="`Station clock with 60 minute marks, minute hand on mark ${m}`">
    <g v-html="BASE" />
    <g :transform="`rotate(${hourAngle} 70 74)`" v-html="HOUR" />
    <g :transform="`rotate(${minuteAngle} 70 74)`" v-html="MINUTE" />
    <g v-html="HUB" />
  </svg>
</template>

<script lang="ts">
const BASE = `<path fill="var(--pa-ink,#161616)" d="m64 2 12 0-2 14-8 0zm8 12 0 8-4 0 0-8zm-60 60a58 58 0 1 1 116 0a58 58 0 1 1 -116 0z"/><path fill="var(--pa-hole,#F6F5F1)" d="m18 74a52 52 0 1 1 104 0a52 52 0 1 1 -104 0z"/><path fill="var(--pa-ink,#161616)" d="m68.2 21.4 3.6 0 0 13.6-3.6 0zm6.6.2 1.4.2-.6 5.9-1.5-.1zm5.4.8 1.5.3-1.3 5.9-1.4-.3zm5.3 1.3 1.5.5-1.9 5.7-1.4-.5zm5.2 1.9 1.4.7-2.5 5.4-1.3-.6zm4 1.9 3.2 1.8-6.8 11.8-3.2-1.8zm5.6 3.5 1.2.9-3.5 4.8-1.2-.8zm4.3 3.4 1.2 1-4.1 4.5-1.1-1zm4 3.8 1 1.2-4.5 4-1-1.1zm3.5 4.3 .9 1.2-4.9 3.5-.8-1.2zm2.6 3.6 1.8 3.2-11.8 6.8-1.8-3.2zm3 5.8 .7 1.4-5.5 2.4-.6-1.3zm2.1 5.1 .5 1.5-5.7 1.8-.5-1.4zm1.5 5.3 .3 1.5-5.9 1.2-.3-1.4zm.9 5.5 .2 1.4-6 .7-.1-1.5zm.4 4.4 0 3.6-13.6 0 0-3.6zm-.2 6.6-.2 1.4-5.9-.6 .1-1.5zm-.8 5.4-.3 1.5-5.9-1.3 .3-1.4zm-1.3 5.3-.5 1.5-5.7-1.9 .5-1.4zm-1.9 5.2-.7 1.4-5.4-2.5 .6-1.3zm-1.9 4-1.8 3.2-11.8-6.8 1.8-3.2zm-3.5 5.6-.9 1.2-4.8-3.5 .8-1.2zm-3.4 4.3-1 1.2-4.5-4.1 1-1.1zm-3.8 4-1.2 1-4-4.5 1.1-1zm-4.3 3.5-1.2.9-3.5-4.9 1.2-.8zm-3.6 2.6-3.2 1.8-6.8-11.8 3.2-1.8zm-5.8 3-1.4.7-2.4-5.5 1.3-.6zm-5.1 2.1-1.5.5-1.8-5.7 1.4-.5zm-5.3 1.5-1.5.3-1.2-5.9 1.4-.3zm-5.5.9-1.4.2-.7-6 1.5-.1zm-4.4.4-3.6 0 0-13.6 3.6 0zm-6.6-.2-1.4-.2 .6-5.9 1.5.1zm-5.4-.8-1.5-.3 1.3-5.9 1.4.3zm-5.3-1.3-1.5-.5 1.9-5.7 1.4.5zm-5.2-1.9-1.4-.7 2.5-5.4 1.3.6zm-4-1.9-3.2-1.8 6.8-11.8 3.2 1.8zm-5.6-3.5-1.2-.9 3.5-4.8 1.2.8zm-4.3-3.4-1.2-1 4.1-4.5 1.1 1zm-4-3.8-1-1.2 4.5-4 1 1.1zm-3.5-4.3-.9-1.2 4.9-3.5 .8 1.2zm-2.6-3.6-1.8-3.2 11.8-6.8 1.8 3.2zm-3-5.8-.7-1.4 5.5-2.4 .6 1.3zm-2.1-5.1-.5-1.5 5.7-1.8 .5 1.4zm-1.5-5.3-.3-1.5 5.9-1.2 .3 1.4zm-.9-5.5-.2-1.4 6-.7 .1 1.5zm-.4-4.4 0-3.6 13.6 0 0 3.6zm.2-6.6 .2-1.4 5.9.6-.1 1.5zm.8-5.4 .3-1.5 5.9 1.3-.3 1.4zm1.3-5.3 .5-1.5 5.7 1.9-.5 1.4zm1.9-5.2 .7-1.4 5.4 2.5-.6 1.3zm1.9-4 1.8-3.2 11.8 6.8-1.8 3.2zm3.5-5.6 .9-1.2 4.8 3.5-.8 1.2zm3.4-4.3 1-1.2 4.5 4.1-1 1.1zm3.8-4 1.2-1 4 4.5-1.1 1zm4.3-3.5 1.2-.9 3.5 4.9-1.2.8zm3.6-2.6 3.2-1.8 6.8 11.8-3.2 1.8zm5.8-3 1.4-.7 2.4 5.5-1.3.6zm5.1-2.1 1.5-.5 1.8 5.7-1.4.5zm5.3-1.5 1.5-.3 1.2 5.9-1.4.3zm5.5-.9 1.4-.2 .7 6-1.5.1z"/>`
const HOUR = `<path fill="var(--pa-ink,#161616)" d="m67.8 44 4.4 0 .4 40-5.2 0z"/>`
const MINUTE = `<path fill="var(--pa-ink,#161616)" d="m68.4 28 3.2 0 .4 58-4 0z"/>`
const HUB = `<path fill="var(--pa-ink,#161616)" d="m65.8 74a4.2 4.2 0 1 1 8.4 0a4.2 4.2 0 1 1 -8.4 0z"/><path fill="var(--pa-hole,#F6F5F1)" d="m68.8 74a1.2 1.2 0 1 1 2.4 0a1.2 1.2 0 1 1 -2.4 0z"/>`
</script>
