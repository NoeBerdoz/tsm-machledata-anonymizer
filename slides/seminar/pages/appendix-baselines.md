---
eyebrow: Appendix for readers
---

# Baselines in full: the two T1 candidates and the Swiss set

<BaselineTables view="full" />

<div class="appx cols bl-notes">
<div>

Char. prec. is character precision. Privacy Filter ran through the transformers pipeline, not OpenAI's own constrained decoder. T2 is in progress, so no row is on T2-dev yet. Each T1 sample is 1,000 texts of an ai4privacy validation split, 250 per language, with a fixed seed. We chose OpenPII-1M validation as T1.

</div>
<div>

The Swiss set has 634 public rows from the OpenPII-1M sample and the Gretel test split, with fake but valid Swiss values. "Regex +" masks every span that either detector finds. Without the 5 types it has no label for, GLiNER2-PII reaches 92 % on OpenPII-1M and 90 % on open-pii-500k.

</div>
</div>

<style>
.bl-notes {
  margin-top: 22px;
  font-size: 16px;
  line-height: 1.42;
  color: var(--muted);
}
</style>

<!--
Appendix for readers, not presented. Sources: docs/baselines.md, docs/swiss-identifiers.md and results/summary.md on main. Measured on a development machine (Apple M5 Max).
-->

---
eyebrow: Appendix for readers
---

# The app's engine today, on the same 200 texts

<BaselineTables view="subset" />

<div class="appx cols bl-notes">
<div>

Recall and character precision (char. prec.). The app's engine today is qwen3:4b through Ollama, with its own rules. It stands in for our student until the pipeline delivers one. A 4B model is slow, so every detector ran on the same 200 texts per set, 50 per language. Compare these rows only with each other, not with the 1,000-text rows.

</div>
<div>

The engine finds about 63 % of the entities, about 20 points below GLiNER2-PII, and masks more text that is not personal data. Its rules find all 251 Swiss values. Its model is already quantized to 4 bits, and its files still weigh twice GLiNER2-PII's.

</div>
</div>

<style>
.bl-notes {
  margin-top: 22px;
  font-size: 16px;
  line-height: 1.42;
  color: var(--muted);
}
</style>

<!--
Appendix for readers, not presented. Sources: docs/baselines.md and results/summary.md on main. Measured on a development machine (Apple M5 Max).
-->

---
eyebrow: Appendix for readers
---

# Time per call, on our development machine

<BaselineTables view="latency" />

<div class="appx cols bl-notes">
<div>

p50 and p95 are the times that 50 and 95 of 100 calls stay under. Each detector made 5 warm-up calls, then 10 runs on each of 30 OpenPII-1M texts (12 to 177 words), so 300 timed calls. These 30 texts are a temporary sample until T2-dev exists.

</div>
<div>

On the CPU, the engine's p95 is 48 times GLiNER2-PII's. On the GPU, as the app runs it, it is still about 7 times GLiNER2-PII on the CPU. These numbers compare only with each other. The official O3 numbers come from the reference laptop.

</div>
</div>

<style>
.bl-notes {
  margin-top: 22px;
  font-size: 16px;
  line-height: 1.42;
  color: var(--muted);
}
</style>

<!--
Appendix for readers, not presented. Sources: docs/baselines.md and results/summary.md on main. Measured on 2026-11-10 on an Apple M5 Max.
-->
