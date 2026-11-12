---
part: 2
eyebrow: Distillation
source: 'Hinton, Vinyals and Dean (2015), Distilling the knowledge in a neural network'
clicks: 4
---

# The loss pulls the student toward *two targets*

The same sentence goes into both models. Only the student learns.

<DistillLoss />

<!--
Target time 0:45. Speaker: to assign.

Here is the student's answer for Dupont: a probability for each type.
[click] First target: the ground truth. CE pulls the answer toward PERSON, 100 percent.
[click] Second target: the teacher's soft labels, at temperature 4. KL pulls the student's soft labels toward them. So LOCATION goes up.
[click] Alpha mixes the two parts. Tau squared keeps them balanced when tau changes.
[click] With alpha zero, there is no teacher. That is our control student. Distillation must beat it: goal O1.
-->
