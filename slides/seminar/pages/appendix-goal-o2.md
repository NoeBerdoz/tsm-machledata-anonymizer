---
eyebrow: Appendix for readers
---

# O2 asks that 90 % of solved test prompts still work

<div class="appx cols goal-appx">
<div>

### O2 Utility

<p class="goal-s">By the final talk, at least <span class="figure-num">90 %</span> of the test prompts solved without pseudonymization stay solved with it. The student's character precision on <span class="n">T2-final</span> is at least <span class="n">GLiNER2-PII's</span> on the same set.</p>

### How we measure it

A test prompt is a prompt, with or without an attached file, and an answer check fixed in advance. 20 of them run through our app with and without pseudonymization, with a pinned OpenAI model version and settings. Each runs 3 times per condition, and is solved when its check passes 2 of 3 times. At least 18 must work without pseudonymization. The prompts and these results are frozen before any run with it.

### Reported, with no threshold

Both counts. Also 5 stress prompts that need to link two forms of one person, such as Marie Dupont in a table with her names in two cells. Linking is out of scope, so they are reported apart.

</div>
<div>

### Why these numbers

<div class="why-row"><span class="k">90 %</span><p>O1 alone can be met by masking everything. O2 checks that the answers stay useful. With 20 solved prompts, at most 2 may break. With 18 or 19, at most 1 may break. <span class="src">docs/smart-goals.md</span></p></div>
<div class="why-row"><span class="k">Precision</span><p>The precision floor limits how much is masked by mistake. Both models are compared on the same set. <span class="src">docs/smart-goals.md</span></p></div>

### The limit

No app result yet: the test prompts run once the app and the backend are ready. That is 120 calls per model version, 150 with the stress prompts.

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

If asked: how can the precision threshold be frozen without T2? We freeze the rule today. The final check compares both models on T2-final. For the development gate, GLiNER2-PII's precision is recorded on T2-dev before any tuning.
-->
