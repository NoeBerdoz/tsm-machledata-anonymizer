<script setup lang="ts">
// One quiet header line: the section name and the slide number.
import { computed, unref } from 'vue'
import { useSlideContext } from '@slidev/client'

const { $frontmatter, $page } = useSlideContext()

const fm = computed(() => (unref($frontmatter) ?? {}) as Record<string, unknown>)
const show = computed(() => String(fm.value.layout ?? 'doc') !== 'cover' && fm.value.chrome !== false)
const section = computed(() => String(fm.value.section ?? ''))
const num = computed(() => String(unref($page)).padStart(2, '0'))
</script>

<template>
  <div v-if="show" class="chrome">
    <span>{{ section }}</span>
    <span class="mono">{{ num }}</span>
  </div>
</template>

<style scoped>
.chrome {
  position: absolute;
  left: var(--margin);
  right: var(--margin);
  top: 28px;
  z-index: 10;
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--hairline);
  font-family: var(--sans);
  font-size: var(--fs-caption);
  line-height: 1.2;
  color: var(--graphite);
  pointer-events: none;
}
</style>
