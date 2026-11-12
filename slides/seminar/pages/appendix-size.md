---
eyebrow: Appendix for readers
---

# Size estimates and their assumptions

<div class="appx">

<div class="path-table">
  <div class="caption">Step</div><div class="caption">What changes</div><div class="caption num">Parameters</div><div class="caption num">Size</div><div class="caption num">Smaller</div>
  <div>The teacher, float32</div><div>Every file: weights, configs, tokenizer</div><div class="num">307M</div><div class="num">1,244 MB, measured</div><div class="num">1x</div>
  <div>int8, pruned vocabulary</div><div>12 layers, the 77,347 tokens of our four languages</div><div class="num">174M</div><div class="num">about 179 MB</div><div class="num">6.9x</div>
  <div>Student, 6 layers</div><div>Pruned vocabulary, int8</div><div class="num">132M</div><div class="num">about 137 MB</div><div class="num">9.1x</div>
  <div>Then int4 embeddings</div><div>Same student, word embeddings at half a byte</div><div class="num">132M</div><div class="num">about 107 MB</div><div class="num">11.6x</div>
  <div>Or rare tokens dropped</div><div>Same student, only the 42,073 tokens seen 10 times or more</div><div class="num">105M</div><div class="num">about 108 MB</div><div class="num">11.6x</div>
  <div>Or both</div><div>Same student, both steps</div><div class="num">105M</div><div class="num">about 91 MB</div><div class="num">13.6x</div>
  <div>Current goal, O3</div><div>1,244 MB divided by 12</div><div class="num"></div><div class="num">about 104 MB</div><div class="num">12x</div>
</div>

<div class="cols size-assume">
<div>

- Estimates at 1 byte per parameter in int8 and half a byte in int4. Only the teacher is measured.
- The GLiNER2 heads (29.5M parameters) are kept.
- The tokenizer counts, as in O3: 16 MB for the teacher. We assume that a pruned tokenizer shrinks with its vocabulary.

</div>
<div>

- The 103,718 French, German, Italian and English validation texts of OpenPII-1M use 77,347 of the 250,112 tokens. This is a lower bound: a real pruning also keeps the tokens of the training texts.
- The 42,073 tokens seen at least 10 times cover 98.8 % of the text. A word that loses its token is cut into smaller tokens, so recall must be measured after any pruning.

</div>
</div>

</div>

<style>
.path-table {
  display: grid;
  grid-template-columns: 236px 1fr 104px 176px 72px;
  column-gap: 20px;
  font-size: 16px;
  line-height: 1.3;
}
.path-table > div {
  padding: 6px 0;
  border-bottom: 1px solid var(--hair);
}
.path-table > .caption {
  font-family: var(--mono);
  font-size: var(--fs-eyebrow);
  letter-spacing: 0.16em;
  text-transform: uppercase;
  border-bottom-color: var(--ink);
}
.path-table .num {
  text-align: right;
  font-variant-numeric: lining-nums tabular-nums;
}
.size-assume {
  margin-top: 18px;
  font-size: 16px;
  line-height: 1.38;
}
</style>

<!--
Appendix for readers, not presented. Source: docs/baselines.md, "The vocabulary of our four languages".
-->
