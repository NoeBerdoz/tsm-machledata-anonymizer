---
theme: default
title: What compression costs in protection
info: Final talk, TSM_MachLeData, mid-December 2026. 8 minutes plus 3 minutes of questions.
exportFilename: final
---

# What compression costs in protection

Quantitative analysis of a distilled and quantized PII detector

TODO: team names

---

# Recap of the method (1 min)

Teacher fine-tuning, distillation with a gold-label control, quantization.

Pseudonymization, not anonymization: the mapping table on the device can put the real values back.

---

# The compression curve (2 min)

TODO: recall and character precision against size, one point per model (fp32, int8, distilled int8, and the options)

---

# Did distillation earn its place? (1.5 min)

TODO: distilled student versus gold-label control at equal size and budget

---

# Per-type recall and Swiss identifiers (1 min)

TODO: per-type recall against the v0 floor

---

# Latency on the reference CPU (1 min)

TODO: p50 and p95 against the O3 budget

---

# The app end to end (1 min)

TODO: leaks in what the backend sends to OpenAI, utility through the app, restoration

---

# SMART goals: met or not (0.5 min)

TODO: one line per goal, with the measured number

---

# Limits and questions
