---
part: 4
clicks: 3
---

# In our evaluation, a partly masked entity *is still a leak*

<p class="lede sub">Protected means fully masked.</p>

<LeakCount :step="$clicks" />

<!--
Target time 0:35. Speaker: to assign.

Now, evaluation: how do we know a model protects enough? Our example: the name from slide 2, Marie Dupont. Our regex finds no names. Only the model can.
[click] Fully masked: protected. Recall 1 of 1, character precision 1.
[click] Only the first name is masked. Dupont stays visible: a leak. Recall drops to 0, though only personal characters were masked.
[click] Masking everything is too much: character precision drops to 0.31.

If asked: why not an IBAN? Our regex already finds most IBANs. Names are where the model, the part we compress, does the work.
If asked: in OpenPII-1M, the first name and the surname are two separate entities. There, this mask protects one of the two.
-->
