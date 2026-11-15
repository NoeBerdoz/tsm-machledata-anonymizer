---
eyebrow: Appendix for readers
source: 'Hinton, Vinyals and Dean (2015), Distilling the knowledge in a neural network'
---

# The loss pulls the student toward two targets

The same sentence goes into both models. Only the student learns.

<DistillLoss still />

<!--
Appendix for readers, not presented.

If asked: how does the student learn? Here is the student's answer for Dupont, a probability for each type. First target: the ground truth. CE pulls the answer toward PERSON, 100 percent. Second target: the teacher's soft labels, at temperature 4. KL pulls the student's soft labels toward them, so LOCATION goes up. Alpha mixes the two parts. Tau squared keeps them balanced when tau changes. With alpha zero, there is no teacher: that is our control student. We report which one wins, under goal O1.
-->
