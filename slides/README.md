# Slides

We have two [Slidev](https://sli.dev) decks. They share one `package.json`:

- `seminar/slides.md`: the seminar talk on 2026-11-16 (8 min + 3 min questions)
- `final/slides.md`: the final talk, mid-December 2026 (8 min + 3 min questions)

Both talks are about the technique, not the product. Most of the time goes to how distillation and quantization work, why we use them, what they cost, and what we measured. The use case only sets the scene.

```sh
cd slides
npm install            # first time only
npm run dev:seminar    # live preview, reloads when you save
npm run export:seminar # PDF export, needs playwright-chromium
```

Replace `seminar` with `final` for the final talk.

The seminar deck is also online at https://noeberdoz.github.io/tsm-machledata-anonymizer/seminar/. The workflow `.github/workflows/slides.yml` publishes it again on every push to `main` that changes the slides.

## Seminar deck design

The deck follows the Swiss International Style on a 1280 by 720 canvas. We use twelve columns, 72 px margins, 24 px gutters and an 8 px rhythm, and we keep very little text on the slides we present.

The titles and text are in Instrument Sans, and the chips, numbers and code are in Fragment Mono. Both fonts come from Google Fonts. The five font sizes and the colours are tokens on `:root` in `seminar/style.css`. Red (`#da291c`) only marks a leak or a failed gate, and black fill is kept for the masked values and the paper cuts.

Three marks tell the story. A dashed line means a value was detected, a black bar means it was masked, and a chip such as `<PERSON_1>` means it was replaced. A dashed outline also marks an estimate.

The poya paper cuts and the small pictures are in `seminar/components/art/`, and the slides place them with `ArtSlot`. To show the green meadow on the cover, set `meadow: true` in the frontmatter of the first slide.

Each diagram is a Vue component in `seminar/components/` that follows the clicks of its slide. The layouts are in `seminar/layouts/`, and the header line is in `seminar/slide-top.vue`.

The slides after "Questions?" are an appendix for readers. We do not present them, but they make the PDF explain the theory on its own.

We fill in the numbers in two files. `seminar/data/baseline.ts` holds the v0 baselines, and the chart appears once a baseline has real values. `seminar/data/goals.ts` holds the short form of the SMART goals.
