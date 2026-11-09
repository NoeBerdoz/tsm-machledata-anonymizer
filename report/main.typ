// Project report. Eight pages at most, references excluded.
#set document(
  title: "A small on-device PII pseudonymizer for cloud LLMs",
  author: ("TODO", "TODO", "TODO", "TODO"),
)
#set page(paper: "a4", margin: 2.2cm, numbering: "1")
#set text(size: 10.5pt, lang: "en")
#set par(justify: true)
#set heading(numbering: "1.")

#align(center)[
  #text(size: 16pt, weight: "bold")[A small on-device PII pseudonymizer for cloud LLMs]

  TSM_MachLeData, MSE HES-SO, autumn 2026 \
  TODO: team members
]

#heading(numbering: none)[Abstract]
TODO: problem, method, main result in numbers.

= Introduction
TODO: why prompts and files sent to a cloud LLM leak personal data, and what we built.
TODO: one sentence on why we say pseudonymization: the mapping table lets us put the real values back. So we call it pseudonymization, not anonymization: the data can still be linked to a person with extra information, here the mapping table kept on the device. The GDPR draws the same line between the two (Art. 4(5) and Recital 26).

= Related work
TODO: PrivAiTe @privaite, Hide and Seek @has, GLiNER2 @gliner2, knowledge distillation @hinton2015, quantization @jacob2018.

= Method
== Teacher fine-tuning
TODO (v1).
== Distillation and gold-label control
TODO (v2).
== Quantization
TODO (v3).
== The app: pseudonymization engine, backend and restoration
TODO: the interface (prompt and attached files), the local engine (regex rules and our model), the replacement and the mapping table on the device, the backend (FastAPI) and the OpenAI Responses API, the restoration on the device.

= Experiments
TODO: T1, T2-dev and T2-final, OOD benchmarks, reference CPU and benchmark protocol.

= Results against the SMART goals
#table(
  columns: (auto, 1fr, auto, auto),
  table.header[*Goal*][*Target*][*Measured*][*Met*],
  [O1], [Student recall ≥ 95 % of teacher, Swiss IDs ≥ 99 %], [TODO], [TODO],
  [O2], [Char. precision ≥ GLiNER2-PII, utility through the app ≥ 90 %], [TODO], [TODO],
  [O3], [≥ 12× smaller, p95 ≤ ¼ of teacher], [TODO], [TODO],
  [O4], [Leaks within budget, 100 % exact restoration, 100 % of injected bad replacements flagged, 0 silent failures], [TODO], [TODO],
  [O5], [Gate refuses and publishes, one alert], [TODO], [TODO],
)

= MLOps pipeline
TODO: DVC stages, CI gates, artifact publication, monitoring.

= Limits
TODO: synthetic training data, only requests through our app are protected, text only.

= Conclusion
TODO.

#bibliography("refs.bib")
