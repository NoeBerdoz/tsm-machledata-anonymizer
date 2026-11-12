<script setup lang="ts">
// Slide 4: what the teacher is made of, to scale, and the three models of the talk.
// Read on 2026-11-10 from the safetensors header and config of
// fastino/gliner2-privacy-filter-PII-multi at commit 1cb4166 (base: microsoft/mdeberta-v3-base):
// 307.1M parameters in float32, 1,228 MB of weights (1.23 GB).
//   word embeddings  250,112 tokens x 768 = 192.1M (63 %)
//   encoder          85.5M
//   GLiNER2 heads    29.5M
// The French, German, Italian and English texts of OpenPII-1M's validation split use 77,347
// of the 250,112 tokens (docs/baselines.md). Pruned to them, the embeddings keep 59.4M
// parameters. It is a lower bound: a real pruning also keeps the tokens of the training texts.
//   0  the bar to scale, with the three models below it
//   1  the embeddings shrink to the tokens of our four languages
import { useBeats, inOutCubic, type Channels, type Seg } from './lib/beats'

const TOTAL = 307.1
const EMB = 192.1
const ENC = 85.5
const HEADS = 29.5
const PRUNED = 59.4
const W = 1136
const GAP = 3
const px = (m: number) => (W * m) / TOTAL
const EMB_W = px(EMB)
const ENC_W = px(ENC)
const HEADS_W = W - EMB_W - ENC_W

function target(n: number): Channels {
  return { cut: n >= 1 ? 1 : 0 }
}
const beats: Record<number, Seg[]> = {
  1: [{ k: 'cut', to: 1, at: 0, dur: 1000, ease: inOutCubic }],
}
const { ch, fade } = useBeats({ target, beats })

// the embedding fill, from 192.1M to 59.4M of the same scale
const embFill = () => EMB_W - GAP - (EMB_W - px(PRUNED)) * ch.cut
const swap = (v: number) => ({ opacity: v, visibility: v > 0.001 ? ('visible' as const) : ('hidden' as const) })
</script>

<template>
  <div class="teacher" :style="{ opacity: fade }">
    <div class="head">
      <span class="total">
        <span class="swap" :style="swap(1 - ch.cut)"><span class="figure-num">307.1M</span> parameters</span>
        <span class="swap" :style="swap(ch.cut)">about <span class="figure-num">174M</span> parameters</span>
      </span>
    </div>

    <!-- the bar, to scale -->
    <div class="names">
      <span :style="{ width: EMB_W + 'px' }">Word embeddings</span>
      <span :style="{ width: ENC_W + 'px' }">Encoder</span>
      <span class="end" :style="{ width: HEADS_W + 'px' }"><span>GLiNER2 heads</span></span>
    </div>
    <div class="bar">
      <div class="seg ghost" :style="{ left: 0, width: EMB_W - GAP + 'px', opacity: ch.cut }" />
      <div class="seg emb" :style="{ left: 0, width: embFill() + 'px' }" />
      <div class="seg enc" :style="{ left: EMB_W + 'px', width: ENC_W - GAP + 'px' }" />
      <div class="seg heads" :style="{ left: EMB_W + ENC_W + 'px', width: HEADS_W + 'px' }" />
    </div>
    <div class="nums">
      <span class="cell" :style="{ width: EMB_W + 'px' }">
        <span class="swap" :style="swap(1 - ch.cut)"><span class="figure-num">192.1M</span> parameters, <span class="figure-num">63 %</span></span>
        <span class="swap" :style="swap(ch.cut)"><span class="figure-num">59.4M</span> parameters or more</span>
      </span>
      <span class="cell" :style="{ width: ENC_W + 'px' }"><span class="figure-num">85.5M</span> parameters</span>
      <span class="cell end" :style="{ width: HEADS_W + 'px' }"><span><span class="figure-num">29.5M</span> parameters</span></span>
    </div>
    <div class="sub">
      <span class="swap" :style="swap(1 - ch.cut)"><span class="figure-num">250,112</span> tokens, <span class="figure-num">768</span> numbers each</span>
      <span class="swap" :style="swap(ch.cut)">Our French, German, Italian and English test texts use <span class="figure-num">77,347</span> of them</span>
    </div>

    <!-- the three models of the talk -->
    <div class="cast">
      <div class="who now">
        <div class="eyebrow ink">Teacher</div>
        <p>GLiNER2-PII, fine-tuned at v1</p>
      </div>
      <div class="who">
        <div class="eyebrow">Student</div>
        <p>Made from the teacher at v2 and v3</p>
      </div>
      <div class="who">
        <div class="eyebrow">Today's app engine</div>
        <p><span class="mono id">qwen3:4b</span> plus rules</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.teacher {
  position: relative;
  width: 1136px;
  margin-top: 36px;
}
.ink {
  color: var(--ink);
}
.head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--ink);
}
.total {
  position: relative;
  display: block;
  width: 600px;
  height: 34px;
  font-size: 20px;
  color: var(--muted);
}
.total .swap {
  left: 0;
  bottom: 0;
  top: auto;
}
.total .figure-num {
  font-size: 26px;
  color: var(--ink);
}

.names,
.nums {
  display: flex;
}
.names {
  margin-top: 26px;
  font-size: 20px;
  line-height: 1.2;
}
.names > span,
.nums > .cell {
  flex: none;
  padding-left: 2px;
  white-space: nowrap;
}
.bar {
  position: relative;
  height: 56px;
  margin-top: 10px;
}
.seg {
  position: absolute;
  top: 0;
  bottom: 0;
}
.emb {
  background: var(--ink);
}
.enc {
  background: rgba(22, 22, 22, 0.42);
}
.heads {
  background: rgba(22, 22, 22, 0.2);
}
/* what the cut removes: an empty frame of the old size */
.ghost {
  border: 1.5px dashed rgba(22, 22, 22, 0.45);
}
.nums {
  margin-top: 12px;
  font-size: 20px;
  color: var(--muted);
}
.nums .figure-num {
  font-size: 26px;
  color: var(--ink);
}
.cell {
  position: relative;
  height: 34px;
}
/* the last part is narrow: its label and number end at the right margin */
.end {
  display: flex;
  justify-content: flex-end;
  padding-left: 0;
}
.id {
  font-size: 19px;
}
.swap {
  position: absolute;
  left: 2px;
  top: 0;
  white-space: nowrap;
}
.sub {
  position: relative;
  height: 28px;
  margin-top: 6px;
  font-size: 20px;
  color: var(--muted);
}
.sub .swap {
  left: 2px;
}
.sub .figure-num {
  color: var(--ink);
}

.cast {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  column-gap: 24px;
  margin-top: 52px;
}
.who {
  padding-top: 12px;
  border-top: 1px solid var(--hair);
}
/* the model of this slide: the ink rule of the current step */
.who.now {
  border-top: 2px solid var(--ink);
  padding-top: 11px;
}
.who p {
  margin-top: 8px;
  font-size: 20px;
  line-height: 1.35;
}
</style>
