---
theme: default
title: Distilling and quantizing a PII detector
info: Seminar talk, TSM_MachLeData, 16 November 2026. 8 minutes plus 3 minutes of questions.
exportFilename: seminar
canvasWidth: 1280
aspectRatio: 16/9
colorSchema: light
fonts:
  provider: none
transition: page-fade
defaults:
  layout: doc
layout: cover
meadow: false
---

<p class="caption cover-course">TSM_MachLeData, MSE HES-SO, seminar talk, 16 November 2026</p>

<div class="grid12 cover-head">
  <div class="cover-main">
    <p class="cover-project">On-device PII pseudonymizer for cloud LLMs</p>
    <h1 class="cover-title">Distilling and quantizing<br>a PII detector</h1>
    <p class="cover-tagline">How small can a pseudonymizer get before it starts to leak?</p>
  </div>
  <ul class="cover-team label">
    <li>Noé Berdoz</li>
    <li>Nicolas Hertling</li>
    <li>Raul Santos Barreira</li>
    <li>Michael Strefeler</li>
  </ul>
</div>

<ArtSlot name="PoyaCover" class="cover-art" :w="1280" :h="330" :meadow="!!$frontmatter.meadow" :walk="($renderContext === 'slide' || $renderContext === 'presenter') && !$nav.isPrintMode" />

<!--
Target time 0:15. Speaker: to assign.

Hello. We are building a pseudonymizer that runs on the user's laptop, in front of a cloud LLM. Our advanced topic is model compression. Our question is how small the detector can get before it starts to leak.
-->

---
section: The problem
clicks: 3
---

<div class="hook">
  <Sentence :state="$clicks" />
</div>

<!--
Target time 0:20. Speaker: to assign.

Here is one sentence a user could send to an LLM. It holds a name, an AVS number and an address.
[click] First, we detect the personal data.
[click] Then we cut it out.
[click] Then we replace each value with a placeholder that we can put back later. That is the whole product in one line.
-->

---
section: The setting
clicks: 3
---

# We replace personal data before it leaves the device

<Setting class="setting-fig" :step="$clicks" />

<p class="label gdpr">The table on the device can put the real values back. So we call it pseudonymization, not anonymization <span class="muted">(GDPR Art. 4(5), Recital 26)</span>.</p>

<!--
Target time 0:40. Speaker: to assign.

The user writes a prompt in our app. It holds a name and an IBAN.
[click] A local engine finds them. Regex rules catch the fixed formats, like AVS numbers and IBANs. Our model catches what needs context, like names and addresses. Each value is replaced, and the pairs go into a mapping table on the device.
[click] Only the pseudonymized text crosses the privacy boundary. It goes to our FastAPI backend, which calls the OpenAI Responses API.
[click] The answer comes back with the placeholders. Once it is on the device, we look up the table and put the real values back.
The identifying pieces stay here. The rest of the text crosses.
Because the table can put the values back, the GDPR calls this pseudonymization, not anonymization, in Article 4, point 5, and Recital 26.
The engine runs on every request, on a laptop CPU. So the detector has to be small and fast.
-->

---
section: The teacher
clicks: 1
---

# The teacher is too big for every request

<TeacherSize :step="$clicks" />

<!--
Target time 0:30. Speaker: to assign.

Our teacher is GLiNER2-PII. We read its size from the safetensors header. It has 307 million parameters, 1.23 gigabytes in float32, and it knows 42 entity types.
[click] 192 million of these parameters, 63 percent, are word embeddings for a vocabulary of 250,112 tokens. So most of the model is a dictionary. We only need French, German, Italian and English, so pruning the vocabulary is an option before we even distil.
-->

---
section: Distillation
clicks: 2
---

# Soft labels carry more than the right answer

<div class="grid12 distil-a">
  <div class="vignette">
    <ArtSlot name="Alembic" :w="200" :h="200" />
  </div>
  <div class="soft-wrap">
    <SoftLabels :step="$clicks" />
  </div>
</div>

<p class="lede takeaway">The student also learns that Dupont can be a place.</p>

<!--
Target time 0:50. Speaker: to assign.

