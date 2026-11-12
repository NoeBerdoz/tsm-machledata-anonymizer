---
eyebrow: Appendix for readers
---

# Quantization in detail

<div class="appx cols">
<div>

### Affine quantization

We store a real value $x$ as a $b$-bit integer $q$. A step $s$ and a zero point $z$ map the range of the values onto $2^b$ evenly spaced levels (Jacob et al. 2018). int8 has $2^8 = 256$ levels.

$$s = \frac{x_{max} - x_{min}}{2^b - 1}, \qquad z = \mathrm{round}\!\left(-\frac{x_{min}}{s}\right)$$

$$q = \mathrm{clamp}\big(\mathrm{round}(x/s) + z,\; 0,\; 2^b - 1\big), \qquad \hat{x} = s\,(q - z)$$

### The example of slide 7

Slide 7 uses the symmetric form: signed int8 levels from $-128$ to $127$, no zero point ($z = 0$), and an example step $s = 0.01$. So $0.4237 / 0.01 = 42.37$ is stored as $q = 42$, and read back as $\hat{x} = 0.01 \times 42 = 0.42$. The error is $|x - \hat{x}| = 0.0037$, under the bound $s/2 = 0.005$. The other weights of the layer give $-19$, $7$ and $30$.

</div>
<div>

### Assumptions

- The step is positive, $s > 0$, so the range is not empty.
- The zero point $z$ is an integer on the grid, from $0$ to $2^b - 1$. This holds when the range contains 0, and then 0.0 is stored exactly. The symmetric form sets $z = 0$.
- For $x$ inside the range the grid covers, from $s\,(0 - z)$ to $s\,(2^b - 1 - z)$, rounding is the only error, and $|x - \hat{x}| \le s/2$.
- Outside that range the clamp clips $x$, and the error can be larger. The half-step bound does not cover clipping.
- The step is stored with the integers, one per tensor or per channel. So the steps add a little to the size.

</div>
</div>

<!--
Appendix for readers, not presented.
-->
