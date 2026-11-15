---
eyebrow: Appendix for readers
---

# Metrics and test sets

<div class="appx cols">
<div>

### The public test set

1,000 OpenPII-1M validation texts, 250 per language (French, German, Italian, English), drawn with seed 42 from a pinned commit. We never use them for training. The two candidate public test sets gave similar recall: 80.6 % and 81.8 %. We chose OpenPII-1M because it is harder and cleaner.

### Our own test set

About 200 app-like snippets of what users send through our app: prompts, e-mails, documents, CSV tables, pasted code or logs. For an attached file (PDF, TXT, DOCX, CSV), the snippet is the text extracted from it, because that is what the detector receives. We plant values in them, including Swiss identifiers (AVS numbers starting with 756, Swiss IBANs, +41 phone numbers, postal codes), so we know the labels by construction. We also label any sensitive value a snippet already holds. By 30 November, before any tuning, we freeze the annotation policy, groups, mix of types and formats, and hashes. Titles, ages, sex and gender count as personal data.

</div>
<div>

### Our development set and our final test set

Before any tuning, we split our own test set in two. Our development set sets thresholds and runs the gate. Our final test set is kept apart and run once at the end, on the selected models. Related snippets stay on the same side.

### Recall, the primary metric

Both sets carry gold character offsets: the exact position of each true entity. An entity counts as protected only if every non-whitespace character is masked, so a partly masked name or IBAN is a leak. Recall is the micro-average of this rule over the true entities, also reported per entity type. One minus recall is the leak rate.

### Character precision

The share of masked non-whitespace characters that belong to a true entity. It shows over-masking: a model that masks everything fails it. In the example of slide 10, masking the whole line gives $11/36 = 0.31$: the line has 36 non-whitespace characters, 11 of them in the name.

</div>
</div>

<!--
Appendix for readers, not presented.
-->
