---
eyebrow: Appendix for readers
---

# SMART goals in full, O4 and O5

<div class="appx cols goals-appx">
<div>

### O4 End to end

We send scripted requests through our app, with prompts and attached files that hold 100 planted test values, each with an ID. We measure leaks on what the backend sends to OpenAI. A planted value leaks if any of its characters reaches OpenAI unmasked, and we count each ID once. The leak budget is half the distinct values that leak with GLiNER2-PII in the same requests, rounded down.

On normal responses, 100 % of the replacements come back exactly. This includes the same entity repeated, distinct entities, and text that already looks like a replacement.

The app never fails silently. If the engine fails, the request is not sent and the user is told. We inject such failures on purpose, and zero requests may reach the backend unpseudonymized. In separate tests, every unknown or altered replacement in the response is flagged to the user, never shown as a real value.

</div>
<div>

### O5 MLOps

A model is published to the MLflow registry, with a version, only if it meets on T2-dev the O1 detection thresholds, the O2 character precision threshold and the O3 size and latency thresholds. The 20 app tasks of O2 are not in the gate. MLflow tracks each run, and each model records its code, data and config versions.

The demonstration shows a degraded model refused and a good model published, which the app then installs and whose version it reports. Sentry records the on-device pseudonymization time apart from the full response time, without any prompt or response content. The alert fires when the p95 of that time over a fixed window crosses a threshold, and we trigger it on purpose.

By 7 December 2026, the pipeline, the gate and the monitoring work with the best model available then. The final model is accepted after v3.

</div>
</div>

<style>
.goals-appx {
  font-size: 17px;
  line-height: 1.42;
}
</style>

<!--
Appendix for readers, not presented. The source is docs/smart-goals.md on main.
-->
