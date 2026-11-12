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

Each slide of the seminar deck lives in its own file in `seminar/pages/`, and `seminar/THEME.md` says how the slides look and how to write one.

The slides after "Questions?" are an appendix for readers. We do not present them, but they make the PDF explain the theory on its own.

We fill in the numbers in two files. `seminar/data/baseline.ts` holds the v0 baselines, and `seminar/data/goals.ts` holds the short form of the SMART goals.
