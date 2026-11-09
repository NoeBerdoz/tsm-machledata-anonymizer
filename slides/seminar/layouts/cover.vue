<template>
  <div class="slidev-layout cover-page">
    <slot />
  </div>
</template>

<style scoped>
.cover-page {
  position: relative;
  height: 100%;
  background: var(--paper);
  padding: 32px var(--margin) 0;
  overflow: hidden;
}
</style>
