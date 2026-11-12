---
part: 3
clicks: 4
---

# Int8 quantization stores each weight *in 1 byte instead of 4*

<QuantExample class="quant-x" :step="$clicks" />

<!--
Target time 0:35. Speaker: to assign.

Take one weight, 0.4237: 4 bytes in float32. Our example step is 0.01.
[click] Divide by the step: 42.37. Round to 42 and store it in 1 byte, as int8.
[click] Read back, it is 0.42. The error, 0.0037, is at most half a step.
[click] Every weight is rounded the same way.
[click] The teacher's weights: 1.23 gigabytes. In int8, about 0.31.
-->
