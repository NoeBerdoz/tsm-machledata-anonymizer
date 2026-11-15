---
part: 5
clicks: 6
---

# The pipeline decides *what reaches users*

<PipelineTrail lede="Our planned pipeline." />

<!--
Target time 0:55. Speaker: to assign.

Our planned pipeline. DVC tracks the data and the models. GitHub Actions tests each merge.
[click] We train on Google Cloud. MLflow records each run: models A and B.
[click] The gate checks each model on our development set. A's recall is under the goal, so A is refused. B passes.
[click] MLflow publishes B as version 4. Only the model reaches the laptop.
[click] Sentry records how long the model takes on each request, never the prompt or the answer. This line shows how long 95 of 100 requests take, at most. When it crosses the red line, we get an alert.
[click] Users review the results. These ratings are optional.
[click] Then the loop starts again.

If asked: the line is the p95: 95 of 100 requests are faster than it. An average would hide the slow ones.
-->
