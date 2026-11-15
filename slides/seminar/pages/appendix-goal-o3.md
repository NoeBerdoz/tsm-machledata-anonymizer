---
eyebrow: Appendix for readers
---

# O3 asks for 8 times smaller, and speed is measured

<div class="appx cols goal-appx">
<div>

### O3 Compression

<p class="goal-s">By the final talk, the delivered student is at least <span class="figure-num">8</span> times smaller than the fp32 teacher: at most <span class="figure-num">155.5 MB</span>, with every file it needs.</p>

### How we measure it

One curve point per step, at least 4: fp32 teacher, pruned vocabulary, int8, distilled student. Each point has its recall, size and p95 latency, so each step shows its cost.

### Reported, with no threshold

The speed: p95 latency on an Intel Core <span class="n">i5-1130G7</span>, 300 calls per model.

</div>
<div>

### Why these numbers

<div class="why-row"><span class="k">8x</span><p>Estimate for 6 layers, four languages and int8, embeddings included: <span class="n">about 137 MB</span>, 9.1 times smaller, <span class="n">19 MB</span> under the limit. <span class="src">docs/baselines.md</span></p></div>
<div class="why-row"><span class="k">Vocabulary</span><p>The dictionary is <span class="n">63 %</span> of the teacher. Kept tokens come from the training data, never from a test set. <span class="src">docs/baselines.md</span></p></div>
<div class="why-row"><span class="k">Speed</span><p>Not measured on the reference laptop yet. With half the layers, DistilBERT was only 1.63 times faster. <span class="src">Sanh et al., 2019</span></p></div>

### Stretch goals, not promised

12 times smaller, with int4 embeddings and fewer tokens together: 13.6 times, an estimate. And 2 times faster.

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

If asked: does 8 times smaller mean faster? Not by itself. We measure the latency on the reference laptop. 2 times faster is a stretch goal.
-->
