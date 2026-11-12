<script setup lang="ts">
// The window of an app, drawn crisp in the deck's type: a title bar with three dots, a title
// and an optional tag, and the body in the default slot.
//   tone="dark"  a remote service, such as a cloud AI
//   icon="cloud" a cloud mark in place of the three dots, for a service that is not an app
//   <template #bar>  extra items at the right end of the title bar
// The bar height and the title size can be set with --win-bar and --win-title.
withDefaults(defineProps<{ title?: string; tag?: string; tone?: 'light' | 'dark'; icon?: 'dots' | 'cloud' }>(), {
  title: '',
  tag: '',
  tone: 'light',
  icon: 'dots',
})
</script>

<template>
  <div class="win" :class="tone">
    <div class="bar">
      <svg v-if="icon === 'cloud'" class="cloud" width="24" height="24" viewBox="0 0 24 24" aria-hidden="true">
        <path d="M6.9 18.5A3.9 3.9 0 0 1 6.61 10.71A5.2 5.2 0 0 1 16.98 10A4.25 4.25 0 1 1 17.1 18.5Z" />
      </svg>
      <span v-else class="dots" aria-hidden="true"><i /><i /><i /></span>
      <span class="title">{{ title }}</span>
      <span v-if="tag" class="tag">{{ tag }}</span>
      <span class="grow" />
      <slot name="bar" />
    </div>
    <div class="body">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.win {
  position: relative;
  display: flex;
  flex-direction: column;
  border-radius: 10px;
  overflow: hidden;
  background: var(--card);
  border: 1px solid var(--hair);
  box-shadow:
    0 1px 0 rgba(22, 22, 22, 0.04),
    0 18px 36px -22px rgba(22, 22, 22, 0.38);
}
.bar {
  flex: none;
  height: var(--win-bar, 36px);
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 14px;
  border-bottom: 1px solid var(--hair);
  background: #faf9f6;
}
.dots {
  display: flex;
  gap: 6px;
}
.dots i {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: rgba(22, 22, 22, 0.14);
}
/* the cloud mark: a stroke icon at the weight of the deck's other marks */
.cloud {
  flex: none;
  margin: 0 -2px 0 -4px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linejoin: round;
  color: var(--muted);
}
.dark .cloud {
  color: #d2d1cc;
}
.title {
  font-family: var(--sans);
  font-size: var(--win-title, 14px);
  font-weight: 500;
  color: var(--muted);
  white-space: nowrap;
}
.tag {
  font-family: var(--mono);
  font-size: 11px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--ink);
  border: 1px solid rgba(22, 22, 22, 0.35);
  border-radius: 4px;
  padding: 1px 6px;
}
.grow {
  flex: 1;
}
.body {
  position: relative;
  flex: 1;
  min-height: 0;
}

.dark {
  background: var(--charcoal);
  border-color: #111111;
  color: var(--on-dark);
}
.dark .bar {
  background: var(--charcoal-bar);
  border-bottom-color: rgba(255, 255, 255, 0.08);
}
.dark .dots i {
  background: rgba(255, 255, 255, 0.18);
}
.dark .title {
  color: #d2d1cc;
}
</style>
