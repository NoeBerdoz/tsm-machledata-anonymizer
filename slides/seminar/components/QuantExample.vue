<script setup lang="ts">
// Slide 7. One rounding on one weight, then the same rounding on every weight of a layer.
//   step 1: 0.4237 / 0.01 = 42.37, rounded to 42, stored as int8 in 1 byte
//   step 2: read back 42 x 0.01 = 0.42, error 0.0037, never more than half a step (0.005)
//   step 3: the weight is one cell of a 2 x 2 matrix: before (float32) and after (int8)
//   step 4: the teacher's weights, 1.23 GB measured, about 0.31 GB estimated in int8
// Top half: the number line and the calculation. Bottom half: the two matrices and the bars.
// Every element is a function of the step, and CSS transitions carry the motion.
// Delays only apply on a single step forward, so going back or jumping lands at once.
import { useSlideContext } from '@slidev/client'
import { computed, ref, watch } from 'vue'

const props = withDefaults(defineProps<{ step?: number }>(), { step: 0 })
const s = computed(() => props.step)

const { $nav } = useSlideContext()
const print = computed(() => !!$nav.value?.isPrintMode)
const reduced = typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

const fwd = ref(false)
watch(s, (v, old) => {
  fwd.value = old !== undefined && v === old + 1
})

// Number line from 0.40 to 0.45: 120 px per step of 0.01.
const X0 = 24
const PER = 120
const x = (v: number) => X0 + ((v - 0.4) / 0.01) * PER
const ticks = [0.4, 0.41, 0.42, 0.43, 0.44, 0.45]
const LY = 140 // the line
const XW = x(0.4237) // the original weight
const XR = x(0.42) // the value read back

const before = ['0.4237', '-0.1862', '0.0714', '0.2981']
const after = ['42', '-19', '7', '30']
</script>

<template>
  <div class="qx" :class="{ s1: s >= 1, s2: s >= 2, s3: s >= 3, s4: s >= 4, fwd: fwd && !print && !reduced, print, rm: reduced }">
    <!-- top left: the number line -->
    <p class="layer">Example layer: step 0.01</p>
    <svg class="line" viewBox="0 0 652 250" width="652" height="250">
      <path :d="`M ${X0 - 14} ${LY} H ${x(0.45) + 14}`" class="axis" />
      <g v-for="t in ticks" :key="t">
        <path :d="`M ${x(t)} ${LY - 9} V ${LY + 9}`" class="tick" />
        <text :x="x(t)" :y="LY + 38" class="tl">{{ t.toFixed(2) }}</text>
      </g>
      <!-- the error, between the read-back value and the original -->
      <path :d="`M ${XR} ${LY} H ${XW}`" class="err" />
      <path :d="`M ${XW} ${LY - 11} V ${LY - 32}`" class="pole" />
      <path :d="`M ${XR} ${LY - 11} V ${LY - 32}`" class="pole rb" />
      <circle :cx="XW" :cy="LY" r="9" class="hollow" />
      <circle :cx="XW" :cy="LY" r="8" class="filled" :style="{ '--dx': XR - XW + 'px' }" />
      <!-- the link from the weight to its calculation -->
      <path d="M 412 94 C 520 94 590 116 660 116" pathLength="1" class="link" />
      <path d="M 652 110 L 660 116 L 652 122" class="link-head" />
    </svg>
    <p class="flag orig num" :style="{ left: XW - 1 + 'px' }">0.4237</p>
    <p class="flag rb num" :style="{ right: 1136 - XR - 1 + 'px' }">0.42</p>
    <div class="errs" :style="{ left: XR + 'px' }">
      <p class="err-t">Error: 0.0037</p>
      <p class="muted">At most half a step: 0.005</p>
    </div>

    <!-- top right: the calculation, in reading order -->
    <div class="calc">
      <p class="row r1"><span class="k">Original weight:</span><span class="num v">0.4237</span></p>
      <p class="row r2">
        <span class="strip"><i /><i /><i /><i /><em>0.4237</em></span>
        <span class="k two"><span>float32: 4 bytes</span><span class="gloss">(32-bit floating-point number)</span></span>
      </p>
      <p class="row r3"><Tex e="0.4237 \div 0.01 = 42.37" /><span class="k">rounded to 42</span></p>
      <p class="row r4">
        <span class="strip"><i /><em>42</em></span>
        <span class="k ink two"><span>Store 42 as int8: 1 byte</span><span class="gloss">(8-bit whole number)</span></span>
      </p>
      <p class="row r5"><Tex e="42 \times 0.01 = 0.42" /><span class="k ink">Read back: 0.42</span></p>
    </div>

    <!-- bottom left: every weight of the layer, before and after -->
    <p class="mhead">The same rounding for every weight of the layer</p>
    <div class="mat before">
      <span class="brk l" />
      <span class="brk r" />
      <div v-for="(v, i) in before" :key="v" class="cell" :class="`cell-b${i}`">
        <span class="strip"><i /><i /><i /><i /><em>{{ v }}</em></span>
      </div>
    </div>
    <svg class="round" viewBox="0 0 120 104" width="120" height="104">
      <path d="M 10 74 H 110" pathLength="1" class="link" />
      <path d="M 102 67 L 110 74 L 102 81" class="link-head" />
    </svg>
    <p class="round-l">divide by 0.01, then round</p>
    <div class="mat after">
      <span class="brk l" />
      <span class="brk r" />
      <div v-for="(v, i) in after" :key="v" class="cell" :class="`cell-a${i}`">
        <span class="strip"><i /><em>{{ v }}</em></span>
      </div>
    </div>
    <p class="mcap muted">Stored integers: int8</p>

    <!-- bottom right: the size of the weights -->
    <div class="size">
      <p class="sz-h">The teacher's weights:<br />4 times smaller</p>
      <div class="bar-row"><span class="bar full" /><span class="bl"><b>1.23 GB</b><br /><span class="muted">measured</span></span></div>
      <div class="bar-row"><span class="bar est" /><span class="bl">about <b>0.31 GB</b><br /><span class="muted">estimated</span></span></div>
      <p class="sz-c muted">The steps add a little.</p>
    </div>
  </div>
