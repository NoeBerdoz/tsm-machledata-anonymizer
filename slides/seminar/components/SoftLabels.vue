<script setup lang="ts">
// Teacher probabilities for the first "Dupont", computed as softmax(z / tau).
// The logits are illustrative and fixed. step 0, 1, 2 sets tau = 1, 2, 4.
import { computed } from 'vue'

const props = withDefaults(defineProps<{ step?: number }>(), { step: 0 })

const classes = ['PERSON', 'LOCATION', 'ORG', 'NONE']
const logits = [4.0, 2.2, 0.6, 0.0]
const gold = [1, 0, 0, 0]
const temps = [1, 2, 4]

function softmax(z: number[], tau: number) {
  const e = z.map((v) => Math.exp(v / tau))
  const sum = e.reduce((a, b) => a + b, 0)
  return e.map((v) => v / sum)
}

const ti = computed(() => Math.min(Math.max(props.step, 0), 2))
const probs = computed(() => softmax(logits, temps[ti.value]))

const BAR = 200
</script>

<template>
  <div class="soft">
    <p class="line">
      Envoyer à Mme <span class="target">Dupont</span>, rue Dupont 4, Lausanne.
    </p>

    <div class="cols">
      <div class="col">
        <div class="head label">Gold label</div>
        <div v-for="(c, i) in classes" :key="c" class="row">
          <span class="mono cls">{{ c }}</span>
          <span class="track"><span class="fill" :style="{ width: gold[i] * BAR + 'px' }" /></span>
          <span class="mono val">{{ gold[i].toFixed(2) }}</span>
        </div>
      </div>

      <div class="col">
        <div class="head label">Teacher</div>
        <div v-for="(c, i) in classes" :key="c" class="row">
          <span class="mono cls">{{ c }}</span>
          <span class="track"><span class="fill" :style="{ width: probs[i] * BAR + 'px' }" /></span>
          <span class="mono val">{{ probs[i].toFixed(2) }}</span>
        </div>
        <div class="taus label">
          <Tex e="\tau =" />
          <span v-for="(t, i) in temps" :key="t" class="mono t" :class="{ act: i === ti }">{{ t }}</span>
          <span class="formula"><Tex e="p_i = \mathrm{softmax}(z_i/\tau)" /></span>
        </div>
      </div>
    </div>

    <p class="caption foot">Categorical teaching example, illustrative logits <span class="mono">z = (4.0, 2.2, 0.6, 0.0)</span></p>
  </div>
</template>

<style scoped>
.soft {
  width: calc(9 * var(--col) + 8 * var(--gutter));
}
.line {
  font-size: var(--fs-body);
}
.target {
  outline: 1.25px dashed var(--ink);
  outline-offset: 3px;
}
.cols {
  display: grid;
  grid-template-columns: calc(4 * var(--col) + 3 * var(--gutter)) 1fr;
  column-gap: var(--gutter);
  margin-top: 32px;
}
.head {
  padding-bottom: 8px;
  margin-bottom: 4px;
  border-bottom: 1px solid var(--hairline);
}
.row {
  display: grid;
  grid-template-columns: 96px 1fr 48px;
  align-items: center;
  height: 40px;
}
.col:first-child .row {
  grid-template-columns: 96px 1fr 48px;
}
.cls {
  font-size: var(--fs-caption);
  color: var(--graphite);
}
.track {
  position: relative;
  height: 16px;
}
.fill {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  max-width: 100%;
  background: var(--graphite);
  transition: width var(--t-slow) var(--ease);
}
.val {
  font-size: var(--fs-caption);
  text-align: right;
}
.taus {
  display: flex;
  align-items: baseline;
  gap: 16px;
  margin-top: 16px;
}
.t {
  color: var(--graphite);
  padding-bottom: 2px;
  border-bottom: 1px solid transparent;
  transition: color var(--t-fast) var(--ease), border-color var(--t-fast) var(--ease);
}
.t.act {
  color: var(--ink);
  border-bottom-color: var(--ink);
}
.formula {
  margin-left: auto;
  color: var(--graphite);
}
.foot {
  margin-top: 24px;
}
</style>
