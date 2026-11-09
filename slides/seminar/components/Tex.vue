<script setup lang="ts">
import katex from 'katex'
import { computed } from 'vue'

const props = withDefaults(defineProps<{ e: string; display?: boolean }>(), { display: false })
const html = computed(() => katex.renderToString(props.e, { displayMode: props.display, throwOnError: false }))
</script>

<template>
  <span class="tex" v-html="html" />
</template>
