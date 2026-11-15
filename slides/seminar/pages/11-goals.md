---
part: 4
clicks: 5
---

# Five *SMART* goals

<Goals />

<!--
Target time 0:35. Speaker: to assign.

Our five SMART goals. We check them at the final talk, and the pipeline by 7 December.
[click] Protection: the student keeps 95 percent of the teacher's recall.
[click] Utility: 90 percent of the solved test prompts still work with placeholders.
[click] Compression: 8 times smaller, 1.5 times faster.
[click] The last two are pass-or-fail goals, so their target is zero. End to end: our app adds no leak.
[click] MLOps: no model reaches the app without passing the gate.

If asked: is 95 % of a weak teacher enough? The student must also never fall below GLiNER2-PII as published: 80.6 % on the public test set.
If asked: does the regex count in the 95 %? No. The 95 % and the floor compare the models alone, so they measure compression. The Swiss 99 % measures the app's detector, the regex and the model together.
If asked: what about a question that links a name written two ways, like Marie Dupont with her names in two cells? Five stress prompts test exactly that. Linking is out of scope, so we report them apart.
If asked: how do we count the zero? Every model version the app installs must have a passing gate record in MLflow for the same file hash. We count the installed versions without one, over the whole project. The target is 0. By 7 December, five scenarios must all pass. A degraded model fails the frozen recall threshold and scores at least 3 recall points below the good model on our development set. A model without results is refused. A good model is published, and the app installs it and shows its version. When a download fails, the app keeps its last approved version. An injected slowdown fires the alert. We fix these demonstration thresholds beforehand. The final student must pass the final thresholds after v3.
If asked: is O4 not just a unit test, either 100 or 0? Yes, pass or fail on purpose. For privacy, the only acceptable number of leaks our own code adds is zero, like zero accidents in safety. We check it on 100 planted values, in everything that leaves the laptop. What the model misses is O1, with 95 %, because a model always makes some mistakes.
-->
