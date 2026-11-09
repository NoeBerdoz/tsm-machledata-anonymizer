// Baseline v0 on T2-dev. Fill in the measured values and set `placeholder: false`.
// The plot appears on the slide as soon as one baseline is not a placeholder and has both
// recall and charPrecision set (values between 0 and 1). Until then the slide shows the table only.
// sizeMeasured marks a size that is already measured, even while the rest is a placeholder.

export interface Baseline {
  name: string
  detail: string
  recall: number | null
  charPrecision: number | null
  size: string | null
  sizeMeasured: boolean
  p95: string | null
  placeholder: boolean
}

export const baselines: Baseline[] = [
  {
    name: 'Regex only',
    detail: 'Our rules for fixed formats',
    recall: null,
    charPrecision: null,
    size: null,
    sizeMeasured: false,
    p95: null,
    placeholder: true,
  },
  {
    name: 'Presidio',
    detail: 'Open-source PII toolkit',
    recall: null,
    charPrecision: null,
    size: null,
    sizeMeasured: false,
    p95: null,
    placeholder: true,
  },
  {
    name: 'GLiNER2-PII',
    detail: 'The teacher as published',
    recall: null,
    charPrecision: null,
    size: '1.23 GB',
    sizeMeasured: true,
    p95: null,
    placeholder: true,
  },
  {
    name: 'OpenAI Privacy Filter',
    detail: 'As published',
    recall: null,
    charPrecision: null,
    size: null,
    sizeMeasured: false,
    p95: null,
    placeholder: true,
  },
]
