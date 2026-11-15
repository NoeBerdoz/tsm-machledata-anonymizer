// The five SMART goals, short form for slide 11: one target figure each, in plain words.
// The full wording, the acceptance conditions and why each number holds are on the appendix
// pages, one page per goal, from docs/smart-goals.md. The targets below are fixed today. The
// limits that a fixed rule sets later are the character precision of O2 (GLiNER2-PII's on
// T2-dev, recorded before any tuning), the latency sample of O3 (30 texts from T2-dev) and the
// demonstration thresholds and alert of O5 (written in advance in params.yaml). They are on
// the last goal page of the appendix.

export interface Goal {
  id: string
  name: string
  figure: string // the target, as printed
  caption: string // reads after the figure
  more?: string // a second condition of the same goal
}

export const goals: Goal[] = [
  { id: 'O1', name: 'Protection', figure: '95 %', caption: "of the teacher's recall", more: 'Swiss IDs: 99 %' },
  { id: 'O2', name: 'Utility', figure: '90 %', caption: 'of solved app tasks still solved with placeholders' },
  { id: 'O3', name: 'Compression', figure: '8x', caption: 'smaller than the teacher', more: '1.5x faster on a laptop CPU' },
  { id: 'O4', name: 'End to end', figure: '100 %', caption: 'of intact placeholders restored exactly', more: 'No leak added by the app' },
  { id: 'O5', name: 'MLOps', figure: '7 Dec.', caption: 'the gate refuses a bad model', more: 'Alert when too slow' },
]