Distillation is like the copper still of a Swiss eau-de-vie. A big pot, the teacher, gives a small flask, the student.
In this sentence "Dupont" appears twice. The first one is a person, the second one is a street. The gold label only says PERSON, with probability one.
The teacher gives a probability for every class. At temperature one it gives 0.82 to PERSON and 0.14 to LOCATION.
[click] We divide the logits by the temperature tau before the softmax. At tau equal to two, LOCATION gets 0.24.
[click] At tau equal to four, the bars are flatter still. This is a categorical teaching example with made-up logits. GLiNER2 scores spans with a sigmoid, and the appendix shows how the same idea carries over.
So the soft labels tell the student something the gold label hides. Dupont can also be a place.
-->

---
section: Distillation
clicks: 1
---

# The student copies the teacher and the labels

<DistillLoss :step="$clicks" />

<!--
Target time 0:50. Speaker: to assign.

This is the distillation loss of Hinton, Vinyals and Dean, 2015. The first term is a KL divergence. The student copies the teacher's softened distribution. Alpha sets how much this term counts.
The factor tau squared keeps the gradient scale roughly constant when we change the temperature. Hinton and colleagues derive it in the high-temperature limit.
The second term is the usual cross-entropy with the gold labels.
[click] Distillation needs a fair test. Goal O1 trains a control student with the same architecture, the same data and the same budget, but on the gold labels only. We compare recall. Distillation earns its place only if it beats this control.
-->

---
section: Quantization
clicks: 1
---

# Quantization snaps weights to a grid

<div class="grid12 quant">
  <div class="vignette">
    <ArtSlot name="StationClock" :w="200" :h="200" :hour="10" :minute="$clicks >= 1 ? 9 : 8" />
    <p class="caption clock-cap">Its minute hand can only stop on one of 60 marks.</p>
  </div>
  <div class="quant-fig">
    <QuantGrid :step="$clicks" />
    <div class="quant-eq label">
      <span><Tex e="\hat{x} = s\,(q - z)" /></span>
      <span><Tex e="|x - \hat{x}| \le s/2" /></span>
      <span class="caption legend"><i class="sw ghost" />weight <i class="sw stored" />stored <i class="sw err" />error</span>
    </div>
  </div>
</div>

<!--
Target time 0:50. Speaker: to assign.

Think of a station clock. Its minute hand does not glide. It jumps, and it can only stop on one of 60 marks.
Quantization does the same with the weights. Each dot is a weight of the model, in float32, 32 bits each. Below is a grid of 16 integer levels, which is 4 bits. int8 has 256.
[click] Every weight snaps to the nearest level. The short lines are the rounding errors.
We store the integer q. We read it back as s times q minus z. s is the step between two levels, and z is the integer that stores zero. Inside the range, the error is never more than half a step. The formulas and their assumptions are in the appendix.
-->

---
section: Quantization
clicks: 4
---

# PTQ or QAT, and the size path

<div class="grid12 ptq">
  <p class="label"><span class="mono">PTQ</span>&nbsp; quantizes a trained model, with no retraining.</p>
  <p class="label"><span class="mono">QAT</span>&nbsp; trains with the rounding and can recover accuracy.</p>
</div>

<CompressionPath :step="$clicks" />

<!--
Target time 0:45. Speaker: to assign.

There are two ways to quantize. Post-training quantization takes a trained model and needs no retraining. In static int8, it also calibrates the activation ranges on a few inputs. It may lose recall. Quantization-aware training simulates the rounding during training, so it can recover accuracy, at the cost of a training run.
Now the sizes. The teacher in float32 is 1.23 gigabytes. This is the only measured bar.
[click] Plain int8 is about 0.31 gigabytes. That is 307 million parameters times one byte.
[click] Pruning the vocabulary brings it to about 150 megabytes.
[click] A six-layer distilled student brings it to about 100 megabytes. That is our O3 target, 12 times smaller. It needs the pruned vocabulary, because the int8 embeddings alone weigh about 192 megabytes.
[click] int4 is an option, at about 55 megabytes. The dashed bars are estimates from parameter counts. We will measure each artifact when we build it.
-->

---
section: Evaluation
clicks: 3
---

# How we count a leak

<p class="lede sub">An entity is protected only if all its characters are masked.</p>

<LeakCount :step="$clicks" />

<!--
Target time 0:35. Speaker: to assign.

