---
part: 2
eyebrow: The teacher
clicks: 3
source: 'Model card on Hugging Face. Tests: 1,000 texts of ai4privacy OpenPII-1M, validation. Full tables in the appendix.'
---

# We plan to start from *GLiNER2-PII*

<TeacherIntro />

<!--
Target time 0:40. Speaker: to assign.

To build our small model, we start from a bigger one: GLiNER2-PII. It finds personal data and gives each piece a type.
[click] Why this one? We tested four tools before our training. It found the most: 81 percent.
[click] By 30 November, we fine-tune it on our training set, because it misses one entity in five. Swiss IDs stay in it, for the formats our regex does not know.
[click] It becomes our teacher. It teaches a small model, the student, that runs on the laptop.

If asked: how fast is it? On our development Mac (Apple M5 Max, CPU, 4 threads), GLiNER2-PII takes 138 ms at p95 per call, on texts of 12 to 177 words. The official numbers will come from the reference laptop.

If asked why not OpenAI's Privacy Filter: we measured it too. It finds fewer names and places, it knows 8 types instead of 42, and it is more than twice as big. The appendix compares them.

If asked why fine-tune when the regex and GLiNER2-PII already reach 99 % on Swiss IDs: the regex does the Swiss numbers. Our model must find names, places and dates, and on our tests GLiNER2-PII still misses one entity in five overall.
-->
