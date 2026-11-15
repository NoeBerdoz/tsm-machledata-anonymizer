---
part: 4
clicks: 5
---

# Five *SMART* goals

We check O1 to O4 at the final talk, in mid-December.

<Goals />

<!--
Target time 0:30. Speaker: to assign.

Our five SMART goals. We check four at the final talk, in mid-December.
[click] Protection: the student keeps 95 percent of the teacher's recall. And with the regex, our app finds 99 percent of Swiss IDs.
[click] Utility: of the test prompts that work without placeholders, at least 90 percent still work with them.
[click] Compression: 8 times smaller, and 1.5 times faster.
[click] End to end: the app restores intact placeholders exactly, and adds no leak.
[click] MLOps: zero models reach the app without passing the quality gate. By 7 December, we show the gate at work and trigger one speed alert.

If asked: is 95 % of a weak teacher enough? The student must also never fall below GLiNER2-PII as published: 80.6 % on T1.
If asked: does the regex count in the 95 %? No. The 95 % and the floor compare the models alone, so they measure compression. The Swiss 99 % measures the app's detector, the regex and the model together.
If asked: what about a question that links a name written two ways, like Marie Dupont with her names in two cells? Five stress prompts test exactly that. Linking is out of scope, so we report them apart.
If asked: how do we count the zero? Every model version the app installs must have a passing gate record in MLflow for the same file hash. We count the installed versions without one, over the whole project. The target is 0. By 7 December, five scenarios must all pass. A degraded model, at least 3 recall points worse, fails the gate. A model without results is refused. A good model is published, and the app installs it and shows its version. When a download fails, the app keeps its last approved version. An injected slowdown fires the alert. We fix these demonstration thresholds beforehand. The final student must pass the final thresholds after v3.
-->
