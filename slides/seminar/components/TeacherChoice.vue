<script setup lang="ts">
// Appendix: why our teacher is GLiNER2-PII and not OpenAI's Privacy Filter. Both were measured
// as published, before our training: on the T1 samples (1,000 texts each; T1 is OpenPII-1M
// validation) and on our Swiss set (781 values in 634 rows).
// Counts: results/results.csv and results/recall_per_type.csv on main, also in
// docs/baselines.md and docs/swiss-identifiers.md. Types and licences: the model cards.
// In each row, the better value prints in ink at the medium weight and the other in muted;
// when both are equal, neither is marked.
const pct = (found: number, all: number) => Math.round((100 * found) / all)
const pct1 = (found: number, all: number) => ((100 * found) / all).toFixed(1)

type Row = { label: string; a: string; b: string; better?: 'a' | 'b' }
const rows: Row[] = [
  // entities found, of 7,275
  { label: 'Recall on T1, OpenPII-1M', a: `${pct(5867, 7275)} %`, b: `${pct(5733, 7275)} %`, better: 'a' },
  // of 2,324
  { label: 'Recall on open-pii-500k', a: `${pct(1901, 2324)} %`, b: `${pct(1622, 2324)} %`, better: 'a' },
  // given names of 858, cities of 506, streets of 339
  {
    label: 'Given names, cities, streets, on T1',
    a: `${pct(818, 858)}, ${pct(445, 506)}, ${pct(324, 339)} %`,
    b: `${pct(727, 858)}, ${pct(343, 506)}, ${pct(272, 339)} %`,
    better: 'a',
  },
  // dates of 871, social security numbers of 168
  { label: 'Dates, social security numbers, on T1', a: `${pct(753, 871)}, ${pct(113, 168)} %`, b: `${pct(837, 871)}, ${pct(162, 168)} %`, better: 'b' },
  // AVS, IBAN and phone values found by the regex or the model, of 781
  { label: 'Swiss AVS, IBAN, phone, with our regex', a: `${pct1(775, 781)} %`, b: `${pct1(777, 781)} %`, better: 'b' },
  { label: 'Entity types it knows', a: '42', b: '8', better: 'a' },
  // every file needed to run it (size_mb); smaller is better
  { label: 'Size on disk', a: '1,244 MB', b: '2,827 MB', better: 'a' },
  // latency_p95_ms: 138.29 and 360.17, 300 calls on 30 texts; faster is better
  { label: 'p95 time per text, development Mac, CPU', a: '138 ms', b: '360 ms', better: 'a' },
  { label: 'Licence', a: 'Apache 2.0', b: 'Apache 2.0' },
]
const mark = (r: Row, side: 'a' | 'b') => (!r.better ? '' : r.better === side ? 'better' : 'worse')
</script>

<template>
  <table class="choice">
    <colgroup>
      <col style="width: 440px" />
      <col style="width: 240px" />
      <col style="width: 240px" />
    </colgroup>
    <thead>
      <tr class="grp">
        <th />
        <th colspan="2">Both measured as published, before our training</th>
      </tr>
      <tr class="who">
        <th />
        <th><span class="model">GLiNER2-PII</span>, Fastino</th>
        <th><span class="model">Privacy Filter</span>, OpenAI</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="r in rows" :key="r.label">
        <td class="crit">{{ r.label }}</td>
        <td :class="mark(r, 'a')">{{ r.a }}</td>
        <td :class="mark(r, 'b')">{{ r.b }}</td>
      </tr>
    </tbody>
  </table>
</template>

<style scoped>
.choice {
  margin-top: 24px;
  width: 920px;
  table-layout: fixed;
  border-collapse: collapse;
  font-size: var(--fs-label);
  line-height: 1.3;
  font-variant-numeric: lining-nums tabular-nums;
  color: var(--ink);
}
/* the rules come from the cells only, not from the base style of a table row */
.choice tr {
  border-bottom: none;
}
th {
  text-align: left;
  font-weight: 400;
  padding: 0 16px 6px 0;
  white-space: nowrap;
}
.grp th {
  font-family: var(--mono);
  font-size: var(--fs-eyebrow);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--ink);
}
.grp th:not(:empty) {
  border-bottom: 1px solid var(--ink);
}
.who th {
  padding-top: 8px;
  font-family: var(--sans);
  color: var(--muted);
  border-bottom: 1px solid var(--hair);
}
.who .model {
  font-weight: 500;
  color: var(--ink);
}
td {
  padding: 5px 16px 5px 0;
  border-bottom: 1px solid var(--hair);
  white-space: nowrap;
}
td.better {
  font-weight: 500;
}
td.worse {
  color: var(--muted);
}
</style>
