---
eyebrow: Appendix for readers
---

# Metrics and test sets

<div class="appx cols">
<div>

### T1

The validation split of the training set, in French, German, Italian and English. We never use it for training. The training set, and so T1, is still open: we choose it by 16 November, between OpenPII-1M and open-pii-masking-500k. The numbers so far favour OpenPII-1M: both give GLiNER2 the same recall, and OpenPII-1M is the harder and cleaner test.

### T2

Our own set of about 200 snippets of what users send through our app: prompts, e-mails, documents, CSV tables, pasted code or logs. For an attached file (PDF, TXT, DOCX, CSV), the snippet is the text extracted from it, because that is what the detector receives. We plant values in them, including Swiss identifiers (AVS numbers starting with 756, Swiss IBANs, +41 phone numbers, postal codes), so we know the labels by construction. We also label any sensitive value a snippet already holds.

</div>
<div>

### T2-dev and T2-final

Before any tuning we split T2 into T2-dev, for thresholds and the gate, and a fixed T2-final, run only on the selected models. Related snippets stay on the same side.

### Recall, the primary metric

Both sets carry gold character offsets: the exact position of each true entity. An entity counts as protected only if all its characters are masked, so a partly masked IBAN is a leak. Recall is the micro-average of this rule over the true entities, also reported per entity type. One minus recall is the leak rate.

### Character precision

The share of masked characters that belong to a true entity. It shows over-masking: a model that masks everything fails it. In the example of slide 10, masking the whole 54-character line gives $26/54 = 0.48$.

</div>
</div>

<!--
Appendix for readers, not presented.
-->
