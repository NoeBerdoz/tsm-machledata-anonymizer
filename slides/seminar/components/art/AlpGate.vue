<script setup lang="ts">
// A wooden alp gate in a short fence. When open, the leaf swings toward the viewer on its hinge.
withDefaults(defineProps<{ open?: boolean; width?: number; ink?: string; paper?: string }>(), {
  open: false,
  width: 200,
  ink: '#161616',
  paper: '#F6F5F1',
})
</script>

<template>
  <svg class="alp-gate" viewBox="0 0 200 100" :width="width" :height="width / 2" :style="{ '--pa-ink': ink, '--pa-hole': paper }" role="img" :aria-label="open ? 'Alp gate, open' : 'Alp gate, closed'">
    <g v-html="BASE" />
    <g class="leaf" :class="{ open }" v-html="LEAF" />
  </svg>
</template>

<script lang="ts">
const BASE = `<path fill="var(--pa-ink,#161616)" d="m5.6 96 .4-40 2-3 2 3 .4 40zm36 0 .4-40 2-3 2 3 .4 40zm112 0 .4-40 2-3 2 3 .4 40zm36 0 .4-40 2-3 2 3 .4 40zm-185.6-33.7 60-1 0 3.4-60 1zm0 17 60-.6 0 3.4-60 .6zm132-17 60-1 0 3.4-60 1zm0 17 60-.6 0 3.4-60 .6zm-74 16.7 0-54 8 0 0 54zm4-61 6 7-12 0zm64 61 0-54 8 0 0 54zm4-61 6 7-12 0zm-134 61 200 0 0 2.6-200 0zm3 0 2-5 1.6 5 1.4-7 1.4 7 1.6-5 2 5zm36 0 2-5 1.6 5 1.4-7 1.4 7 1.6-5 2 5zm18 0 2-5 1.6 5 1.4-7 1.4 7 1.6-5 2 5zm76 0 2-5 1.6 5 1.4-7 1.4 7 1.6-5 2 5zm18 0 2-5 1.6 5 1.4-7 1.4 7 1.6-5 2 5zm36 0 2-5 1.6 5 1.4-7 1.4 7 1.6-5 2 5z"/><path fill="var(--pa-hole,#F6F5F1)" d="m66 52.3c-.6 0-1.8-1.6-2.1-2.2-.3-.6.1-1.5.3-1.7 .3-.3.9-.4 1.1-.3 .3.1.5.9.7.9 .2 0 .4-.8.7-.9 .2-.1.8 0 1.1.3 .2.2.6 1.1.3 1.7-.3.6-1.5 2.2-2.1 2.2zm68 0c-.6 0-1.8-1.6-2.1-2.2-.3-.6.1-1.5.3-1.7 .3-.3.9-.4 1.1-.3 .3.1.5.9.7.9 .2 0 .4-.8.7-.9 .2-.1.8 0 1.1.3 .2.2.6 1.1.3 1.7-.3.6-1.5 2.2-2.1 2.2z"/>`
const LEAF = `<path fill="var(--pa-ink,#161616)" d="m71 48 59 0 0 7-59 0zm0 36 59 0 0 6-59 0zm.1-36 3.8 0 0 42-3.8 0zm9.2 0 3.8 0 0 42-3.8 0zm9.1 0 3.8 0 0 42-3.8 0zm9.2 0 3.8 0 0 42-3.8 0zm9.2 0 3.8 0 0 42-3.8 0zm9.1 0 3.8 0 0 42-3.8 0zm9.2 0 3.8 0 0 42-3.8 0zm-53 37.6 53-35 1.8 2.8-53 35zm-5.1-35.7 12 0 0 3.2-12 0zm0 35.5 12 0 0 3.2-12 0z"/><path fill="var(--pa-hole,#F6F5F1)" d="m100.5 53.9c-.6 0-1.8-1.6-2.1-2.2-.3-.6.1-1.5.3-1.7 .3-.3.9-.4 1.1-.3 .3.1.5.9.7.9 .2 0 .4-.8.7-.9 .2-.1.8 0 1.1.3 .2.2.6 1.1.3 1.7-.3.6-1.5 2.2-2.1 2.2z"/>`
</script>

<style scoped>
.leaf {
  transform-box: view-box;
  transform-origin: 70px 0;
  transition: transform 350ms cubic-bezier(0.3, 0.7, 0.3, 1);
}
.leaf.open {
  transform: scaleX(0.2);
}
@media (prefers-reduced-motion: reduce) {
  .leaf {
    transition: none;
  }
}
</style>
