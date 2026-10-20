# Report

We write the report in [Typst](https://typst.app). It has 8 pages at most, references not counted.

Build it from the repository root:

```sh
typst compile report/main.typ report/main.pdf
```

While you write, use `typst watch report/main.typ`. It builds the PDF again each time you save. Do not commit the PDF: git ignores it.

Put figures in `report/figures/`. When a result is final, copy its plot there.
