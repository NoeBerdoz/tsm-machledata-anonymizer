---
part: 2
eyebrow: Distillation
source: 'Hinton, Vinyals and Dean (2015), Distilling the knowledge in a neural network'
clicks: 2
---

# Soft labels carry more than the right answer

In distillation, the teacher's prediction becomes the student's target.

<SoftLabels />

<!--
Target time 0:45. Speaker: to assign.

The scores are made up. The ground truth says Dupont is a person: a hard label. The teacher gives a probability to every class: soft labels.
[click] The temperature tau divides each score. A higher tau brings the probabilities closer together. At tau 2, LOCATION gets 24 percent.
[click] At tau 4, 26 percent. The student copies all four values, so it learns that Dupont can also be a place.
-->
