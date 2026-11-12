<script setup lang="ts">
// Slide 4: the model we plan to use as the teacher, introduced before any size or parameter.
//   0  its model card: name, origin, job, licence, types and languages
//   1  why this one: recall of four existing detectors on 1,000 public texts, before any
//      training; GLiNER2-PII finds the most
//   2  what we add: fine-tuning on Swiss identifiers and on our training set, by 30 November
//   3  its job: the fine-tuned model teaches a small model, the student, that runs on the laptop
// Sources: the model card of fastino/gliner2-privacy-filter-PII-multi on Hugging Face (base
// GLiNER2, Apache 2.0, 42 types, 7 languages: EN, FR, ES, DE, IT, PT, NL); docs/baselines.md
// (recall on OpenPII-1M, size 1,244 MB); docs/smart-goals.md and docs/swiss-identifiers.md
// (what we fine-tune on); docs/project-management.md (fine-tuned teacher due 2026-11-30).
// Every bar starts at zero. The slide's one red is the headline's emphasis.
import { useBeats, inOutCubic, type Channels, type Seg } from './lib/beats'
import { detectors } from '../data/baseline'

// recall on the T1 candidate sample, rounded to whole numbers to be said aloud
const ORDER = ['gliner2', 'privacy-filter', 'presidio', 'regex']
const rows = ORDER.map((k) => detectors.find((d) => d.key === k)!).map((d) => ({
  key: d.key,
  name: d.name,
  recall: d.openpii.recall,
  shown: Math.round(d.openpii.recall) + ' %',
}))
const gliner = detectors.find((d) => d.key === 'gliner2')!
const sizeMB = gliner.sizeMB!.toLocaleString('en-US') + ' MB'

function target(n: number): Channels {
  return {
    tests: n >= 1 ? 1 : 0,
    grow: n >= 1 ? 1 : 0,
    fine: n >= 2 ? 1 : 0,
    role: n >= 3 ? 1 : 0,
    arrow: n >= 3 ? 1 : 0,
    stud: n >= 3 ? 1 : 0,
  }
}
const beats: Record<number, Seg[]> = {
  1: [
    { k: 'tests', to: 1, at: 0, dur: 300 },
    { k: 'grow', to: 1, at: 120, dur: 1000, ease: inOutCubic },
  ],
  2: [{ k: 'fine', to: 1, at: 0, dur: 380 }],
  3: [
    { k: 'role', to: 1, at: 0, dur: 320 },
    { k: 'arrow', to: 1, at: 260, dur: 520, ease: inOutCubic },
    { k: 'stud', to: 1, at: 700, dur: 380 },
  ],
}
const { ch, fade } = useBeats({ target, beats })

const TRACK = 300
const vis = (v: number) => ({ opacity: v, visibility: v > 0.001 ? ('visible' as const) : ('hidden' as const) })
const rise = (v: number) => ({ ...vis(v), transform: `translateY(${(1 - v) * 10}px)` })
// the bars grow one after the other, the first one leading
const growAt = (i: number) => Math.max(0, Math.min(1, ch.grow * 1.45 - i * 0.15))
</script>

<template>
  <div class="intro" :style="{ opacity: fade }">
    <!-- 0 the model card -->
    <div class="card">
      <div class="name">GLiNER2-PII</div>
      <div class="mono id">fastino/gliner2-privacy-filter-PII-multi</div>
      <p class="job">It finds personal data and gives each piece a type.</p>
      <div class="spec">
        <span class="k">By</span><span class="v">Fastino</span>
        <span class="k">Licence</span><span class="v">Apache 2.0, open</span>
        <span class="k">Types</span><span class="v"><span class="figure-num">42</span>, such as <span class="mono t">person</span>, <span class="mono t">iban</span></span>
        <span class="k">Languages</span><span class="v"><span class="figure-num">7</span>, with French, German, Italian, English</span>
      </div>
    </div>

    <div class="side">
      <!-- 1 why this one -->
      <section class="part" :style="rise(ch.tests)">
        <div class="ck">Why this one: our tests</div>
        <p class="what">Personal data found (recall) in <span class="figure-num">1,000</span> public texts, before our training</p>
        <div v-for="(r, i) in rows" :key="r.key" class="row" :class="{ lead: r.key === 'gliner2' }">
          <span class="rname">{{ r.name }}</span>
          <span class="track" :style="{ width: TRACK + 'px' }">
            <span class="fill" :style="{ width: (r.recall / 100) * TRACK * growAt(i) + 'px' }" />
          </span>
          <span class="num" :style="vis(growAt(i) > 0.6 ? 1 : 0)">{{ r.shown }}</span>
        </div>
      </section>

      <!-- 2 what we add -->
      <section class="part" :style="rise(ch.fine)">
        <div class="ck">What we add: fine-tuning, by 30 November</div>
        <p class="add"><span class="mono plus">+</span> Swiss IDs: AVS numbers, IBANs, phone numbers</p>
        <p class="add"><span class="mono plus">+</span> our training set</p>
      </section>

      <!-- 3 its job -->
      <section class="part" :style="rise(ch.role)">
        <div class="ck">Its job: teach a small model</div>
        <div class="pair">
          <div class="box teacher">
            <div class="top"><span class="eyebrow ink">Teacher</span><span class="figure-num big">{{ sizeMB }}</span></div>
            <p>GLiNER2-PII, fine-tuned</p>
          </div>
          <div class="link">
            <span class="teaches" :style="vis(ch.arrow)">teaches</span>
            <svg width="96" height="16" viewBox="0 0 96 16" aria-hidden="true">
              <path d="M2 8 H88" pathLength="1" class="shaft" :style="{ strokeDashoffset: 1 - ch.arrow }" />
              <path d="M82 3 L90 8 L82 13" class="head" :style="vis(ch.arrow > 0.9 ? 1 : 0)" />
            </svg>
          </div>
          <div class="box student" :style="{ ...vis(ch.stud), transform: `translateX(${(1 - ch.stud) * 14}px)` }">
            <div class="top"><span class="eyebrow ink">Student</span><span class="small">small</span></div>
            <p>Runs on the laptop</p>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.intro {
  position: relative;
  width: 1136px;
  margin-top: 24px;
  display: grid;
  grid-template-columns: 436px 1fr;
  column-gap: 56px;
  /* the model card runs as tall as the right column, so both end on one line */
  align-items: stretch;
}
.ink {
  color: var(--ink);
}
.mono {
  font-family: var(--mono);
}
.ck {
  display: flex;
  justify-content: space-between;
  font-family: var(--mono);
  font-size: 14px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--ink);
}
.ck-r {
  color: var(--muted-2);
}

