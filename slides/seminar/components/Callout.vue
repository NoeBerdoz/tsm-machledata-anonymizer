<script setup lang="ts">
// The one thing to remember, as a ruled note: a small mono tag, then one sentence.
//   tone="alert"  red, for a danger only
//   <Callout tag="In short">This time, the AI only saw placeholders.</Callout>
withDefaults(defineProps<{ tag?: string; tone?: 'note' | 'alert' }>(), { tag: '', tone: 'note' })
</script>

<template>
  <div class="callout" :class="tone">
    <div v-if="tag" class="tag">{{ tag }}</div>
    <div class="text"><slot /></div>
  </div>
</template>

<style scoped>
.callout {
  --c: var(--ink);
  border-left: 3px solid var(--c);
  padding: 3px 0 4px 18px;
}
.alert {
  --c: var(--red);
}
.tag {
  font-family: var(--mono);
  font-size: 12px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--c);
  margin-bottom: 6px;
}
.text {
  font-family: var(--sans);
  font-size: 26px;
  font-weight: 500;
  line-height: 1.28;
  letter-spacing: -0.008em;
  color: var(--ink);
}
.text :deep(em) {
  font-style: normal;
  color: var(--red);
}
</style>