Here is one line of a CSV file that a user attached to a prompt. It holds a Swiss IBAN, the gold entity, 26 characters.
[click] If we mask all of it, the IBAN is protected. Recall is one out of one, and character precision is 1.
[click] If the last digits stay visible, it is a leak. Recall drops to zero, even though every masked character was right.
[click] If we mask the whole line, the IBAN is protected, but we masked too much. Character precision drops to 26 out of 54, 0.48.
Recall is our primary metric, because one minus recall is the leak rate. We measure on T1, from ai4privacy, and on T2, our own prompts and attached files with Swiss identifiers.
-->

---
section: SMART goals
---

# Five goals, frozen at this talk

<Goals />

<!--
Target time 0:45. Speaker: to assign.

These are our five goals. We freeze every threshold today.
O1 is protection. The quantized student keeps at least 95 percent of the fine-tuned teacher's recall, and Swiss identifiers reach 99 percent. It must also beat a gold-label control and GLiNER2-PII as published.
O2 is utility. We run 20 scripted tasks through our app, with and without pseudonymization. The tasks solved in both, divided by the tasks solved without, must reach 90 percent.
O3 is compression. At least 12 times smaller and four times faster on a laptop CPU.
O4 is end to end. We plant 100 values in prompts and files. Restoration must be exact, and the app never fails silently.
O5 is the MLOps pipeline. The gate refuses a degraded model and publishes a good one, and an alert fires on the on-device time. It all works by 7 December.
Four thresholds are set at v0 by fixed rules, from the baselines on T2-dev. The full goals are in the appendix.
-->

---
section: Baseline
---

# Baseline v0 on T2-dev

<Baseline />

<!--
Target time 0:35. Speaker: to assign.

These are the four baselines we measure at v0, on T2-dev. Regex only, with the same rules we use everywhere. Presidio, an open-source PII toolkit. GLiNER2-PII as published. Its size is the only number we have measured so far, 1.23 gigabytes. And the OpenAI Privacy Filter.
For the team. Once the v0 results are in data/baseline.ts, read them here.
-->

---
section: Pipeline
clicks: 2
---

# Only models that meet our thresholds are released

<Gate :step="$clicks" />

<p class="label muted gate-cap">The gate checks the O1 to O3 thresholds on T2-dev.</p>

<!--
Target time 0:30. Speaker: to assign.

Training runs on Google Cloud. GitHub Actions runs the tests, and DVC and MLflow track the data, the models and the runs. The pipeline fine-tunes the teacher, distils, quantizes and evaluates on T2-dev.
[click] Model A misses a threshold. The gate stays closed, and the model is rejected.
[click] Model B passes. It goes to the registry, and the app on the device installs it. Sentry watches the pseudonymization time and the errors, without any content.
-->

---
section: Roadmap
---

# Roadmap

<Route :progress="0" class="route-fig" />

<!--
Target time 0:15. Speaker: to assign.

This is our climb. Today we have v0. The fine-tuned teacher comes at the end of November. The pipeline, the gate and the monitoring work by 7 December. The distilled and quantized students come around 10 December, and the final talk around mid-December. The path shows the schedule, not better accuracy.
-->

---
layout: cover
clicks: 1
---

<p class="questions">Questions?</p>

<div class="close-sentence">
  <Sentence :state="$clicks >= 1 ? 0 : 3" />
</div>

<ArtSlot name="PoyaDesalpe" class="close-art" :w="1280" :h="240" />

<!--
Target time 0:05. Speaker: to assign.

[click] And on the device, our sentence gets its real values back. Thank you. We are happy to take your questions.
-->

---
section: Appendix for readers
---

# Distillation in detail

<div class="appx cols">
<div>

### Soft labels with a temperature

The teacher gives a logit $z_i$ for each class $i$. A softmax with temperature $\tau$ turns the logits into probabilities.

$$p_i^{\tau} = \frac{e^{z_i/\tau}}{\sum_j e^{z_j/\tau}}$$

At $\tau = 1$ this is the usual softmax. A higher $\tau$ flattens the distribution, so the student also sees how the teacher ranks the wrong classes. The slide uses the illustrative logits $z = (4.0, 2.2, 0.6, 0.0)$. They show uncertainty, not evidence that this Dupont is a place.

### The loss

$$\mathcal{L} = \alpha\,\tau^2\,\mathrm{KL}\big(p_T^{\tau}\,\|\,p_S^{\tau}\big) + (1-\alpha)\,\mathrm{CE}\big(y,\,p_S\big)$$

