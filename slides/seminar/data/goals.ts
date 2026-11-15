// The five SMART goals, short form for slide 11: one target figure each, in plain words.
// Every big figure is a measure, never a date. The figure and its caption read as one phrase
// the speaker can say aloud: the target, what it counts, and what it is compared with. The
// dates are the T of SMART: mid-December for O1 to O4 is in the lede, and 7 December is in
// the second line of O5, so each date shows once. A "|" marks where a line may break: the
// phrases between the marks stay whole on the slide.
// The full wording, the acceptance conditions and why each number holds are on the appendix
// pages, one page per goal, from docs/smart-goals.md. The targets below are fixed today. The
// limits that a fixed rule sets later are the character precision of O2 (GLiNER2-PII's on
// T2-dev, recorded before any tuning), the latency sample of O3 (30 texts from T2-dev) and the
// demonstration thresholds and alert of O5 (written in advance in params.yaml). They are on
// the last goal page of the appendix.

export interface Goal {
  id: string
  name: string
  figure: string // the target, as printed: a measure, never a date
  caption: string // reads after the figure: what it counts, and what it is compared with
  more?: string // a second condition of the same goal; for O5, its date and its alert
}

export const goals: Goal[] = [
  { id: 'O1', name: 'Protection', figure: '95 %', caption: "of the teacher's recall", more: 'Swiss IDs: 99 %, | rules and model' },
  { id: 'O2', name: 'Utility', figure: '90 %', caption: 'of solved test prompts | still work | with placeholders' },
  { id: 'O3', name: 'Compression', figure: '8x', caption: 'smaller than | the teacher', more: '1.5x faster | on the i5 laptop' },
  { id: 'O4', name: 'End to end', figure: '100 %', caption: 'of intact placeholders | restored exactly', more: 'No leak added | by the app' },
  { id: 'O5', name: 'MLOps', figure: '0', caption: 'models reach the app | without passing | the quality gate', more: 'Shown by 7 Dec., | with one speed alert' },
]
