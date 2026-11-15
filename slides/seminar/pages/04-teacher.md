---
part: 2
eyebrow: Our starting model
clicks: 2
source: 'Model card on Hugging Face. Tests: 1,000 texts of ai4privacy OpenPII-1M, validation.'
---

# We plan to start from *GLiNER2-PII*

<TeacherIntro />

<!--
Target time 0:40. Speaker: to assign.

To build our small model, we start from a bigger one: GLiNER2-PII. It finds personal data and gives each piece a type.
[click] Why this one? We tested four tools before our training. It found the most: 81 percent.
[click] But as published, it has two gaps. It misses one entity in five. And at 1,244 megabytes, it is far from our goal of 8 times smaller. The next slide shows how we close both.

If asked: how fast is it? On our development Mac (Apple M5 Max, CPU, 4 threads), GLiNER2-PII takes 138 ms at p95 per call, on texts of 12 to 177 words. The official numbers will come from the reference laptop.

If asked why not OpenAI's Privacy Filter: in our test setup, Privacy Filter finds fewer names and places. We did not use OpenAI's own decoder. GLiNER2-PII is also less than half the size.

If asked: why is the regex at 8 %? It only finds Swiss numbers and e-mails, and these public texts have almost no valid Swiss values. On our Swiss set it finds 95 %.

If asked why fine-tune when the regex and GLiNER2-PII already reach 99 % on Swiss IDs: the regex does the Swiss numbers. Our model must find names, places and dates, and on our tests GLiNER2-PII still misses one entity in five overall.
-->