The first term makes the student $S$ match the softened distribution of the teacher $T$. The second term is the usual cross-entropy with the gold label $y$, at $\tau = 1$. The weight $\alpha$ sets the balance.

</div>
<div>

### Why the factor $\tau^2$

Hinton, Vinyals and Dean (2015) show that the gradients of the soft term scale as $1/\tau^2$ in the high-temperature limit. Multiplying by $\tau^2$ keeps the gradient scale roughly constant when the temperature changes.

### Unlabelled text

The teacher can also label extra text that has no gold labels, such as logs or e-mails. On that text only the soft term applies. Training on extra unlabelled text is a separate comparison. It is not part of the control below.

### The control of goal O1

We train a control student with the same architecture, the same gold data and the same training budget as the distilled student, but on the gold labels only. Distillation earns its place only if the distilled student beats this control on recall.

</div>
</div>

<!--
Appendix for readers, not presented.
-->

---
section: Appendix for readers
---

# Distillation for GLiNER2 spans

<div class="appx cols">
<div>

### From classes to span and type pairs

The slides use a categorical example, one softmax over four classes. GLiNER2 works differently (Zaratiana et al. 2025). It scores each pair of a candidate text span and an entity type with a sigmoid. So each pair is a yes or no decision with its own probability.

$$p_T = \sigma(z_T/\tau), \qquad p_S = \sigma(z_S/\tau)$$

Here $z_T$ and $z_S$ are the teacher's and the student's scores for the same pair. We sum both terms of the loss over the span and type pairs, with the same weights $\alpha$ and $\tau^2$. The teacher and the student score the same pairs, so each term compares like with like.

</div>
<div>

### The soft term becomes a binary KL

Per pair, the soft term is the KL divergence between two Bernoulli distributions.

$$\mathrm{KL}(p_T\,\|\,p_S) = p_T \log\frac{p_T}{p_S} + (1-p_T)\log\frac{1-p_T}{1-p_S}$$

### The gold term becomes a binary cross-entropy

Per pair, the gold label $y \in \{0, 1\}$ says whether the span is an entity of this type. At $\tau = 1$ the gold term is the binary cross-entropy.

$$\mathrm{BCE}(y, p_S) = -\big[\,y \log p_S + (1-y)\log(1-p_S)\,\big]$$

</div>
</div>

<!--
Appendix for readers, not presented.
-->

---
section: Appendix for readers
---

# Quantization in detail

<div class="appx cols">
<div>

### Affine quantization

We store a real value $x$ as a $b$-bit integer $q$. The step size $s$ and the zero point $z$ map the range of the values onto $2^b$ evenly spaced levels (Jacob et al. 2018).

$$s = \frac{x_{max} - x_{min}}{2^b - 1}, \qquad z = \mathrm{round}\!\left(-\frac{x_{min}}{s}\right)$$

$$q = \mathrm{clamp}\big(\mathrm{round}(x/s) + z,\; 0,\; 2^b - 1\big), \qquad \hat{x} = s\,(q - z)$$

### Levels

The figure uses $b = 4$, an unsigned grid from 0 to 15 with 16 levels. int8 has $2^8 = 256$ levels. The station clock has 60 marks for its minute hand.

</div>
<div>

### Assumptions

- The step size is positive, $s > 0$, so the range is not empty.
- The zero point is an integer inside the range, $0 \le z \le 2^b - 1$. This holds when the range contains 0, and then 0.0 is stored exactly.
- For $x$ inside the range the grid covers, from $s\,(0 - z)$ to $s\,(2^b - 1 - z)$, rounding is the only error, and $|x - \hat{x}| \le s/2$.
- Outside that range the clamp clips $x$, and the error can be larger. The half-step bound does not cover clipping.

</div>
</div>

<!--
Appendix for readers, not presented.
-->

---
section: Appendix for readers
---

# PTQ and QAT

<div class="appx cols">
<div>

### Post-training quantization

PTQ quantizes a model that is already trained, with no retraining. The weights are quantized from their own range. In static int8 PTQ the activations are quantized too. Their ranges are not known in advance, so we run a small calibration set through the model and record them. Calibration belongs to this static case. PTQ may lose recall, and we measure how much.

