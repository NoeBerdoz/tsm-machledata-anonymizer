---
part: 2
eyebrow: Teacher and student
clicks: 4
source: 'Planned: v1 at the end of November, v2 and v3 around 10 December.'
---

# Three steps lead from GLiNER2-PII *to our laptop model*

<ModelChain />

<!--
Target time 0:35. Speaker: to assign.

Here is our plan, from GLiNER2-PII as published.
[click] Fine-tuning on 50,000 labelled rows gives the teacher, v1. It learns the types it misses today, like titles and ages.
[click] The student learns from the teacher and the true labels. It has fewer layers and a smaller dictionary.
[click] Quantization stores the weights in 1 byte. This gives our app model, v3. Our goal: at least 8 times smaller than the teacher.
[click] In the app, the model finds the name. Rules find the AVS number. The app sends placeholders.

If asked: how will the student start? Not decided yet. The usual choice, DistilBERT's, is to copy every second layer of the teacher, then train.
If asked: how many layers? We pick the number that keeps 95 % of the teacher's recall and still meets 8 times smaller. 6 is our estimate. 8 layers would still pass 8 times.
If asked: how do we know the teacher helps? A control student, the same model trained on the same data without the teacher, tells us. We report which one wins.
If asked: does the teacher run on the laptop? Only once, to time it for O3. The app only runs v3.
-->
