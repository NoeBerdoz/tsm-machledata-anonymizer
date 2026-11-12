# How our slides look

A Swiss product: paper, black ink, neutral greys and one red, like a station clock or a Swiss poster. Each slide makes one claim. The figure under the claim is a real thing drawn crisply, such as a chat window, a table, a chart or a small card. It is never an illustration.

## Colours

| Name | Value | Use it for |
| --- | --- | --- |
| paper | `#f6f5f1` | the page |
| card | `#ffffff` | windows and cards that sit on the page |
| ink | `#161616` | text, the paper-cut art, placeholder chips |
| muted | `#4a4a45` | the lede and secondary text |
| muted-2 | `#666660` | labels, eyebrows, sources |
| hair | ink at 16 % | rules, borders, empty bars |
| ui | `#efeeea` | quiet interface fills: a chat bubble, a status line |
| charcoal | `#232323` | the dark panel of a remote service, such as the cloud AI |
| red | `#da291c` | the signal, see below |

There is no other colour: no blue, no green, no navy. Do not add one.

## What each colour means

- **Red is the signal.** It marks only:
  - the one emphasis of a headline;
  - a real personal value, such as Marie Dupont;
  - a refusal, a failed goal or an alert;
  - the "you are here" marker, in the footer rail and in a step trail.
- **Everything else is ink and greys.**
- **A placeholder,** such as `<PERSON_1>`, is never red. It is an ink chip with light mono text, like a redaction.
- **A value that passes** is ink with a check mark.
- **Red never decorates.**
- **Each slide shows one red idea.** When the headline's red competes with the slide's red idea, drop the headline's emphasis. Slide 2 does this, so the eye lands on the red personal values.

On the charcoal panel, the red is lifted to `#f2584b` so that type stays readable, and a placeholder chip keeps a light edge.

## Three type voices

The fonts are Instrument Sans and Fragment Mono.

- **The claim headline:** Instrument Sans at weight 500, never bold. Its one emphasis prints in red, upright, never in italic.
- **The lede, prose and interface text:** Instrument Sans at weight 400.
- **Figures** (48%, big numbers, table values): Instrument Sans with tabular digits, so counting digits never jump. Big numbers are set a little narrow (width 84 %, the `--fig-stretch` token), in the Swiss poster way.
- **Fragment Mono:** eyebrows, labels and identifiers, such as `<PERSON_1>`, a hash or a version. It has one weight, so never set it bold.

Sizes on the 1280 x 720 page: headline 44, lede 24, text inside figures 18 to 22, eyebrows 13, sources 14. Text that explains is never smaller than 18 px. Only eyebrows and sources may be smaller.

The font files and their licences (SIL Open Font License) are in `fonts/`.

## Writing

Nobody in the room is a native English speaker: not the four of us, and not the audience. So every word on a slide and in the notes is simple English.

- **Simple English.**
  - Short sentences: about 15 words at most, one idea each.
  - Common words: "use", not "utilize"; "about", not "approximately"; "check", not "validate".
  - No idioms, and no phrasal verb when a plain verb exists.
  - A technical term only when the idea needs it, such as recall or quantization. Explain it once in plain words, on the slide, the first time it appears.
  - Numbers that are easy to say aloud.
  - The test: a listener with B1 English follows each sentence the first time they hear it.
- **About 30 words per click state,** not counting the figure's own numbers. When you add a label, remove another.
- **Explaining text is 18 px or more.** Only eyebrows and sources may be smaller.
- **Keyboard characters only,** in slide text, eyebrows and notes: no em dash, no middle dot, no curly quotes, no typed arrows and no typed math symbols. Use a slash or spacing as a separator, and "about" for an approximation. Math goes through `<Tex>`.

## Writing a slide

Each slide is one file in `pages/`, such as `pages/06-soft-labels.md`, and `slides.md` lists it with a `src:` line after the cover.

```md
---
part: 2
eyebrow: Distillation
source: 'Hinton, Vinyals and Dean (2015)'
clicks: 2
---

# The student copies *the teacher*

One sentence under the headline. A paragraph written right under the headline becomes the lede.

<SoftLabels />

<!--
Target time 0:40. Speaker: to assign.

What to say before the first click.
[click] What to say on the first click.
-->
```

- `part` is the part of the talk (see below). The masthead, the hairline, the rail of the parts and the page number then come by themselves. `eyebrow` adds a topic after the part name. `source` prints small at the bottom left.
- The headline is a claim, not a topic: "The pipeline decides *what reaches users*", not "Pipeline". It has exactly one emphasis, written between stars, and makes no absolute promise.
- Every symbol and abbreviation is named on the slide, because nobody can read the notes during the talk.

## The five parts

The rail at the bottom right shows where we are in the talk.

| Part | Slides |
| --- | --- |
| 1 Problem | 2 the hook, 3 the laptop |
| 2 Model | 4 the teacher, 5 the dictionary, 6 soft labels, 7 the loss |
| 3 Quantization | 8 int8, 9 the size path, then PTQ and QAT |
| 4 Evaluation | 10 how we count a leak, 11 the SMART goals |
| 5 Plan | 12 the pipeline, 13 the roadmap |

The cover has no rail. The closing lights the whole rail. The appendix pages have no rail.

## Layouts

- **The default slide** needs no layout line: masthead, claim, lede, body, footer rail.
- **`layout: cover`**: the title block, with the Poya herd along the foot of the page.
- **`layout: closing`**: one large line in the middle of the page, with the whole rail lit.

## Building blocks

| Block | Use it for | Example |
| --- | --- | --- |
| `Callout` | the one thing to remember | `<Callout tag="In short">This time, the AI only saw placeholders.</Callout>`, with `tone="alert"` for a danger |
| `BigStat` | one figure and its caption | `<BigStat :value="48" suffix="%" side>of employees report ...</BigStat>` |
| `StepTrail` | a process read left to right, the current step lit | `<StepTrail :steps="['Version', 'Train', 'Gate']" :current="1" />`, with `size="lg"` when the trail is the figure |
| `Window` | the window of an app | `<Window title="AI chat">...</Window>`, with `tone="dark"` for a remote service and `icon="cloud"` in place of the three dots when the service is not an app |
| `Bar` | a measure against a goal line | `<Bar :value="88" :max="100" :goal="95" tone="fail" display="88 %" />` |

The figures of slides 2 and 12 are `PromptTrip` and `PipelineTrail`. They are built from the same blocks.

A bar row looks the same on every slide: a 12 px bar on a light track that starts at zero, the value at 20 px with tabular digits, and a check mark after a value that passes.

One trap: the deck runs UnoCSS, which reads a class named like one of its utilities as that utility. A class called `table` becomes `display: table`, and `flex`, `grid`, `block` or `hidden` would do the same. Give a class a name of its own, such as `gate-table`.

## Motion

- When a slide opens, its parts rise in calmly, one after the other. Then each click is one beat.
- A click moves something at once, within a tenth of a second, and no beat lasts more than about 2.5 s before the speaker can talk over it.
- Going back, or clicking fast, always lands on the right state. The PDF shows the end of each click. With reduced motion, things fade instead of moving.

## The art

The Poya paper-cut stays on the cover and on the roadmap (slide 13) only, cut in the deck's ink. On the roadmap, its one red is the heart on the station where we stand today. We draw no new figurative art: no laptops, hands, clouds or people.
