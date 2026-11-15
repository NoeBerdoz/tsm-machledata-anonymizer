---
eyebrow: Appendix for readers
---

# PTQ and QAT

<div class="appx cols">
<div>

### Post-training quantization (PTQ)

PTQ rounds a model that is already trained, with no retraining. The weights are rounded from their own range. In static int8 PTQ the activations, the values inside the model as it runs, are rounded too. Their ranges are not known in advance, so we run a few inputs, a calibration set, through the model and record them. Calibration belongs to this static case. PTQ may lose recall, so recall is measured after it.

### Which tensors

The weights go to int8. On the size path of slide 9, int4 for the word embeddings is an option. Any tensor left in float counts in the delivered size.

</div>
<div>

### Quantization-aware training (QAT)

QAT trains with the rounding simulated. In the forward pass, each quantized tensor is rounded to its grid and read back, as on slide 8. The model learns weights that cope with the rounding, so QAT can recover accuracy that PTQ loses. It costs a training run.

### The straight-through estimator

Rounding has a zero gradient almost everywhere. The straight-through estimator approximates the gradient of the rounding by 1 and passes the gradient through (Bengio, Léonard and Courville 2013). Where the clamp clips a value, the gradient is usually set to 0, so clipping can stop it.

$$\frac{\partial \hat{x}}{\partial x} \approx \begin{cases} 1 & \text{inside the range} \\ 0 & \text{where } x \text{ is clipped} \end{cases}$$

</div>
</div>

<!--
Appendix for readers, not presented.
-->
