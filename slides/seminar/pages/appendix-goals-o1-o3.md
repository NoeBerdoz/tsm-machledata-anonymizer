---
eyebrow: Appendix for readers
---

# SMART goals in full, O1 and O2

<div class="appx cols goals-appx">
<div>

### O1 Protection

The quantized student (v3) keeps at least 95 % of the fine-tuned teacher's (v1) recall, on T1 and on T2-final, each set separately. Swiss structured identifiers, caught by the regex rules and the model together, reach at least 99 % recall.

No entity type may fall below the recall that the best baseline reaches on that type on T2-dev. This is the per-type floor.

The student must beat GLiNER2-PII as published: a higher micro recall on T2-final, at equal or better character precision. It must also beat a control student with the same architecture, the same gold data and the same training budget, trained on the gold labels only.

We report structured identifiers and free-text entities separately. With no threshold, we also report recall and character precision on the out-of-distribution sets SPY, TAB, GraSCCo_PHI and BigCode PII.

</div>
<div>

### O2 Utility

We run 20 scripted tasks through our app, once with pseudonymization and once without, with the same OpenAI model and the same settings. Each task has an oracle fixed in advance, such as an exact value, expected JSON fields or a label.

Paired utility is the number of tasks solved in both runs, divided by the number solved without pseudonymization. It must be at least 90 %.

The replacement is a placeholder such as `<PERSON_1>` (issue #17). So the gap between the two runs also shows what placeholders cost.

We also measure the student's character precision on T2-final. Its threshold is the character precision that GLiNER2-PII reaches on T2-dev.

O1 and O2 pull in opposite directions. Both are evaluated at the final talk, around mid-December 2026.

</div>
</div>

<style>
.goals-appx {
  font-size: 17px;
  line-height: 1.42;
}
</style>

<!--
Appendix for readers, not presented. The source is docs/smart-goals.md on main.
-->

---
eyebrow: Appendix for readers
---

# SMART goals in full, O3, and the rules fixed today

<div class="appx cols goals-appx">
<div>

### O3 Compression

The delivered student is at least 12 times smaller than the fp32 teacher, and at least 4 times faster on a laptop CPU.

Size counts every file needed to run the model, weights and tokenizer included. Counted this way, the teacher measures 1,244 MB, so 12 times smaller is about 104 MB.

Its p95 latency, the time that 95 of 100 calls stay under, is at most a quarter of the fp32 teacher's. We measure it on one reference laptop CPU, with a fixed benchmark protocol: the same texts, length counted in words, fixed runtime and thread settings, a warm-up and a fixed number of runs.

We publish a compression curve with at least 3 points (fp32, int8, distilled int8), and 5 with the options (pruned vocabulary, int4). Each point has its recall, size and latency. O3 is evaluated at the final talk.

</div>
<div>

### Fixed today, and set later by a fixed rule

The rules are fixed today. The values that depend on data are computed on T2-dev, our development set, which is in progress.

| Goal | Fixed today | Set later, by a rule |
|---|---|---|
| O1 | 95 % of the teacher's recall, Swiss IDs 99 %, beats GLiNER2-PII | Per-type floor: the best baseline's recall per type |
| O2 | Paired utility of at least 90 % | Character precision: GLiNER2-PII's on T2-dev |
| O3 | 12 times smaller, p95 at most a quarter of the teacher's, 3 curve points | The reference CPU and the benchmark protocol |
| O4 | 100 % exact restoration, every bad replacement flagged, no silent failure | Leak budget: half of GLiNER2-PII's leaks, rounded down |
| O5 | Refusal and publication shown in MLflow, the app installs the model, one alert, 7 December 2026 | Alert window and threshold on the pseudonymization time |

</div>
</div>

<style>
.goals-appx {
  font-size: 17px;
  line-height: 1.42;
}
.goals-appx table {
  margin-top: 14px;
  width: 100%;
  border-collapse: collapse;
  font-size: 16px;
  line-height: 1.32;
}
.goals-appx th {
  font-family: var(--mono);
  font-size: 13px;
  font-weight: 400;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--muted-2);
  text-align: left;
  padding: 0 10px 6px 0;
  border-bottom: 1px solid var(--ink);
}
.goals-appx td {
  vertical-align: top;
  padding: 7px 10px 7px 0;
  border-bottom: 1px solid var(--hair);
}
.goals-appx td:first-child {
  font-family: var(--mono);
}
</style>

<!--
Appendix for readers, not presented. The source is docs/smart-goals.md on main, and docs/baselines.md for the measured 1,244 MB.
-->