### Which tensors

We quantize the weights to int8, or to int4 as an option. With static int8 we also quantize the activations. Any tensor left in float counts in the delivered size.

</div>
<div>

### Quantization-aware training

QAT simulates the deployment quantization during training. In the forward pass each quantized tensor is rounded to its grid and read back. The model learns weights that survive the rounding, so QAT can recover accuracy that PTQ loses. It costs a training run.

### The straight-through estimator

Rounding has a zero gradient almost everywhere. The straight-through estimator approximates the gradient of the rounding by 1 and passes the gradient through (Bengio, Léonard and Courville 2013). Where the clamp clips a value, the gradient is usually set to 0, so clipping can stop it.

$$\frac{\partial \hat{x}}{\partial x} \approx \begin{cases} 1 & \text{inside the range} \\ 0 & \text{where } x \text{ is clipped} \end{cases}$$

</div>
</div>

<!--
Appendix for readers, not presented.
-->

---
section: Appendix for readers
---

# Size estimates and their assumptions

<div class="appx">

<div class="size-table">
  <div class="caption">Step</div><div class="caption">Size</div><div class="caption">How we get it</div>
  <div>fp32 teacher</div><div class="mono">1.23 GB</div><div>Measured. 307M parameters at 4 bytes, read from the safetensors header.</div>
  <div>int8</div><div class="mono">about 0.31 GB</div><div>Estimate. 307M parameters at 1 byte.</div>
  <div>+ pruned vocabulary</div><div class="mono">about 150 MB</div><div>Estimate from parameter counts, keeping the tokens of French, German, Italian and English.</div>
  <div>+ six-layer student</div><div class="mono">about 100 MB</div><div>Estimate. The O3 target is 12 times smaller than 1.23 GB, about 102 MB.</div>
  <div>+ int4</div><div class="mono">about 55 MB</div><div>Estimate at half a byte per weight. An option.</div>
</div>

<div class="cols size-notes">
<div>

The 100 MB point needs the pruned vocabulary. The int8 embeddings alone weigh about 192 MB, since 192M of the 307M parameters (63 %) are embeddings of the 250,112-token vocabulary. At int4 they would still weigh about 96 MB.

</div>
<div>

Delivered size counts every file needed to run the model. That is the weights, the tokenizer, the config, the quantization scales and any tensors left in float. We record the real size of each artifact when we produce it.

</div>
</div>

</div>

<!--
Appendix for readers, not presented.
-->

---
section: Appendix for readers
---

# Metrics and test sets

<div class="appx cols">
<div>

### T1

The validation split of the ai4privacy dataset chosen at v0 (OpenPII-1M or open-pii-masking-500k), in French, German, Italian and English. We never use it for training.

### T2

Our own set of about 200 snippets of what users send through our app. These are prompts, e-mails, documents, CSV tables, pasted code or logs. For an attached file (PDF, TXT, DOCX, CSV), the snippet is the text extracted from it, because that is what the detector receives. We plant values in them, including Swiss identifiers (AVS numbers starting with 756, Swiss IBANs, +41 phone numbers, postal codes), so we know the labels by construction. Before any tuning we split T2 into T2-dev, for thresholds and the gate, and a frozen T2-final. Related snippets stay on the same side.

</div>
<div>

### Recall, the primary metric

Both sets carry gold character offsets. An entity counts as protected only if all its characters are masked, so a partly masked IBAN is a leak. Recall is the micro-average of this rule over the gold entities, also reported per entity type. One minus recall is the leak rate.

### Character precision

The share of masked characters that belong to a gold entity. It shows over-masking. A model that masks everything fails it. In the example, masking the whole 54-character line gives $26/54 = 0.48$.

</div>
</div>

<!--
Appendix for readers, not presented.
-->

---
section: Appendix for readers
---

# SMART goals in full, O1 to O3

<div class="appx small cols3">
<div>

### O1 Protection

The quantized student (v3) keeps at least 95 % of the fine-tuned teacher's (v1) recall on T1 and on T2-final, each set separately. Swiss structured identifiers, caught by the regex rules and the model together, reach at least 99 % recall.

No type may fall below the recall that the best v0 baseline reaches on that type on T2-dev. This per-type floor is decided at v0.

