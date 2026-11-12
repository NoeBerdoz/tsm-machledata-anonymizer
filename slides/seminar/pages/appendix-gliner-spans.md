---
eyebrow: Appendix for readers
---

# Distillation for GLiNER2 spans

<div class="appx cols">
<div>

### From classes to span and type pairs

The slides use a simple example: one softmax over four classes. GLiNER2 works differently (Zaratiana et al. 2025). It scores each pair of a candidate text span and an entity type. A sigmoid $\sigma$ turns each score into a probability between 0 and 1. So each pair is a yes or no decision with its own probability.

$$p_T = \sigma(z_T/\tau), \qquad p_S = \sigma(z_S/\tau)$$

Here $z_T$ and $z_S$ are the scores of the teacher $T$ and the student $S$ for the same pair, and $\tau$ is the temperature. We sum both parts of the loss over the span and type pairs, with the same weights $\alpha$ and $\tau^2$. The teacher and the student score the same pairs, so each part compares like with like.

</div>
<div>

### The soft part becomes a binary KL

For each pair, the soft part is the Kullback-Leibler divergence (KL) between two yes or no distributions.

$$\mathrm{KL}(p_T\,\|\,p_S) = p_T \log\frac{p_T}{p_S} + (1-p_T)\log\frac{1-p_T}{1-p_S}$$

### The ground truth part becomes a binary cross-entropy

For each pair, the ground truth $y$ is 1 if the span is an entity of this type, and 0 if not. At $\tau = 1$ this part is the binary cross-entropy (BCE).

$$\mathrm{BCE}(y, p_S) = -\big[\,y \log p_S + (1-y)\log(1-p_S)\,\big]$$

</div>
</div>

<!--
Appendix for readers, not presented.
-->
