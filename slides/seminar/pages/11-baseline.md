---
part: 4
clicks: 2
source: 'Development machine (Apple M5 Max). T1 candidate: ai4privacy OpenPII-1M, validation. Swiss set: 634 public texts with fake Swiss IDs. Full tables in the appendix.'
---

# Our tests favour *GLiNER2-PII* as the teacher

Measured before any training. T2, our own test set, is in progress.

<Baseline />

<!--
Target time 0:35. Speaker: to assign.

Before any training, we measured four detectors on T1, 1,000 public texts. GLiNER2-PII finds the most, so our tests favour it as the teacher.
[click] Most misses are types it has no label for, like age. Without them, it reaches 92 percent.
[click] On our Swiss set, the regex and the model cover different misses. Together, they pass O1's 99 percent.
-->
