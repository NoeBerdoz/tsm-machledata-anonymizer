<script setup lang="ts">
// The five goals, one line each.
import { goals } from '../data/goals'
</script>

<template>
  <div class="goals">
    <div v-for="g in goals" :key="g.id" class="row grid12">
      <span class="id">{{ g.id }}</span>
      <span class="name">{{ g.name }}</span>
      <span class="key">{{ g.key }}</span>
      <span class="when mono">{{ g.when }}</span>
    </div>
  </div>
</template>

<style scoped>
.goals {
  width: 1136px;
  margin-top: 48px;
  border-top: 1px solid var(--ink);
}
.row {
  height: 80px;
  align-items: center;
  border-bottom: 1px solid var(--hairline);
}
.id {
  grid-column: 1 / span 1;
  font-size: var(--fs-label);
  color: var(--graphite);
}
.name {
  grid-column: 2 / span 3;
}
.key {
  grid-column: 5 / span 6;
}
.when {
  grid-column: 11 / span 2;
  font-size: var(--fs-label);
  color: var(--graphite);
  text-align: right;
}
</style>