/* the model card */
.card {
  padding: 20px 26px 24px;
  background: var(--card);
  border: 1px solid var(--hair);
  border-radius: 10px;
  box-shadow:
    0 1px 0 rgba(22, 22, 22, 0.04),
    0 18px 36px -22px rgba(22, 22, 22, 0.38);
}
.name {
  margin-top: 0;
  font-size: 36px;
  font-weight: 500;
  line-height: 1.1;
  letter-spacing: -0.014em;
}
.id {
  margin-top: 6px;
  font-size: 15px;
  color: var(--muted-2);
}
.job {
  margin-top: 18px;
  padding-bottom: 18px;
  border-bottom: 1px solid var(--hair);
  font-size: 22px;
  line-height: 1.32;
}
.spec {
  display: grid;
  grid-template-columns: 102px 1fr;
  row-gap: 10px;
  margin-top: 16px;
  align-items: baseline;
}
.k {
  font-family: var(--mono);
  font-size: 13px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--muted-2);
}
.v {
  font-size: 20px;
  line-height: 1.3;
}
.v .figure-num {
  font-size: 22px;
}
.t {
  font-size: 18px;
  padding: 0 4px 1px;
  border: 1px solid var(--hair);
  border-radius: 4px;
  white-space: nowrap;
}

/* the three answers on the right */
.side {
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.part {
  padding-top: 10px;
  border-top: 1px solid var(--ink);
}
.what {
  margin: 8px 0 8px;
  font-size: 18px;
  line-height: 1.3;
  color: var(--muted);
}
.row {
  display: grid;
  grid-template-columns: 212px 300px 1fr;
  column-gap: 14px;
  align-items: center;
  height: 31px;
}
.rname {
  font-size: 19px;
  color: var(--muted);
  white-space: nowrap;
}
.lead .rname {
  color: var(--ink);
}
.track {
  position: relative;
  display: block;
  height: 12px;
  background: var(--wash);
  border-radius: 2px;
}
.fill {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  border-radius: 2px;
  background: var(--ink);
  opacity: 0.32;
}
.lead .fill {
  opacity: 1;
}
/* a table value, set as on every bar row of the deck: 20 px, tabular digits */
.num {
  font-size: 20px;
  font-variant-numeric: lining-nums tabular-nums;
  color: var(--muted);
  white-space: nowrap;
}
.lead .num {
  color: var(--ink);
}
.add {
  margin-top: 8px;
  font-size: 20px;
  line-height: 1.3;
}
.plus {
  display: inline-block;
  width: 18px;
  color: var(--muted-2);
}

/* teacher and student */
.pair {
  display: flex;
  align-items: center;
  margin-top: 12px;
}
.box {
  flex: none;
  width: 262px;
  padding: 9px 16px 11px;
  border-radius: 8px;
}
.box p {
  margin-top: 4px;
  font-size: 20px;
  line-height: 1.25;
  white-space: nowrap;
}
.top {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}
.small {
  font-size: 20px;
  color: var(--ink);
}
.teacher {
  border: 2px solid var(--ink);
  background: var(--card);
}
/* the student does not exist yet: a dashed frame */
.student {
  border: 1.5px dashed var(--ink);
}
.big {
  font-size: 22px;
}
.link {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}
.teaches {
  font-size: 18px;
  color: var(--ink);
}
.shaft {
  fill: none;
  stroke: var(--ink);
  stroke-width: 2;
  stroke-dasharray: 1;
}
.head {
  fill: none;
  stroke: var(--ink);
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}
</style>
