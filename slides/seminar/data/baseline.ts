// The first baselines: off-the-shelf detectors, before any training, on the two T1 candidate
// samples and on our Swiss set. T2 is in progress, so nothing here is on T2-dev yet.
// Sources on main: docs/baselines.md, docs/swiss-identifiers.md and results/summary.md
// (PRs #28 and #34). Everything was measured on a development machine (Apple M5 Max), not on
// the reference laptop. Percentages are strict recall and character precision.

export interface Detector {
  key: string
  name: string // as printed on the slides
  combo?: boolean // the regex and a model together: a span is masked if either finds it
  // 1,000 texts each, 250 per language (FR, DE, IT, EN), seed 42
  openpii: { recall: number; charPrecision: number } // ai4privacy OpenPII-1M, validation
  openpii500k: { recall: number; charPrecision: number } // ai4privacy open-pii-masking-500k, validation
  // Swiss set: 634 rows, 781 fake Swiss values; recall on the three Swiss types
  swiss: { avs: number; iban: number; phone: number; all: number }
  sizeMB: number | null // every file needed to run it; null for the rules alone
}

export const detectors: Detector[] = [
  {
    key: 'regex',
    name: 'Regex rules',
    openpii: { recall: 8.0, charPrecision: 99.4 },
    openpii500k: { recall: 6.3, charPrecision: 99.96 },
    swiss: { avs: 92.9, iban: 88.8, phone: 100, all: 95.4 },
    sizeMB: null,
  },
  {
    key: 'presidio',
    name: 'Presidio',
    openpii: { recall: 54.3, charPrecision: 85.7 },
    openpii500k: { recall: 63.5, charPrecision: 89.0 },
    swiss: { avs: 7.7, iban: 99.1, phone: 100, all: 79.9 },
    sizeMB: 2357,
  },
  {
    key: 'gliner2',
    name: 'GLiNER2-PII',
    openpii: { recall: 80.7, charPrecision: 98.2 },
    openpii500k: { recall: 81.8, charPrecision: 96.7 },
    swiss: { avs: 75.6, iban: 79.9, phone: 91.2, all: 84.8 },
    sizeMB: 1244,
  },
  {
    key: 'privacy-filter',
    name: 'OpenAI Privacy Filter',
    openpii: { recall: 78.8, charPrecision: 97.3 },
    openpii500k: { recall: 69.8, charPrecision: 96.6 },
    swiss: { avs: 99.4, iban: 79.4, phone: 96.7, all: 92.6 },
    sizeMB: 2827,
  },
  {
    key: 'regex+gliner2',
    name: 'Regex + GLiNER2-PII',
    combo: true,
    openpii: { recall: 80.7, charPrecision: 98.2 },
    openpii500k: { recall: 81.8, charPrecision: 96.7 },
    swiss: { avs: 97.6, iban: 99.1, phone: 100, all: 99.2 },
    sizeMB: 1244,
  },
  {
    key: 'regex+privacy-filter',
    name: 'Regex + Privacy Filter',
    combo: true,
    openpii: { recall: 79.0, charPrecision: 97.3 },
    openpii500k: { recall: 70.0, charPrecision: 96.6 },
    swiss: { avs: 100, iban: 98.1, phone: 100, all: 99.5 },
    sizeMB: 2827,
  },
]

// GLiNER2-PII on OpenPII-1M without the five types its model card has no label for
// (title, age, gender, sex, time)
export const gliner2KnownTypes = 92

// The O1 goal on Swiss structured identifiers, regex and model together
export const swissGoal = 99

// The app's engine today (qwen3:4b through Ollama, plus its own rules), scored on 200 texts per
// set (50 per language, fixed seed) because a 4B model is slow. Every other detector ran on the
// same 200 texts, so these rows compare only with each other, never with the 1,000-text rows.
export interface Row200 {
  name: string
  openpii: [number, number] // recall, character precision
  openpii500k: [number, number]
  swiss251: number // recall on the 251 Swiss values of the 200-row Swiss sample
  size: string
}
export const subset200: Row200[] = [
  { name: 'Regex rules', openpii: [7.5, 100.0], openpii500k: [6.2, 99.8], swiss251: 96.8, size: 'rules only' },
  { name: 'Presidio', openpii: [55.0, 87.0], openpii500k: [65.9, 89.7], swiss251: 77.3, size: '2,357 MB' },
  { name: 'GLiNER2-PII', openpii: [81.9, 98.5], openpii500k: [82.6, 98.1], swiss251: 84.1, size: '1,244 MB' },
  { name: 'OpenAI Privacy Filter', openpii: [79.4, 97.5], openpii500k: [73.2, 97.1], swiss251: 94.4, size: '2,827 MB' },
  { name: 'Regex + GLiNER2-PII', openpii: [82.0, 98.5], openpii500k: [82.6, 98.1], swiss251: 99.2, size: '1,244 MB' },
  { name: 'Regex + Privacy Filter', openpii: [79.5, 97.5], openpii500k: [73.4, 97.1], swiss251: 100.0, size: '2,827 MB' },
  { name: 'App engine, qwen3:4b + rules', openpii: [62.4, 87.4], openpii500k: [63.5, 92.3], swiss251: 100.0, size: '2,497 MB' },
]

// Latency on an Apple M5 Max, CPU, 4 threads: a temporary sample of 30 texts of the OpenPII-1M
// 200-text subset, 5 warm-up calls, then 10 runs per text (300 timed calls). The official O3
// numbers come from the reference laptop.
export interface Latency {
  name: string
  p50: string
  p95: string
  per100: string // p95 per 100 words
}
export const latency: Latency[] = [
  { name: 'Regex rules', p50: '0.01 ms', p95: '0.04 ms', per100: '0.04 ms' },
  { name: 'Presidio', p50: '3 ms', p95: '10 ms', per100: '13 ms' },
  { name: 'GLiNER2-PII', p50: '77 ms', p95: '138 ms', per100: '426 ms' },
  { name: 'OpenAI Privacy Filter', p50: '137 ms', p95: '360 ms', per100: '512 ms' },
  { name: 'Regex + GLiNER2-PII', p50: '76 ms', p95: '137 ms', per100: '425 ms' },
  { name: 'Regex + Privacy Filter', p50: '131 ms', p95: '356 ms', per100: '502 ms' },
  { name: 'App engine, on the CPU', p50: '2,962 ms', p95: '6,615 ms', per100: '15,359 ms' },
  { name: 'App engine, on the GPU as in the app', p50: '621 ms', p95: '941 ms', per100: '2,740 ms' },
]
