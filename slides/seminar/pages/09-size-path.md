---
part: 3
clicks: 4
source: 'Size estimates at 1 byte per weight in int8 and half a byte in int4, tokenizer counted.'
---

# Int8 is not enough to make our model *8 times smaller*

<SizePath />

<!--
Target time 0:45. Speaker: to assign.

Our goal: 8 times smaller than 1,244 megabytes, so at most about 155. Int8 with the smaller dictionary: about 7 times, not enough.
[click] A six-layer student: about 9 times. On paper, that reaches the goal.
[click] Two options, int4 or fewer tokens: 11.6 times each, toward our stretch goal of 12.
[click] Both: 13.6 times. Recall must be measured after each step.
[click] Two ways to apply the rounding. PTQ rounds a trained model, with no retraining. QAT trains with the rounding, so the model can adapt.
-->
