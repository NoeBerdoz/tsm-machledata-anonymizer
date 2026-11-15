---
eyebrow: Appendix for readers
---

# O4 asks that our app adds no leak of its own

<div class="appx cols goal-appx">
<div>

### O4 End-to-end protection in our app

<p class="goal-s">By the final talk, with 100 planted values in prompts and files, our app adds <span class="figure-num">0</span> leaks. It restores <span class="figure-num">100 %</span> of intact placeholders, flags every listed bad replacement, and never fails silently.</p>

### How we measure it

In test runs, we capture everything that leaves the laptop, the request to our backend and the Sentry events, and the payload sent to OpenAI. We trace each planted value and each detected span into them. A value the detector missed counts in O1. A detected value found in any capture is an app leak. Restored exactly means the stored value: the detected text with its spaces normalized.

### Reported, with no threshold

All leaks, detector misses included, for the student and for <span class="n">GLiNER2-PII</span>.

</div>
<div>

### Why these numbers

<div class="why-row"><span class="k">0, 100 %</span><p>Software checks on 100 fixed values. A found value is masked or not. A placeholder comes back exactly or not. <span class="src">docs/smart-goals.md</span></p></div>
<div class="why-row"><span class="k">O4 vs O1</span><p>O1 counts the detector's misses. O4 finds what the app adds: file extraction, masking, restoration, failures.</p></div>

### Why we can reach it

Our tests already cover masking, repeated values and restoration. The path to the cloud still needs testing. <span class="src">tests/test_engine.py, tests/test_app.py</span>

### Outside the guarantee

If OpenAI swaps one valid placeholder for another, such as `<PERSON_2>` for `<PERSON_1>`, the app cannot see it. The list of bad replacements is written before testing.

</div>
</div>

<style>
.goal-appx {
  font-size: 18px;
  line-height: 1.4;
}
.goal-appx .goal-s {
  font-size: 21px;
  line-height: 1.36;
}
.goal-appx p,
.goal-appx li {
  text-wrap: pretty;
}
.goal-appx .why-row {
  display: grid;
  grid-template-columns: 100px 1fr;
  column-gap: 12px;
  align-items: start;
}
.goal-appx .why-row + .why-row {
  margin-top: 10px;
}
.goal-appx .k {
  font-weight: 500;
  font-variant-numeric: lining-nums tabular-nums;
}
.goal-appx .n {
  white-space: nowrap;
}
.goal-appx .src {
  font-family: var(--mono);
  font-size: 14px;
  color: var(--muted-2);
  white-space: nowrap;
}
</style>

<!--
Appendix for readers, not presented.

If asked: do 99 % and zero added leaks prove the app is safe? No. They are results on fixed test sets, partly synthetic. Unseen inputs can still leak.
-->
