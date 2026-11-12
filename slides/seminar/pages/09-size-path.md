---
part: 3
clicks: 4
source: 'Size estimates at 1 byte per weight in int8 and half a byte in int4, tokenizer counted. Assumptions in the appendix.'
---

# Int8 is not enough to make our model *12 times smaller*

<SizePath />

<!--
Target time 0:45. Speaker: to assign.

Our current goal: 12 times smaller. The teacher measures 1,244 megabytes. Int8 with the smaller dictionary: about 7 times.
[click] A six-layer student: about 9 times.
[click] An int4 dictionary or fewer tokens: 11.6 each, just under the goal.
[click] Both: 13.6 times. Recall must be measured after each step.
[click] Two ways to apply the rounding. PTQ rounds a trained model, with no retraining. QAT trains with the rounding, so the model can adapt.
-->