</template>

<style scoped>
.qx {
  position: relative;
  width: 1136px;
  height: 500px;
  --fs-mid: 22px;
  font-size: var(--fs-label);
}
.qx > * {
  position: absolute;
}
.num {
  font-family: var(--mono);
}
.muted {
  color: var(--graphite);
}
/* the error is ink: on this slide the red is the headline's emphasis */
.err-t {
  color: var(--ink);
  font-weight: 500;
}

/* ---------- top left: number line ---------- */
.layer {
  left: 0;
  top: 0;
  color: var(--graphite);
}
.line {
  left: 0;
  top: 0;
  overflow: visible;
}
.axis,
.tick {
  stroke: var(--ink);
  stroke-width: 1.5;
  fill: none;
}
.tl {
  font-family: var(--mono);
  font-size: 18px;
  fill: var(--graphite);
  text-anchor: middle;
}
.pole {
  stroke: var(--graphite);
  stroke-width: 1.5;
}
.hollow {
  fill: var(--paper);
  stroke: var(--ink);
  stroke-width: 2;
}
.flag {
  top: 76px;
  font-size: 24px;
  line-height: 1.2;
  white-space: nowrap;
  color: var(--ink);
}
.errs {
  top: 198px;
  white-space: nowrap;
  font-size: 20px;
  line-height: 1.3;
}

/* the read-back point travels from the original to 0.42 */
.filled {
  fill: var(--ink);
  opacity: 0;
  transform: translateX(0);
  transition:
    opacity 120ms linear,
    transform 300ms var(--ease);
}
.s2 .filled {
  opacity: 1;
  transform: translateX(var(--dx));
}
.err {
  stroke: var(--ink);
  stroke-width: 5;
  transform-box: fill-box;
  transform-origin: right center;
  transform: scaleX(0);
  transition: transform 300ms var(--ease);
}
.s2 .err {
  transform: scaleX(1);
}
.pole.rb,
.flag.rb,
.errs {
  opacity: 0;
  transition: opacity 200ms var(--ease);
}
.s2 .pole.rb,
.s2 .flag.rb,
.s2 .errs {
  opacity: 1;
}
.fwd.s2 .filled {
  transition-duration: 120ms, 450ms;
}
.fwd.s2 .err {
  transition-duration: 450ms;
}
.fwd.s2 .pole.rb,
.fwd.s2 .flag.rb,
.fwd.s2 .errs {
  transition-delay: 200ms;
  transition-duration: 250ms;
}

