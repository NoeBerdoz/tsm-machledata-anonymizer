// Project report. Eight pages at most, references excluded.
#set document(
  title: "A small on-device PII anonymizer for AI coding agents",
  author: ("TODO", "TODO", "TODO", "TODO"),
)
#set page(paper: "a4", margin: 2.2cm, numbering: "1")
#set text(size: 10.5pt, lang: "en")
#set par(justify: true)
#set heading(numbering: "1.")

#align(center)[
  #text(size: 16pt, weight: "bold")[A small on-device PII anonymizer for AI coding agents]

  TSM_MachLeData, MSE HES-SO, autumn 2026 \
  TODO: team members
]

#heading(numbering: none)[Abstract]
TODO: problem, method, main result in numbers.

= Introduction
TODO: why tool outputs of coding agents leak personal data, and what we built.

= Related work
TODO: PrivAiTe @privaite, Hide and Seek @has, GLiNER2 @gliner2, knowledge distillation @hinton2015, quantization @jacob2018.

= Method
== Teacher fine-tuning
TODO (v1).
== Distillation and gold-label control
TODO (v2).
== Quantization
TODO (v3).
== Hooks integration
TODO: PostToolUse, PreToolUse, MessageDisplay, UserPromptSubmit.

= Experiments
TODO: T1, T2-dev and T2-final, OOD benchmarks, reference CPU and benchmark protocol.

= Results against the SMART goals
#table(
  columns: (auto, 1fr, auto, auto),
  table.header[*Goal*][*Target*][*Measured*][*Met*],
  [O1], [Student recall ≥ 95 % of teacher, Swiss IDs ≥ 99 %], [TODO], [TODO],
  [O2], [Char. precision ≥ GLiNER2-PII, utility ≥ 90 %], [TODO], [TODO],
  [O3], [≥ 12× smaller, p95 ≤ ¼ of teacher], [TODO], [TODO],
  [O4], [Leaks within budget, 0 silent fallbacks, 100 % restoration], [TODO], [TODO],
  [O5], [Gate refuses and publishes, one alert], [TODO], [TODO],
)

= MLOps pipeline
TODO: DVC stages, CI gates, artifact publication, monitoring.

= Limits
TODO: synthetic training data, typed prompts not covered by hooks, text only.

= Conclusion
TODO.

#bibliography("refs.bib")
