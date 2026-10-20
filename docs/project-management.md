# Project management

The teachers want to see who did what, and when. We keep all our planning in one GitHub Project linked to this repository. We update it while we work, not just before the talks.

## The board

The Board view is our kanban. It has five columns:

| Column | Meaning |
|---|---|
| Backlog | Known work, not planned yet |
| Ready | Planned for the current milestone, with an owner and a date |
| In progress | Someone is working on it now |
| In review | A pull request is open |
| Done | Merged, or closed with a note |

Keep "In progress" short: at most two cards per person.

## The schedule

The Roadmap view is our Gantt chart. Each issue has a start date and a target date (two custom fields). The Roadmap draws them as bars, grouped by milestone. We take a screenshot of it for each talk.

## Issues

- Every issue has exactly one owner (the assignee) and a target date.
- Every issue belongs to one milestone: `v0`, `v1`, `v2`, `v3` or `final`.
- Labels give the area: `data`, `model`, `hooks`, `pipeline`, `bench`, `report`, `slides`.
- An issue should take about two days of work at most. If it is bigger, split it.

## Milestones

| Milestone | Content | Due |
|---|---|---|
| v0 | Baselines, T2 built and split, thresholds and benchmark protocol frozen, seminar talk | 2026-11-16 |
| v1 | Fine-tuned teacher | End of November 2026 |
| v2 | Distilled student and gold-label control | Around 2026-12-10 |
| v3 | Quantized student | Around 2026-12-10 |
| final | Final talk and report | Mid-December 2026, to confirm |

## Contribution flow

1. Pick an issue in "Ready" that is assigned to you. Move it to "In progress".
2. Create a branch from `main`. Name it after the issue, for example `12-swiss-iban-regex`.
3. Commit in small steps. Each message says what changed.
4. Open a pull request that links the issue (write `Closes #12` in it).
5. Another team member reviews it. One approval is enough to merge.
6. Squash-merge into `main`. The issue closes and moves to "Done".

Nobody pushes directly to `main`. Data and models never go into git. When the code arrives, we will add automatic checks (tests and lint) to every pull request.