/* links and arrows draw from their start */
.link {
  stroke: var(--graphite);
  stroke-width: 1.5;
  fill: none;
  stroke-dasharray: 1 1;
  stroke-dashoffset: 1;
  transition: stroke-dashoffset 200ms var(--ease);
}
.link-head {
  stroke: var(--graphite);
  stroke-width: 1.5;
  fill: none;
  stroke-linecap: round;
  stroke-linejoin: round;
  opacity: 0;
  transition: opacity 150ms linear;
}
.s1 .line .link,
.s3 .round .link {
  stroke-dashoffset: 0;
}
.s1 .line .link-head,
.s3 .round .link-head {
  opacity: 1;
}
.fwd.s1 .line .link {
  transition-duration: 250ms;
}
.fwd.s1 .line .link-head {
  transition-delay: 200ms;
}

/* ---------- top right: the calculation ---------- */
.calc {
  left: 676px;
  top: 0;
  width: 460px;
  height: 240px;
}
.row {
  position: absolute;
  left: 0;
  display: flex;
  align-items: center;
  gap: 14px;
  height: 32px;
  font-size: var(--fs-mid);
  white-space: nowrap;
}
.row .k {
  color: var(--graphite);
}
.row .k.ink {
  color: var(--ink);
}
/* a type and its name in plain words, on two lines */
.row .two {
  display: flex;
  flex-direction: column;
  line-height: 1.15;
}
.row .two .gloss {
  font-size: var(--fs-label);
  color: var(--graphite);
}
.row .v {
  font-size: 24px;
}
.r1 {
  top: 0;
}
.r2 {
  top: 40px;
  height: 48px;
}
.r3 {
  top: 100px;
}
.r4 {
  top: 146px;
  height: 48px;
}
.r5 {
  top: 206px;
}
.r3,
.r4,
.r5 {
  opacity: 0;
  transform: translateY(6px);
  transition:
    opacity 200ms var(--ease),
    transform 250ms var(--ease);
}
.s1 .r3,
.s1 .r4,
.s2 .r5 {
  opacity: 1;
  transform: none;
}
.fwd.s1 .r3 {
  transition-delay: 150ms;
  transition-duration: 300ms;
}
.fwd.s1 .r4 {
  transition-delay: 400ms;
  transition-duration: 250ms;
}
.fwd.s2 .r5 {
  transition-duration: 300ms;
}

/* a memory strip: one outlined bar, one segment per byte, wider than tall.
   Short marks at the top and bottom edges split the bytes, the value sits inside. */
.strip {
  position: relative;
  display: inline-flex;
  flex: none;
  height: 34px;
  border: 1.5px solid var(--ink);
  border-radius: 2px;
}
.strip i {
  position: relative;
  display: block;
  width: 40px;
  height: 100%;
}
.strip i + i::before,
.strip i + i::after {
  content: '';
  position: absolute;
  left: -0.75px;
  width: 1.5px;
  height: 5px;
  background: var(--ink);
}
.strip i + i::before {
  top: 0;
}
.strip i + i::after {
  bottom: 0;
}
.strip em {
  position: absolute;
  inset: 0;
  font-style: normal;
  font-family: var(--mono);
  font-size: 20px;
  line-height: 31px;
  text-align: center;
  color: var(--ink);
}

/* ---------- bottom left: the two matrices ---------- */
.mhead {
  left: 0;
  top: 276px;
  font-size: 20px;
  font-weight: 500;
}
.mat {
  top: 316px;
  width: 368px;
  height: 110px;
}
.mat.before {
  left: 0;
}
.mat.after {
  left: 504px;
}
.brk {
  position: absolute;
  top: 0;
  width: 10px;
  height: 110px;
  box-sizing: border-box;
  border: 1.5px solid var(--ink);
}
.brk.l {
  left: 0;
  border-right: none;
}
.brk.r {
  right: 0;
  border-left: none;
}
/* every cell has the same size on both sides; only the strip inside shrinks */
.cell {
  position: absolute;
  width: 164px;
  height: 34px;
  display: flex;
  justify-content: center;
  transition:
    opacity 200ms linear,
    transform 250ms var(--ease);
}
.cell-b0,
.cell-a0 {
  left: 14px;
  top: 14px;
}
.cell-b1,
.cell-a1 {
  left: 190px;
  top: 14px;
}
.cell-b2,
.cell-a2 {
  left: 14px;
  top: 62px;
}
.cell-b3,
.cell-a3 {
  left: 190px;
  top: 62px;
}
.round {
  left: 376px;
  top: 316px;
  overflow: visible;
}
.round-l {
  left: 376px;
  top: 322px;
  width: 120px;
  text-align: center;
  line-height: 1.2;
  color: var(--graphite);
}
.mcap {
  left: 504px;
  top: 430px;
}

