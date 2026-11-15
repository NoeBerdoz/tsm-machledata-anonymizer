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
TODO: the interface (prompt and attached files), the local engine (regex rules and our model), the replacement by placeholders and why (issue #17), the mapping table on the device, the backend (FastAPI) and the OpenAI Responses API, the restoration on the device.

= Experiments
TODO: T1, T2-dev and T2-final, OOD benchmarks, reference CPU and benchmark protocol.

= Results against the SMART goals
#table(
  columns: (auto, 1fr, auto, auto),
  table.header[*Goal*][*Target*][*Measured*][*Met*],
  [O1], [Models alone: student recall ≥ 95 % of the teacher's and at least GLiNER2-PII's (80.6 % on T1). Regex and model: Swiss IDs ≥ 99 %, pooled], [TODO], [TODO],
  [O2], [Char. precision ≥ GLiNER2-PII on the same set, utility through the app ≥ 90 % on 20 frozen test prompts, at least 18 solved without pseudonymization, those results frozen before any run with it. Pinned OpenAI model version and settings, 3 runs per condition, solved when 2 of 3 pass, every result kept. 5 stress prompts reported], [TODO], [TODO],
  [O3], [At least 8 times smaller in exact bytes (at most about 155.6 MB), at least 1.5 times faster (p95)], [TODO], [TODO],
  [O4], [0 leaks added by the app, in everything that leaves the device and in the backend's payload to OpenAI. 100 % restoration of intact placeholders to the stored value, spaces normalized. Every listed bad replacement flagged. 0 silent failures. Swaps between two valid placeholders are outside the guarantee.], [TODO], [TODO],
  [O5], [Across the whole project, 0 installed versions without a passing MLflow gate record for the same file hash. Five scenarios by 7 December: a degraded model fails the frozen recall threshold and scores at least 3 recall points below the good model on T2-dev. A model without results is refused. A good model is published, and the app installs it and shows the installed version. The app keeps its last approved version when a download fails. An injected slowdown fires the alert.], [TODO], [TODO],
)

= MLOps pipeline
TODO: DVC stages, CI gates, artifact publication, monitoring.

= Limits
TODO: synthetic training data, only requests through our app are protected, text only.

= Conclusion
TODO: what we reached against the SMART goals.
TODO: future work. Fake values in place of placeholders (issue #17) are a possible continuation, above all if the O2 test prompts show that placeholders make the answers worse.

#bibliography("refs.bib")
