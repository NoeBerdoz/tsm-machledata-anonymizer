---
part: 4
clicks: 3
---

# Evaluation: a partly masked entity *is still a leak*

<p class="lede sub">Protected means fully masked.</p>

<LeakCount :step="$clicks" />

<!--
Target time 0:35. Speaker: to assign.

Now, evaluation: how do we know a model protects enough? Our example: a Swiss IBAN of 21 characters, in a CSV line.
[click] Fully masked: protected. Recall 1 of 1, character precision 1.
[click] The last digits stay visible: a leak. Recall drops to 0, though only personal characters were masked.
[click] Masking everything is too much: character precision drops to 0.43.
-->
