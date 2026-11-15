---
eyebrow: Appendix for readers
---

# What is fixed today, and what a rule sets later

<div class="appx thr-appx">

<p class="thr-lede">Every rule is fixed at this talk. Numbers that depend on data are recorded later, by the rule.</p>

<div class="thr-table">
  <div class="th">Goal</div><div class="th">Fixed today</div><div class="th">Recorded later, by a fixed rule</div>
  <div class="g">O1</div><div><span class="n">95 %</span> of the fine-tuned teacher's recall, on T1 and on <span class="n">T2-final</span>. Never below <span class="n">GLiNER2-PII</span>. Swiss IDs <span class="n">99 %</span></div><div class="none">Nothing</div>
  <div class="g">O2</div><div><span class="n">90 %</span> of solved test prompts still solved, on 20 frozen prompts. 5 stress prompts reported apart</div><div>Character precision: <span class="n">GLiNER2-PII's</span> on <span class="n">T2-final</span></div>
  <div class="g">O3</div><div>8 times smaller, at most <span class="n">155.5 MB</span>. <span class="n">1.5 times</span> faster on the reference laptop. At least 4 curve points</div><div>The 30-text latency sample, from <span class="n">T2-dev</span></div>
  <div class="g">O4</div><div>0 leaks added by the app. <span class="n">100 %</span> exact restoration of intact placeholders. Every listed bad replacement flagged. No silent failure</div><div class="none">Nothing</div>
  <div class="g">O5</div><div>0 models reach the app without passing the gate. Shown by 7 December 2026: a model 3 recall points worse is refused</div><div>Demonstration thresholds, alert window and alert threshold, in params.yaml</div>
  <div class="g">Data</div><div><span class="n">OpenPII-1M</span> and Gretel, a seeded subset of 50,000 rows. T1 is the <span class="n">OpenPII-1M</span> validation split</div><div class="none">Nothing</div>
</div>

<p class="thr-note">Estimated training cost: about 5.4 hours of T4 GPU, <span class="n">about USD 3.40</span>. All of <span class="n">OpenPII-1M</span> and Gretel would cost <span class="n">about USD 80</span>, more than our <span class="n">USD 50</span> of credits. <span class="src">docs/smart-goals.md</span></p>

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
  grid-template-columns: 64px 1fr 1fr;
  column-gap: 24px;
  margin-top: 16px;
}
.thr-table > div {
  padding: 6px 0;
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
