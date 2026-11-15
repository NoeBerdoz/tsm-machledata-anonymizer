---
eyebrow: Appendix for readers
---

# O1 asks for 95 % of the teacher's recall

<div class="appx cols goal-appx">
<div>

### O1 Protection

<p class="goal-s">By the final talk in mid-December 2026, the delivered student keeps at least <span class="figure-num">95 %</span> of the fine-tuned teacher's recall, on the public test set and on our final test set, each set separately, and never falls below <span class="n">GLiNER2-PII</span> as published (<span class="n">80.6 %</span> on the public set). With the regex, Swiss IDs reach at least <span class="figure-num">99 %</span> recall on our final test set.</p>

### How we measure it

An entity counts as protected only if every character except spaces is masked. The 95 % and the floor compare the models alone, without the regex, so they measure compression. The 99 % measures the app's detector, the regex and the model, pooled over AVS numbers, IBANs and phone numbers. Decisions use the unrounded counts.

</div>
<div>

### Why these numbers

<div class="why-row"><span class="k">95 %</span><p>Compression costs some recall. With half the layers, DistilBERT kept <span class="n">97 %</span> of BERT's score. <span class="src">Sanh et al., 2019</span></p></div>
<div class="why-row"><span class="k">99 %</span><p>The regex and <span class="n">GLiNER2-PII</span> already find 775 of 781 Swiss values, <span class="n">99.2 %</span>. Pooled, this hides AVS numbers at 164 of 168, <span class="n">97.6 %</span>. <span class="src">results/recall_per_type.csv</span></p></div>

### Why we can reach it

Two thirds of <span class="n">GLiNER2-PII's</span> misses are types it has no label for, and our training data labels them. On the public test set, a teacher at <span class="n">85 %</span> makes the floor follow from the 95 % rule: <span class="n">95 %</span> of it is <span class="n">80.75 %</span>, above <span class="n">80.6 %</span>. Cloud training works (9 November), but that test covered 13 types only. <span class="src">docs/smart-goals.md</span>

### Also reported

The absolute recall, overall and per type: a teacher at <span class="n">90 %</span> allows <span class="n">85.5 %</span>. Each Swiss type's counts, the regex with the model, <span class="n">GLiNER2-PII</span> per type, and a control student.

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
