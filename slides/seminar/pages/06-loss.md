---
part: 2
eyebrow: Distillation
source: 'Hinton, Vinyals and Dean (2015), Distilling the knowledge in a neural network'
clicks: 2
---

# The loss pulls the student toward *two targets*

<DistillLoss />

<!--
Target time 0:45. Speaker: to assign.

The loss has two parts. KL pulls the student's soft labels toward the teacher's. CE pulls its answer toward the ground truth. Alpha mixes the two. Tau squared keeps the pull steady when the temperature changes.
[click] At alpha 0.5, the answer sits between the two targets: PERSON 91 percent, LOCATION 7.
[click] The control student uses alpha 0, so only the ground truth. Distillation must beat it.
-->
