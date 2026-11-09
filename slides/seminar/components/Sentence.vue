<script setup lang="ts">
// The opening sentence. state follows the marks of Pii.vue:
// 0 plain, 1 detected, 2 cut out, 3 replaced.
withDefaults(defineProps<{ state?: number }>(), { state: 0 })
</script>

<template>
  <p class="sentence">
    <Pii :state="state" chip="<PERSON_1>">Marie Dupont</Pii>
    (AVS <Pii :state="state" chip="<AVS_1>">756.1234.5678.97</Pii>) moved to<br />
    <Pii :state="state" chip="<ADDRESS_1>">Rue de Bourg 12, 1003 Lausanne</Pii>.
  </p>
</template>

<style scoped>
.sentence {
  font-size: var(--fs-head);
  line-height: 1.5;
  font-weight: 400;
  letter-spacing: -0.008em;
}
</style>
