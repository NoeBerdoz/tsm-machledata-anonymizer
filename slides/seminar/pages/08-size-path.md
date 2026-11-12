---
part: 3
clicks: 4
source: 'Size estimates at 1 byte per weight in int8 and half a byte in int4, tokenizer counted. Assumptions in the appendix.'
---

# 12 times smaller takes *more than int8*

<SizePath />

<!--
Target time 0:45. Speaker: to assign.

Two ways to get int8. PTQ rounds a trained model with no retraining. QAT trains with the rounding, so the model adapts to it.
[click] Our current goal: 12 times smaller. The teacher measures 1,244 megabytes. Int8 with the smaller dictionary: about 7 times.
[click] A six-layer student: about 9 times.
[click] Int4 embeddings or fewer tokens: 11.6 each, just under the goal.
[click] Both: 13.6 times. These are estimates, so recall must be measured after each step.
-->
