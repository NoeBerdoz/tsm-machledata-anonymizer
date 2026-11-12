---
part: 4
clicks: 3
---

# A partly masked entity *is a leak*

<p class="lede sub">An entity is protected only if all its characters are masked.</p>

<LeakCount :step="$clicks" />

<!--
Target time 0:35. Speaker: to assign.

An example CSV line in a prompt. The true entity is a Swiss IBAN, 26 characters.
[click] Fully masked: protected. Recall 1 of 1, character precision 1.
[click] The last digits stay visible: a leak. Recall drops to 0, even though only personal characters were masked.
[click] The whole line masked: protected, but too much. Character precision drops to 0.48.
-->
