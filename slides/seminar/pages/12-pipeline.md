---
part: 5
clicks: 6
---

# The pipeline decides *what reaches users*

<PipelineTrail lede="Our planned pipeline, ready by 7 December 2026." />

<!--
Target time 0:55. Speaker: to assign.

Our planned pipeline. DVC tracks the data and the models. GitHub Actions tests each merge.
[click] We train on Google Cloud. MLflow records each run: models A and B.
[click] The gate checks each model on T2-dev. A's recall is under the goal, so A is refused. B passes.
[click] MLflow publishes B as version 4. The laptop app updates. Only the model reaches the laptop.
[click] Sentry records times and errors, never the prompt or the answer. When the p95 crosses the line, we get an alert.
[click] People review the users' ratings and plan the next run.
[click] The loop starts again: our plan for 7 December.
-->