/* hidden until step 3 */
.mhead,
.mat .brk,
.mat .cell,
.round-l,
.mcap {
  opacity: 0;
  transition: opacity 200ms linear;
}
/* the original weight's strip starts on top of the float32 strip in the calculation */
.cell-b0 {
  transform: translate(662px, -283px);
}
.cell-b1,
.cell-b2,
.cell-b3 {
  transform: scale(0.94);
}
.mat.after .cell {
  transform: translateX(-14px);
}
.s3 .mhead,
.s3 .mat .brk,
.s3 .mat .cell,
.s3 .round-l,
.s3 .mcap {
  opacity: 1;
}
.s3 .mat .cell {
  transform: none;
}
/* 0 to 600 ms: the weight's strip drops into its cell and the before matrix appears.
   600 to 1060 ms: the arrow draws and the after matrix fills in. */
.fwd.s3 .cell-b0 {
  transition-duration: 60ms, 600ms;
}
.fwd.s3 .cell-b1,
.fwd.s3 .cell-b2,
.fwd.s3 .cell-b3,
.fwd.s3 .before .brk,
.fwd.s3 .mhead {
  transition-delay: 150ms;
  transition-duration: 300ms;
}
.fwd.s3 .round .link {
  transition-delay: 600ms;
  transition-duration: 200ms;
}
.fwd.s3 .round .link-head {
  transition-delay: 770ms;
}
.fwd.s3 .round-l,
.fwd.s3 .after .brk {
  transition-delay: 620ms;
  transition-duration: 200ms;
}
.fwd.s3 .cell-a0 {
  transition-delay: 680ms;
  transition-duration: 180ms;
}
.fwd.s3 .cell-a1 {
  transition-delay: 760ms;
  transition-duration: 180ms;
}
.fwd.s3 .cell-a2 {
  transition-delay: 820ms;
  transition-duration: 180ms;
}
.fwd.s3 .cell-a3 {
  transition-delay: 880ms;
  transition-duration: 180ms;
}
.fwd.s3 .mcap {
  transition-delay: 860ms;
}

/* ---------- bottom right: the storage bars ---------- */
.size {
  left: 896px;
  top: 276px;
  width: 240px;
  opacity: 0;
  transition: opacity 200ms linear;
}
.s4 .size {
  opacity: 1;
}
.sz-h {
  line-height: 1.3;
  font-size: 20px;
  font-weight: 500;
  margin-bottom: 14px;
}
.bar-row {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 12px;
  white-space: nowrap;
}
/* the size on top, measured or estimated under it */
.bl {
  font-size: var(--fs-label);
  line-height: 1.25;
}
.bar-row b {
  font-weight: 500;
}
.bar {
  display: block;
  flex: none;
  width: 88px;
  height: 30px;
  box-sizing: border-box;
  border: 1.5px solid var(--ink);
}
.bar.est {
  border-style: dashed;
  transition: width 350ms var(--ease);
}
.s4 .bar.est {
  width: 22px;
}
.sz-c {
  margin-top: 2px;
  font-size: var(--fs-label);
}
.fwd.s4 .size {
  transition-duration: 150ms;
}
.fwd.s4 .bar.est {
  transition-delay: 200ms;
  transition-duration: 400ms;
}

/* reduced motion: short fades, no travel, no zoom */
.rm .filled,
.rm .err,
.rm .cell,
.rm .bar.est,
.rm .r3,
.rm .r4,
.rm .r5 {
  transition-property: opacity !important;
  transition-duration: 150ms !important;
  transition-delay: 0ms !important;
}
.rm .cell,
.rm .r3,
.rm .r4,
.rm .r5 {
  transform: none !important;
}

/* print: every page shows the finished state of its click */
.print,
.print *,
.print :deep(*) {
  transition: none !important;
}
</style>
