<script setup lang="ts">
// The default slide. The masthead and the footer rail come from slide-top.vue; this layout
// places the claim headline, the lede and the body between them.
</script>

<template>
  <div class="slidev-layout doc">
    <slot />
  </div>
</template>

<style scoped>
.doc {
  position: relative;
  height: 100%;
  background: var(--paper);
  padding: 92px var(--margin) 64px;
}
</style>
