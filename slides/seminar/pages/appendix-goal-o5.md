---
eyebrow: Appendix for readers
---

# O5 shows our pipeline at work by 7 December

<div class="appx cols goal-appx">
<div>

### O5 MLOps pipeline, cloud deployment and monitoring

<p class="goal-s">Every model version the app installs has a passing gate record in MLflow for the same file hash. We count the versions without one: the target is <span class="n">0</span>. By <span class="date">7 December 2026</span>, five scenarios must all pass.</p>

- A degraded model, at least 3 recall points below the good one on our development set, fails the recall threshold.
- A model without evaluation results is refused.
- A good model is published. The app installs it and shows its version.
- When a download fails, the app keeps its last approved version.
- An injected slowdown fires the Sentry alert.

</div>
<div>

### Why this goal

<div class="why-row"><span class="k">Cloud</span><p>The kickoff asks for cloud training, deployment and monitoring. On 19 October, the teachers said laptop inference is enough if training runs in the cloud. <span class="src">docs/smart-goals.md</span></p></div>
<div class="why-row"><span class="k">7 Dec.</span><p>22 days from 15 November. The gate must work before the final student arrives, around 10 December. <span class="src">docs/smart-goals.md</span></p></div>

### Why we can reach it

Cloud training already works (9 November, <span class="n">about USD 0.13</span>). The gate reuses the O1 to O3 scripts. <span class="src">docs/cloud-training.md</span>

### How we check it

Demonstration thresholds and the alert rule are written in advance in params.yaml. A demonstration approval never releases a model. The final student is accepted after v3, against the frozen thresholds of O1 to O3. User feedback and a smoke run on each merge are optional.

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
.goal-appx .date {
  font-weight: 500;
}
.goal-appx ul {
  margin-top: 8px;
}
.goal-appx li {
  line-height: 1.4;
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

If asked: how can the gate work on 7 December without the final student? It uses demonstration thresholds written in advance in params.yaml. The final student is accepted after v3, against the frozen thresholds of O1 to O3.
-->
