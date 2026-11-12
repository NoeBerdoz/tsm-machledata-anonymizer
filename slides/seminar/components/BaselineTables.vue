<script setup lang="ts">
// The appendix tables behind slide 11, from data/baseline.ts.
//   view="full"     both T1 candidate samples (1,000 texts each) and the Swiss set (781 values)
//   view="subset"   the app's engine against the others on the same 200 texts per set
//   view="latency"  time per call on the development machine
import { detectors, subset200, latency } from '../data/baseline'

defineProps<{ view: 'full' | 'subset' | 'latency' }>()

// as the docs print them: 100 %, 99.96 %, 92.9 %
const pct = (v: number) => (v === 100 ? '100' : Math.abs(v * 10 - Math.round(v * 10)) > 1e-9 ? v.toFixed(2) : v.toFixed(1)) + ' %'
const p1 = (v: number) => v.toFixed(1) + ' %'
const mb = (v: number | null) => (v == null ? 'rules only' : v.toLocaleString('en-US') + ' MB')
</script>

<template>
  <div class="bt">
    <template v-if="view === 'full'">
      <table class="tbl full">
        <thead>
          <tr class="grp">
            <th />
            <th colspan="2">OpenPII-1M, 1,000 texts</th>
            <th colspan="2">open-pii-500k, 1,000 texts</th>
            <th colspan="4">Swiss set, recall on 781 values</th>
            <th />
          </tr>
          <tr>
            <th>Detector</th>
            <th>Recall</th>
            <th>Char. prec.</th>
            <th>Recall</th>
            <th>Char. prec.</th>
            <th>AVS (168)</th>
            <th>IBAN (214)</th>
            <th>Phone (399)</th>
            <th>All three</th>
            <th class="r">Size</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="d in detectors" :key="d.key" :class="{ combo: d.combo }">
            <td class="name">{{ d.name }}</td>
            <td>{{ p1(d.openpii.recall) }}</td>
            <td>{{ p1(d.openpii.charPrecision) }}</td>
            <td>{{ p1(d.openpii500k.recall) }}</td>
            <td>{{ pct(d.openpii500k.charPrecision) }}</td>
            <td>{{ pct(d.swiss.avs) }}</td>
            <td>{{ pct(d.swiss.iban) }}</td>
            <td>{{ pct(d.swiss.phone) }}</td>
            <td class="strong">{{ p1(d.swiss.all) }}</td>
            <td class="r">{{ mb(d.sizeMB) }}</td>
          </tr>
        </tbody>
      </table>
    </template>

    <template v-else-if="view === 'subset'">
        <table class="tbl">
          <thead>
            <tr class="grp">
              <th />
              <th colspan="2">OpenPII-1M</th>
              <th colspan="2">open-pii-500k</th>
              <th>Swiss</th>
              <th />
            </tr>
            <tr>
              <th>Same 200 texts per set</th>
              <th>Recall</th>
              <th>Char. prec.</th>
              <th>Recall</th>
              <th>Char. prec.</th>
              <th>251 values</th>
              <th class="r">Size</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in subset200" :key="r.name" :class="{ engine: r.name.startsWith('App engine') }">
              <td class="name">{{ r.name }}</td>
              <td>{{ p1(r.openpii[0]) }}</td>
              <td>{{ p1(r.openpii[1]) }}</td>
              <td>{{ p1(r.openpii500k[0]) }}</td>
              <td>{{ p1(r.openpii500k[1]) }}</td>
              <td>{{ p1(r.swiss251) }}</td>
              <td class="r">{{ r.size }}</td>
            </tr>
          </tbody>
        </table>
    </template>

    <template v-else>
        <table class="tbl lat">
          <thead>
            <tr class="grp">
              <th colspan="4">Apple M5 Max, 30 texts, CPU with 4 threads unless stated</th>
            </tr>
            <tr>
              <th>Detector</th>
              <th class="r">p50</th>
              <th class="r">p95</th>
              <th class="r">p95 per 100 words</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="l in latency" :key="l.name" :class="{ engine: l.name.startsWith('App engine') }">
              <td class="name">{{ l.name }}</td>
              <td class="r">{{ l.p50 }}</td>
              <td class="r">{{ l.p95 }}</td>
              <td class="r">{{ l.per100 }}</td>
            </tr>
          </tbody>
        </table>
    </template>
  </div>
</template>

<style scoped>
.bt {
  margin-top: 26px;
  width: 1136px;
}

.lat {
  width: 760px;
}
.tbl {
  width: 100%;
  border-collapse: collapse;
  font-size: 16px;
  line-height: 1.3;
  font-variant-numeric: lining-nums tabular-nums;
}
th {
  font-family: var(--mono);
  font-size: 13px;
  font-weight: 400;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted-2);
  text-align: left;
  padding: 0 8px 6px 0;
  border-bottom: 1px solid var(--hair);
  white-space: nowrap;
}
.grp th {
  color: var(--ink);
  letter-spacing: 0.12em;
  padding-top: 0;
}
.grp th:not(:empty) {
  border-bottom: 1px solid var(--ink);
}
.grp th:empty {
  border-bottom: none;
}
td {
  padding: 8px 8px 8px 0;
  border-bottom: 1px solid rgba(22, 22, 22, 0.07);
  white-space: nowrap;
}
.name {
  color: var(--ink);
}
.r {
  text-align: right;
}
.strong {
  font-weight: 500;
}
tr.engine td {
  border-top: 1px solid var(--ink);
}
</style>
