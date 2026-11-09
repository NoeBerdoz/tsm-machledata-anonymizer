// SMART goals, short form for the presented slide. The full wording and every
// acceptance condition are on the appendix slides, from docs/smart-goals.md.

export interface Goal {
  id: string
  name: string
  key: string
  when: string
}

export const goals: Goal[] = [
  { id: 'O1', name: 'Protection', key: '95 % of teacher recall, Swiss IDs 99 %', when: 'mid-Dec.' },
  { id: 'O2', name: 'Utility', key: '90 % paired utility', when: 'mid-Dec.' },
  { id: 'O3', name: 'Compression', key: '12 times smaller, 4 times faster', when: 'mid-Dec.' },
  { id: 'O4', name: 'End to end', key: 'leaks within budget, exact restoration', when: 'mid-Dec.' },
  { id: 'O5', name: 'MLOps', key: 'gate, publication, alert', when: '7 Dec.' },
]
