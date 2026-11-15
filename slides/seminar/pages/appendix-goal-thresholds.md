---
eyebrow: Appendix for readers
---

# What is fixed today, and what a rule sets later

<div class="appx thr-appx">

<p class="thr-lede">Every rule is fixed at this talk. Numbers that depend on data are recorded later, by the rule.</p>

<div class="thr-table">
  <div class="th">Goal</div><div class="th">Fixed today</div><div class="th">Recorded later, by a fixed rule</div>
  <div class="g">O1</div><div>Models alone: <span class="n">95 %</span> of the fine-tuned teacher's recall, on T1 and on <span class="n">T2-final</span>. Never below <span class="n">GLiNER2-PII</span> (<span class="n">80.6 %</span> on T1). With the regex: Swiss IDs <span class="n">99 %</span>, pooled</div><div class="none">Nothing</div>
  <div class="g">O2</div><div><span class="n">90 %</span> of solved test prompts still solved, on 20 frozen prompts. Pinned model version. Solved when 2 of 3 runs pass. 5 stress prompts reported apart</div><div>Character precision: <span class="n">GLiNER2-PII's</span> on <span class="n">T2-final</span></div>
  <div class="g">O3</div><div>8 times smaller in exact bytes, at most <span class="n">about 155.6 MB</span>. <span class="n">1.5 times</span> faster on the reference laptop. At least 4 curve points</div><div>The 30-text latency sample, drawn from <span class="n">T2-dev</span> with a fixed seed</div>
  <div class="g">O4</div><div>0 leaks added by the app, in everything that leaves the device. <span class="n">100 %</span> exact restoration of intact placeholders. Every listed bad replacement flagged. No silent failure</div><div class="none">Nothing</div>
  <div class="g">O5</div><div>Across the whole project, 0 installed versions without a passing MLflow gate record for the same file hash. Five scenarios pass by 7 December 2026</div><div>Demonstration thresholds, alert window and alert threshold, in params.yaml</div>
  <div class="g">Data</div><div><span class="n">OpenPII-1M</span> and Gretel, a seeded subset of 50,000 rows. T1 is a fixed 1,000-text sample of the <span class="n">OpenPII-1M</span> validation split</div><div>T2's annotation policy, groups, mix and hashes, frozen by 30 November</div>
</div>

<p class="thr-note">Estimated training cost: about 5.4 hours of T4 GPU, <span class="n">about USD 3.40</span>. One run on all French, German, Italian and English rows would take about 50 hours of our one T4, <span class="n">about USD 30</span>. The subset leaves room for retries within our <span class="n">USD 50</span> of credits, and gives the three models the same budget. <span class="src">docs/smart-goals.md</span></p>

</div>

<style>
.thr-appx {
  font-size: 17px;
  line-height: 1.36;
}
.thr-appx p,
.thr-table > div {
  text-wrap: pretty;
}
.thr-lede {
  color: var(--muted);
}
.thr-table {
  display: grid;
  grid-template-columns: 64px 1.5fr 1fr;
  column-gap: 24px;
  margin-top: 16px;
}
.thr-table > div {
  padding: 4px 0;
  border-bottom: 1px solid var(--hair);
}
.thr-table > .th {
  font-family: var(--mono);
  font-size: var(--fs-eyebrow);
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--muted-2);
  padding-top: 0;
  border-bottom-color: var(--ink);
}
.thr-table > .g {
  font-weight: 500;
}
.thr-table > .none {
  color: var(--muted-2);
}
.thr-appx .n {
  white-space: nowrap;
}
.thr-note {
  margin-top: 14px;
}
.thr-note .src {
  font-family: var(--mono);
  font-size: 14px;
  color: var(--muted-2);
  white-space: nowrap;
}
</style>

<!--
Appendix for readers, not presented.

If asked: how can thresholds be frozen without T2? We freeze the rules today, at this talk. The final checks compare the models on T2-final. The numbers for the development gate are recorded on T2-dev before any tuning.
-->
