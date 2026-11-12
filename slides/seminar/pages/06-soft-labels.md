---
part: 2
eyebrow: Distillation
source: 'Hinton, Vinyals and Dean (2015), Distilling the knowledge in a neural network'
clicks: 4
---

# The teacher also shows what else a word can be

<SoftLabels />

<!--
Target time 0:45. Speaker: to assign.

Here, each word gets a type. Take Dupont.
[click] Dupont appears twice: a person, then part of a street. A model can hesitate.
[click] The ground truth says person, 100 percent: a hard label. It says nothing about the other types.
[click] The teacher gives a probability to each type: soft labels. They show its doubt: Dupont might be a place.
[click] Small values almost vanish. A higher temperature, here 4, spreads the probabilities. Now the student also sees the second choices.
-->
