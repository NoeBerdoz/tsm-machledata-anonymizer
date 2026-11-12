---
eyebrow: Appendix for readers
---

# Distillation in detail

<div class="appx cols distil-appx">
<div>

### Soft labels with a temperature

The teacher gives a score $z_i$ to each class $i$. The softmax with the temperature $\tau$ turns these scores into probabilities.

$$p_i^{\tau} = \frac{e^{z_i/\tau}}{\sum_j e^{z_j/\tau}}$$

At $\tau = 1$ this is the usual softmax. A higher $\tau$ makes the probabilities flatter. The student then also sees how the teacher ranks the wrong classes.

### The example of slides 6 and 7

The scores are made up: $z = (4.0,\ 2.2,\ 0.6,\ 0.0)$ for PERSON, LOCATION, ORGANIZATION and NONE. They show doubt in the teacher, not evidence that this Dupont is a place.

<div class="soft-table">
  <span class="th">TEMPERATURE</span><span class="th">PERSON</span><span class="th">LOCATION</span><span class="th">ORGANIZATION</span><span class="th">NONE</span>
  <span><Tex e="\tau = 1" /></span><span>82.2 %</span><span>13.6 %</span><span>2.7 %</span><span>1.5 %</span>
  <span><Tex e="\tau = 2" /></span><span>58.0 %</span><span>23.6 %</span><span>10.6 %</span><span>7.8 %</span>
  <span><Tex e="\tau = 4" /></span><span>41.1 %</span><span>26.2 %</span><span>17.6 %</span><span>15.1 %</span>
</div>

Rounded to whole percents, as on the slides, the four values can add up to 101 %.

</div>
<div>

### The loss

$$\mathcal{L} = (1-\alpha)\,\mathrm{CE}\big(y,\,p_S\big) + \alpha\,\tau^2\,\mathrm{KL}\big(p_T^{\tau}\,\|\,p_S^{\tau}\big)$$

CE (cross-entropy) measures how far the student's answer $p_S$, at $\tau = 1$, is from the ground truth $y$. KL (Kullback-Leibler divergence) measures how far the student's soft labels $p_S^{\tau}$ are from the teacher's $p_T^{\tau}$. The weight $\alpha$, from 0 to 1, sets the mix.

### What slide 7 draws

A student during training, with made-up scores $z_S = (2.0,\ 0,\ 0,\ 0)$: its answer at $\tau = 1$ is 71.1 / 9.6 / 9.6 / 9.6 %, its soft labels at $\tau = 4$ are 35.5 / 21.5 / 21.5 / 21.5 %. CE pulls the answer toward the ground truth, KL pulls the soft labels toward the teacher's. On LOCATION the two pulls disagree.

### Why the factor $\tau^2$

Hinton, Vinyals and Dean (2015) show that the gradients of the soft part shrink as $1/\tau^2$ when $\tau$ is high. Multiplying by $\tau^2$ keeps the pull about the same when the temperature changes.

### The control of goal O1

The control student has the same architecture, data and training budget, but learns from the ground truth only: $\alpha = 0$. Distillation counts only if it beats the control on recall.

</div>
</div>

<style>
.distil-appx {
  margin-top: 18px;
  font-size: 16px;
  line-height: 1.34;
}
.distil-appx p {
  line-height: 1.34;
}
.distil-appx p + p {
  margin-top: 6px;
}
.distil-appx * + h3 {
  margin-top: 9px;
}
.distil-appx .katex-display {
  margin: 6px 0;
}
/* the headings are uppercase: the math in them must keep its own case */
.distil-appx h3 .katex {
  text-transform: none;
}
.soft-table {
  display: grid;
  grid-template-columns: 1.1fr 1fr 1fr 1.3fr 0.9fr;
  margin: 10px 0 8px;
  font-variant-numeric: lining-nums tabular-nums;
}
.soft-table > span {
  padding: 2px 0;
  border-bottom: 1px solid var(--hair);
}
.soft-table .th {
  font-family: var(--mono);
  font-size: 13px;
  letter-spacing: 0.08em;
  color: var(--muted-2);
  border-bottom-color: var(--ink);
}
</style>

<!--
Appendix for readers, not presented.
-->