The student must beat GLiNER2-PII as published, with a higher micro recall on T2-final at equal or better character precision. It must also beat a control student with the same architecture, gold data and training budget, trained on the gold labels only.

We report structured and free-text entities separately. We also report, with no threshold, recall and character precision on the out-of-distribution sets SPY, TAB, GraSCCo_PHI and BigCode PII.

</div>
<div>

### O2 Utility

We run 20 scripted tasks through our app, once with pseudonymization and once without, with the same OpenAI model and identical settings. Each task has an oracle fixed in advance, such as an exact value, expected JSON fields or a label.

Paired utility is the number of tasks solved in both conditions divided by the number solved without pseudonymization. It must be at least 90 %.

The student's character precision is measured on T2-final. Its threshold is decided at v0 as the character precision GLiNER2-PII reaches on T2-dev.

</div>
<div>

### O3 Compression

The delivered student is at least 12 times smaller than the measured 1.23 GB fp32 teacher. Size counts all files needed to run the model, weights and tokenizer included.

Its p95 latency is at most a quarter of the fp32 teacher's, on one reference laptop CPU named at v0. The benchmark protocol is frozen at v0, with the same texts, length counted in words, fixed runtime and thread settings, a warm-up and a fixed number of runs.

We publish a compression curve with at least 3 points (fp32, int8, distilled int8), and 5 with the options (pruned vocabulary, int4), each with its recall, size and latency.

O1 to O3 are evaluated at the final talk, around mid-December 2026.

</div>
</div>

<!--
Appendix for readers, not presented. The source is docs/smart-goals.md.
-->

---
section: Appendix for readers
---

# SMART goals in full, O4 and O5

<div class="appx small cols3">
<div>

### O4 End to end

We send scripted requests through our app, with prompts and attached files that hold 100 planted values, each with an ID. We measure leaks on what the backend sends to OpenAI. A planted value leaks if any of its characters reaches OpenAI unmasked, and we count each ID once. The leak budget is decided at v0 as half the distinct values that leak with GLiNER2-PII in the same requests, rounded down.

On normal responses, 100 % of the replacements are restored exactly, including repeated entities, distinct entities and text that already looks like a replacement.

</div>
<div>

### Failures and flags

The app never fails silently. If the engine fails, the request is not sent and the user is told. We inject such failures on purpose, and zero requests may reach the backend unpseudonymized.

In separate tests we inject unknown and altered replacements into the response. Every one is flagged to the user and never shown as a real value. Flagging does not count as a successful restoration.

### Decided at v0

The per-type floor (O1), the character precision threshold (O2), the reference CPU and benchmark protocol (O3), the leak budget (O4), and the alert window and threshold (O5). Each follows the rule stated with its goal, on T2-dev, and is frozen at this talk.

</div>
<div>

### O5 MLOps

A model is published to the MLflow registry, with a version, only if it meets on T2-dev the O1 detection thresholds, the O2 character precision threshold and the O3 size and latency thresholds. The 20 app tasks of O2 are not in the gate.

The demonstration shows a degraded model refused and a good model published, which the app then installs and whose version it reports. Sentry records the on-device pseudonymization time separately from the full response time, without any prompt or response content. The alert fires when the p95 of that time over a fixed window exceeds a threshold, and we trigger it on purpose.

The pipeline, the gate and the monitoring work by 7 December 2026.

</div>
</div>

<!--
Appendix for readers, not presented. The source is docs/smart-goals.md.
-->

---
section: Appendix for readers
---

# References

<div class="refs label">

Hinton, G., Vinyals, O. and Dean, J. (2015). Distilling the knowledge in a neural network. arXiv:1503.02531.

Jacob, B. et al. (2018). Quantization and training of neural networks for efficient integer-arithmetic-only inference. CVPR 2018. arXiv:1712.05877.

Bengio, Y., Léonard, N. and Courville, A. (2013). Estimating or propagating gradients through stochastic neurons for conditional computation. arXiv:1308.3432.

Zaratiana, U. et al. (2025). GLiNER2: An efficient multi-task information extraction system with schema-driven interface. arXiv:2507.18546. Model card at huggingface.co/fastino/gliner2-privacy-filter-PII-multi.

ai4privacy. OpenPII-1M and open-pii-masking-500k. huggingface.co/datasets/ai4privacy.

</div>

<!--
Appendix for readers, not presented.
-->
