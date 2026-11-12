// The five SMART goals, short form for slide 10: one target figure each, in plain words.
// The full wording and every acceptance condition are on the appendix pages, from
// docs/smart-goals.md. The targets below are fixed today. The limits that a fixed rule
// computes on T2-dev (per-type floor, character precision, leak budget, alert line) are on
// the appendix pages.

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
  { id: 'O3', name: 'Compression', figure: '12x', caption: 'smaller than the teacher', more: '4x faster on a laptop CPU' },
  { id: 'O4', name: 'End to end', figure: '100 %', caption: 'of replacements restored exactly', more: 'No silent failure' },
  { id: 'O5', name: 'MLOps', figure: '7 Dec.', caption: 'the gate refuses a bad model', more: 'Alert when too slow' },
]
