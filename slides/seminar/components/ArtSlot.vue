<script setup lang="ts">
// Renders one illustration from ./art by name. Until that file exists, it keeps an
// empty, clearly marked frame of the same size, so the layout around it stays fixed.
import { computed, useAttrs } from 'vue'

defineOptions({ inheritAttrs: false })

const props = defineProps<{ name: string; w: number; h: number }>()

const pieces = import.meta.glob('./art/*.vue', { eager: true }) as Record<string, { default: unknown }>
const attrs = useAttrs()
const passed = computed(() => {
  const { class: _c, style: _s, ...rest } = attrs
  return rest
})
const piece = computed(() => pieces[`./art/${props.name}.vue`]?.default)
</script>

<template>
  <div class="art-slot" :class="$attrs.class" :style="[{ width: w + 'px', height: h + 'px' }, $attrs.style]">
    <component :is="piece" v-if="piece" v-bind="passed" />
    <div v-else class="empty mono">{{ name }}, {{ w }} x {{ h }}</div>
  </div>
</template>

<style scoped>
.art-slot > :deep(svg),
.art-slot > :deep(div) {
  display: block;
  width: 100%;
  height: 100%;
}
.empty {
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px dashed var(--hairline);
  font-size: var(--fs-caption);
  color: var(--graphite);
}
</style>
