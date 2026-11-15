---
eyebrow: Appendix for readers
---

# O3 asks for 8 times smaller and 1.5 times faster

<div class="appx cols goal-appx">
<div>

### O3 Compression

<p class="goal-s">By the final talk, the delivered student is at least <span class="figure-num">8</span> times smaller than the fp32 teacher, at most <span class="n">about <span class="figure-num">155.6 MB</span></span> with every file, in exact bytes, and at least <span class="figure-num">1.5</span> times faster: its p95 latency is at most two thirds of the teacher's.</p>

### How we measure it

Speed is the p95 latency of both models on an Intel Core <span class="n">i5-1130G7</span>, 300 calls each, on 30 texts drawn from our development set with a fixed seed, across its sources, before any timing. We time both models in the student's runtime when it can run the teacher. Otherwise the ratio is the speedup of the deployed system, and we name both runtimes. One curve point per step, at least 4: fp32 teacher, pruned vocabulary, int8, distilled student.

</div>
<div>

### Why these numbers

<div class="why-row"><span class="k">8x</span><p>Estimate for 6 layers, four languages and int8, embeddings included: <span class="n">about 137 MB</span>, 9.1 times smaller. <span class="src">docs/baselines.md</span></p></div>
<div class="why-row"><span class="k">Vocabulary</span><p>The dictionary is <span class="n">63 %</span> of the teacher. Kept tokens come from training data, never a test set. <span class="src">docs/baselines.md</span></p></div>
<div class="why-row"><span class="k">1.5x</span><p>The model runs before every request. Half the layers made DistilBERT 1.63 times faster, and int8 usually adds speed, not yet measured on our model. <span class="src">Sanh et al., 2019</span></p></div>

### Stretch goals, not promised

12 times smaller, with int4 embeddings and fewer tokens together: 13.6 times, an estimate. 2 times faster: a smaller dictionary saves space, not time.

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

If asked: does 8 times smaller mean faster? Not by itself. That is why O3 also asks for 1.5 times faster, measured on the reference laptop. 2 times faster is a stretch goal.

If asked: why only 1.5 times? Half the layers made DistilBERT 1.63 times faster, and we have no measurement on the reference laptop yet. It comes with the latency sample from our development set.
-->
