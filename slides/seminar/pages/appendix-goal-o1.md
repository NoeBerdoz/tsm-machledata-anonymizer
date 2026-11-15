---
eyebrow: Appendix for readers
---

# O1 asks for 95 % of the teacher's recall

<div class="appx cols goal-appx">
<div>

### O1 Protection

<p class="goal-s">By the final talk in mid-December 2026, the delivered student keeps at least <span class="figure-num">95 %</span> of the fine-tuned teacher's recall, on T1 and on <span class="n">T2-final</span>, each set separately. With the regex, Swiss IDs reach at least <span class="figure-num">99 %</span> recall.</p>

### How we measure it

An entity counts as found only if every character except spaces is masked. Swiss IDs are AVS numbers, IBANs and phone numbers, counted together.

### Reported, with no threshold

The absolute recall, overall and per type, since <span class="n">95 %</span> is relative: a teacher at <span class="n">90 %</span> allows <span class="n">85.5 %</span>. Also <span class="n">GLiNER2-PII</span> as published, and a control student without the teacher.

</div>
<div>

### Why these numbers

<div class="why-row"><span class="k">95 %</span><p>Compression costs some recall. With half the layers, DistilBERT kept <span class="n">97 %</span> of BERT's score. <span class="src">Sanh et al., 2019</span></p></div>
<div class="why-row"><span class="k">99 %</span><p>The regex and <span class="n">GLiNER2-PII</span> already find 775 of 781 Swiss values, <span class="n">99.2 %</span>. Compression must not break this. <span class="src">results/recall_per_type.csv</span></p></div>

### Why we can reach it

On 9 November, 2 minutes of cloud training on 900 rows raised recall on 13 types from <span class="n">76.5 %</span> to <span class="n">95.4 %</span>. The test rows came from the same dataset, so this is optimistic. <span class="src">docs/cloud-training.md</span>

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

If asked: does 95 % of the teacher's recall mean 95 % protection? No. A teacher at 90 % allows a student at 85.5 %. We report the absolute recall too.

If asked: what if distillation loses to the control student? We report it. Under our budget, distillation then gave no measured benefit. The comparison still answers the question.

If asked: do 99 % and zero added leaks prove the app is safe? No. They are results on fixed test sets, partly synthetic. Unseen inputs can still leak.
-->
