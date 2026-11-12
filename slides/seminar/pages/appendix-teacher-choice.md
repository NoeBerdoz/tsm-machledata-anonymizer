---
eyebrow: Appendix for readers
source: "T1 samples: 1,000 texts each. Swiss IDs: 781 values in 634 rows. Times: Apple M5 Max, CPU, 4 threads, texts of 12 to 177 words. Privacy Filter ran through the transformers pipeline, not OpenAI's own decoder."
---

# Why GLiNER2-PII and not OpenAI's Privacy Filter

<TeacherChoice />

<div class="appx choice-take">

The regex finds the Swiss numbers. Our model must find the rest, such as names and places. There, GLiNER2-PII finds much more.

Privacy Filter is better on dates and ID numbers, but with our regex both pass 99 % on Swiss IDs.

</div>

<style>
.choice-take {
  margin-top: 22px;
  color: var(--ink);
}
</style>

<!--
Appendix for readers, not presented. If asked: we measured both models as published. GLiNER2-PII finds more names and places, and that is our model's job. Privacy Filter is better on dates and ID numbers, but our regex covers the Swiss ones. GLiNER2-PII also knows 42 types instead of 8, and it is less than half the size. Sources: docs/baselines.md, docs/swiss-identifiers.md and results/ on main.
-->
