# Project management

The teachers want to see who did what, and when. We keep all our planning in one GitHub Project linked to this repository: https://github.com/users/NoeBerdoz/projects/2. We update it while we work, not just before the talks.

## How it fits together

- The **Project** is the board. It shows cards, but it stores almost nothing itself.
- Each **card** is an **issue** of this repository. We use issues for everything, including work without code, such as choosing a dataset or preparing the slides.
- A **pull request** is linked to its issue. When it is merged, the issue closes and the card moves to "Done" on its own.

```
Issue #4 ("Ready", target date set)
  └─ you assign yourself, create the branch 4-public-datasets → "In progress"
       └─ pull request with "Closes #4" → "In review", a teammate reads it
            └─ squash-merge → issue closed → "Done"
```

## The views

The Project has three views:

| View | What it shows |
|---|---|
| Board | Our kanban, one column per status |
| Roadmap | Our Gantt chart: each issue is a bar from its start date to its target date, grouped by milestone. We take a screenshot of it for each talk. |
| My tasks | Only the issues assigned to you |

The Board has five columns:

| Column | Meaning |
|---|---|
| Backlog | Known work, not planned yet |
| Ready | Planned for the current milestone, with a date. Anyone can take it. |
| In progress | Someone is working on it now |
| In review | A pull request is open |
| Done | Merged, or closed with a note |

Keep "In progress" short: at most two cards per person.

## Issues

- Create issues with the "Task" template. It asks for the goal, a "Done when" checklist that anyone can verify, the output, and the issues it depends on.
- Every issue has exactly one owner (the assignee), a start date and a target date. An issue in "Ready" may have no owner yet: whoever takes it assigns themselves.
- Every issue belongs to one milestone: `v0`, `v1`, `v2`, `v3` or `final`.
- Labels give the area: `data`, `model`, `hooks`, `pipeline`, `bench`, `report`, `slides`.
- An issue should take about two days of work at most. If it is bigger, split it.
- We only detail the current milestone. The next one is split into issues when it starts, because the results of the previous one change the plan.

## Milestones

| Milestone | Content | Due |
|---|---|---|
| v0 | Architecture, project skeleton, evaluation harness, data decisions, first baselines, first cloud training run, seminar talk | 2026-11-16 |
| v1 | Fine-tuned teacher | 2026-11-30 |
| v2 | Distilled student and gold-label control | Around 2026-12-10 |
| v3 | Quantized student | Around 2026-12-10 |
| final | Final talk and report | Mid-December 2026, to confirm |

## Contribution flow

1. Pick an issue in "Ready". Assign yourself (the "Assignees" box in the issue) and move the card to "In progress".
2. Create a branch from `main` named after the issue, for example `4-public-datasets`.
3. Commit in small steps. Each message follows [Conventional Commits](#commit-messages) and says what changed.
4. Open a pull request whose title also follows Conventional Commits, and write `Closes #4` in its description. Move the card to "In review".
5. Ask a teammate to read it. A review is welcome but not required to merge.
6. Squash-merge into `main`. The issue closes, the branch is deleted, and the card moves to "Done".

Some issues end with a decision rather than code, for example "Do we need our own test set?". Write the decision and its reason in a comment, update `docs/` if needed, then close the issue.

Data and models never go into git: they are versioned with DVC. Automatic checks (lint and tests) run on every pull request, see [development.md](development.md#checks).

## Commit messages

We follow [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/). A message starts with a type, an optional scope in parentheses, a colon, and a short description:

```
feat(hooks): replace names with placeholders before sending
fix: keep the IBAN checksum when restoring values
docs: add the dataset licences
```

| Type | Use it for |
|---|---|
| `feat` | A new feature |
| `fix` | A bug fix |
| `docs` | Documentation only, including the report and the slides |
| `test` | Adding or changing tests |
| `refactor` | A code change that neither adds a feature nor fixes a bug |
| `build` | Dependencies, the Python project, DVC setup |
| `ci` | The GitHub Actions workflows |
| `chore` | Anything else that does not touch the code |

The scope is free, but the issue labels (`data`, `model`, `hooks`, `pipeline`, `bench`) are a good choice.

We squash-merge, so the title of the pull request becomes the commit message on `main`. That is why the pull request title must follow the convention too.

## Weekly sync

Once a week, 15 minutes in front of the Board. Each of us says what they finished, what they take next, and what blocks them. We move the cards and fix the dates during the meeting.
