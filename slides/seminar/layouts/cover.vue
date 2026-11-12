<script setup lang="ts">
// The cover: the title block written in the slide, and the Poya herd along the foot of the
// page, cut in the deck's ink. The herd steps forward once when the talk opens in the main
// view or the presenter view, never in thumbnails or print. art: false leaves it out.
import { computed, unref } from 'vue'
import { useNav, useSlideContext } from '@slidev/client'
import PoyaCover from '../components/art/PoyaCover.vue'

const { $frontmatter, $renderContext } = useSlideContext()
const { isPrintMode } = useNav()
const fm = computed(() => (unref($frontmatter) ?? {}) as Record<string, unknown>)
const art = computed(() => fm.value.art !== false)
const walk = computed(() => {
  const ctx = unref($renderContext)
  return (ctx === 'slide' || ctx === 'presenter') && !unref(isPrintMode)
})
</script>

<template>
  <div class="slidev-layout cover">
    <div class="cover-body">
      <slot />
    </div>
    <PoyaCover v-if="art" class="cover-art" :walk="walk" ink="var(--ink)" paper="var(--paper)" />
  </div>
</template>

<style>
.slidev-layout.cover {
  position: relative;
  height: 100%;
  background: var(--paper);
  padding: 0 var(--margin);
  overflow: hidden;
}
.slidev-layout.cover .cover-body {
  position: absolute;
  left: var(--margin);
  right: var(--margin);
  top: 104px;
}
.slidev-layout.cover .cover-body > * {
  animation: rise 0.7s var(--ease-out) both;
}
.slidev-layout.cover .cover-body > :nth-child(2) {
  animation-delay: 0.12s;
}
.slidev-layout.cover .cover-body > :nth-child(3) {
  animation-delay: 0.3s;
}
.slidev-layout.cover .cover-body > :nth-child(n + 4) {
  animation-delay: 0.5s;
}
.slidev-layout.cover h1 {
  margin-top: 14px;
  font-size: var(--fs-cover);
  line-height: 1.02;
  letter-spacing: -0.02em;
}
.slidev-layout.cover h1 + p {
  margin-top: 18px;
  font-size: 26px;
  max-width: none;
}
.slidev-layout.cover .cover-team {
  margin-top: 30px;
  color: var(--ink);
}
/* One ink, as in a real paper-cut: the art's accents print in ink too, so the red of the
   title stays the one colour on the page. */
.slidev-layout.cover .cover-art {
  position: absolute;
  left: 0;
  bottom: 0;
  width: 1280px;
  --pa-red: var(--ink) !important;
  --pa-brass: var(--ink) !important;
}
@media (prefers-reduced-motion: reduce) {
  .slidev-layout.cover .cover-body > * {
    animation-name: fade-in;
    animation-duration: 0.2s;
    animation-delay: 0s;
  }
}
</style>
