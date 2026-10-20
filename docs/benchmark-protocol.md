# Benchmark protocol

Status: draft. We freeze this protocol at v0, before the seminar talk on 2026-11-16. If we change it after that, we must measure every model again.

This protocol says how we measure size and latency for goal O3. With the same rules for every model, all points of the compression curve can be compared.

## Reference machine

- CPU: TODO (name the laptop model and CPU at v0)
- RAM: TODO
- OS and Python version: TODO
- Power: on mains, with no other heavy process running

## Inputs

- The texts: TODO (a fixed sample of T2-dev, listed by snippet ID in a file that we keep with the code)
- We count the length of an input in words. We report latency per input and per 100 words.

## Runtime settings

- Runtime and version: TODO (for example ONNX Runtime x.y)
- Threads: TODO (fixed intra-op and inter-op counts)
- Batch size: 1, because the hooks process one tool output at a time

## Procedure

1. Load the model once, outside the timed part.
2. Warm up with TODO runs. We do not record them.
3. Run each input TODO times, and record the wall-clock time of each call.
4. Report p50 and p95 over all recorded calls.

## Size

The size is the sum of every file needed to run the model: weights, tokenizer and config. We report it in bytes and in MB (10^6 bytes).

## Output

The evaluation script writes `size_bytes`, `latency_p50_ms` and `latency_p95_ms` into its metrics file, next to the quality metrics.
