<script setup lang="ts">
// The running chrome of every slide, read from its frontmatter:
//   masthead  the part on the left ("02 / Model", from part: 2, plus an optional eyebrow:),
//             the talk on the right, and a hairline under both
//   footer    a source in small print (source:), the rail of the five parts, the slide number
// The cover and the closing set their own masthead. chrome: false hides everything.
import { computed, unref, watchEffect } from 'vue'
import { useNav, useSlideContext } from '@slidev/client'
import Rail from './components/Rail.vue'
import { PARTS } from './components/parts'

const { $frontmatter, $page } = useSlideContext()
const { isPrintMode } = useNav()

// While the deck is exported, every page shows its end state at once (see style.css)
watchEffect(() => {
  if (typeof document !== 'undefined') document.documentElement.classList.toggle('is-print', !!unref(isPrintMode))
})

const fm = computed(() => (unref($frontmatter) ?? {}) as Record<string, unknown>)
const layout = computed(() => String(fm.value.layout ?? 'doc'))
const show = computed(() => fm.value.chrome !== false)
const part = computed(() => {
  const n = Number(fm.value.part ?? 0)
  return n >= 1 && n <= PARTS.length ? n : 0
})
const pad = (n: number) => String(n).padStart(2, '0')

const left = computed(() => {
  if (fm.value.left) return String(fm.value.left)
  if (layout.value === 'cover') return 'TSM_MachLeData / MSE HES-SO'
  const extra = fm.value.eyebrow ? String(fm.value.eyebrow) : ''
  if (part.value) return [pad(part.value), PARTS[part.value - 1], extra].filter(Boolean).join(' / ')
  return extra || String(fm.value.section ?? '')
})
const right = computed(() => {
  if (fm.value.right) return String(fm.value.right)
  if (layout.value === 'cover') return 'Seminar talk / 16 November 2026'
  return 'On-device PII pseudonymizer'
})
const source = computed(() => (fm.value.source ? String(fm.value.source) : ''))
const num = computed(() => pad(Number(unref($page))))
</script>

<template>
  <div v-if="show" class="chrome">
    <div class="masthead">
      <span class="eyebrow">{{ left }}</span>
      <span class="eyebrow">{{ right }}</span>
    </div>
    <div class="footer">
      <span class="source">{{ source }}</span>
      <Rail v-if="layout === 'closing' || part" :current="part" :all="layout === 'closing'" />
      <span v-if="layout !== 'cover'" class="num">{{ num }}</span>
    </div>
  </div>
</template>

<style scoped>
.chrome {
  position: absolute;
  inset: 0;
  z-index: 10;
  pointer-events: none;
}
.masthead {
  position: absolute;
  left: var(--margin);
  right: var(--margin);
  top: 34px;
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--hair);
}
.footer {
  position: absolute;
  left: var(--margin);
  right: 30px;
  bottom: 24px;
  display: flex;
  align-items: center;
  gap: 18px;
}
.source {
  flex: 1;
  min-width: 0;
  font-family: var(--sans);
  font-size: 14px;
  line-height: 1.4;
  color: var(--muted-2);
}
.num {
  width: 24px;
  text-align: right;
  font-family: var(--mono);
  font-size: 12px;
  color: var(--muted-2);
}
</style>
