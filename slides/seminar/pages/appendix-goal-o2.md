---
eyebrow: Appendix for readers
---

# O2 asks that 90 % of solved tasks still work

<div class="appx cols goal-appx">
<div>

### O2 Utility

<p class="goal-s">By the final talk, at least <span class="figure-num">90 %</span> of the app tasks solved without pseudonymization stay solved with it. The student's character precision on <span class="n">T2-final</span> is at least <span class="n">GLiNER2-PII's</span> on <span class="n">T2-dev</span>.</p>

### How we measure it

20 scripted tasks run through our app twice, with and without pseudonymization, with the same OpenAI model and settings. Each task has an answer check fixed in advance.

### Reported, with no threshold

Both counts. If not all 20 tasks pass without pseudonymization, we divide by the real number.

</div>
<div>

### Why these numbers

<div class="why-row"><span class="k">90 %</span><p>O1 alone can be met by masking everything. O2 checks that the answers stay useful: at most 2 of 20 solved tasks may break. <span class="src">docs/smart-goals.md</span></p></div>
<div class="why-row"><span class="k">Precision</span><p>The precision floor limits how much is masked by mistake. The number is recorded on <span class="n">T2-dev</span> before any tuning. <span class="src">docs/smart-goals.md</span></p></div>

### The limit

No app result yet: the tasks run once the app and the backend are ready.

</div>
</div>

<style>
.goal-appx {
  font-size: 18px;
  line-height: 1.4;
}
.goal-appx .goal-s {
  font-size: 21px;
  line-height: 1.36;
}
.goal-appx p,
.goal-appx li {
  text-wrap: pretty;
}
.goal-appx .why-row {
  display: grid;
  grid-template-columns: 100px 1fr;
  column-gap: 12px;
  align-items: start;
}
.goal-appx .why-row + .why-row {
  margin-top: 10px;
}
.goal-appx .k {
  font-weight: 500;
  font-variant-numeric: lining-nums tabular-nums;
}
.goal-appx .n {
  white-space: nowrap;
}
.goal-appx .src {
  font-family: var(--mono);
  font-size: 14px;
  color: var(--muted-2);
  white-space: nowrap;
}
</style>

<!--
Appendix for readers, not presented.

If asked: how can the precision threshold be frozen without T2-dev? We freeze the rule today: the student's precision on T2-final must be at least GLiNER2-PII's on T2-dev. That number is recorded on T2-dev before any tuning.
-->
