<script setup lang="ts">
// The closing slide: one large line and what follows it, set low on the page, with the
// whole rail lit and quiet in the footer (slide-top.vue).
</script>

<template>
  <div class="slidev-layout closing">
    <slot />
  </div>
</template>

<style>
.slidev-layout.closing {
  position: relative;
  height: 100%;
  background: var(--paper);
  padding: 92px var(--margin) 64px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.slidev-layout.closing h1 {
  font-size: var(--fs-cover);
  line-height: 1.04;
  letter-spacing: -0.018em;
}
</style>
