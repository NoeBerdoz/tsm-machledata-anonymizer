---
theme: default
title: Distilling and quantizing a PII detector
info: Seminar talk, TSM_MachLeData, 2026-11-16. 8 minutes plus 3 minutes of questions.
exportFilename: seminar
---

# Distilling and quantizing a PII detector

How small can an anonymizer get before it starts to leak?

TODO: team names

---

# The setting (1 min)

- A coding agent sends tool outputs to a cloud model, personal data included
- A local model replaces sensitive values with placeholders, and hooks restore them
- The detector runs on every agent turn, so it must be small and fast

TODO: one diagram of the mask and restore loop

---

# Knowledge distillation (2 min)

- Teacher soft labels carry more information than hard labels
- Token-level loss for span detection: TODO formula
- Temperature and the mix of soft and gold loss
- Why we train a gold-label control student of the same size

---

# Quantization (2 min)

- From fp32 to int8: scale, zero point, rounding error
- Post-training quantization versus quantization-aware training
- Where the size goes: 63 % of GLiNER2-PII is word embeddings
- What vocabulary pruning removes before any distillation

---

# SMART goals (1.5 min)

| Goal | Target |
|---|---|
| O1 Protection | Student recall ≥ 95 % of teacher, Swiss IDs ≥ 99 % |
| O2 Utility | Char. precision ≥ GLiNER2-PII, 90 % of agent tasks |
| O3 Compression | ≥ 12× smaller, p95 ≤ ¼ of teacher |
| O4 Integration | Leaks within budget, 0 silent fallbacks |
| O5 MLOps | Gated publication, one alert |

TODO: thresholds decided at v0

---

# Baseline v0 (1.5 min)

TODO: recall, character precision, size and p95 latency of regex, Presidio, GLiNER2-PII and the OpenAI Privacy Filter on T2-dev

---

# Next steps

v1 teacher, v2 student and control, v3 quantized student. Questions?
