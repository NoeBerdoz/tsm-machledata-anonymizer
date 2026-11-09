# Benchmark protocol

We freeze this protocol at v0, before the seminar talk on 2026-11-16. If we change it after that, we must measure every model again.

This protocol says how we measure size and latency for goal O3. With the same rules for every model, all points of the compression curve can be compared. The code that applies it is `src/pii_anonymizer/benchmark.py`, and the quality metrics are defined in [evaluation.md](evaluation.md).

## Reference machine

- CPU: Intel Core i5-1130G7 (4 cores, 8 threads)
- RAM: 16 GB
- OS and Python version: recorded in each row of the results
- Power: on mains, with no other heavy process running

The reference machine is Michael's laptop, an ordinary laptop. Michael runs the reference measurements, and the official numbers for the goals come from this laptop.

## Other machines

Latency numbers only compare within one machine. Any teammate can still add rows measured on their own laptop. The `cpu` column of the results tells the machines apart, and a rerun only replaces the row of the same CPU. The same commands work on Linux, macOS and Windows.

The quality gate of the CI (#14) runs the student and the teacher in the same job, on the same machine. It checks the size and the latency ratio (student p95 at most a quarter of the teacher's), so it needs no reference machine.

## Inputs

- The texts: a fixed sample of 30 T2-dev snippets, listed by snippet ID in `src/pii_anonymizer/latency_ids.txt`, one ID per line. We create this file in issue #6, once T2-dev exists (issue #5).
- We measure latency only on a test set that holds this sample. On the other test sets, the latency cells stay empty.
- We count the length of an input in words, split on whitespace. We report latency per input and per 100 words.

## Runtime settings

- Runtime and version: the baselines run in different runtimes (Python regular expressions, Presidio, PyTorch). So each detector reports its runtime and version, and we record them in each row of the results.
- Threads: 4 intra-op threads and 1 inter-op thread, one per core of the reference laptop. The evaluation script sets `OMP_NUM_THREADS`, `MKL_NUM_THREADS` and `OPENBLAS_NUM_THREADS` to 4 before it loads a detector. A detector whose runtime has its own settings (for example `torch.set_num_threads` and `torch.set_num_interop_threads`) applies them too.
- Batch size: 1, because our app sends one prompt or one file at a time.

## Procedure

1. Load the model once, outside the timed part.
2. Warm up with 5 calls, which go through the first texts of the sample. We do not record them.
3. Run each input 10 times, and record the wall-clock time of each call with `time.perf_counter`.
4. Report p50 and p95 over all recorded calls (300 calls for 30 inputs). We use linear interpolation between the closest values.
5. For the latency per 100 words, we divide each call's time by the words of its input, times 100, and take p50 and p95 the same way.

Five warm-up calls are enough for lazy initialisation and caches to settle. Ten runs per input give 300 calls, so the p95 rests on 15 calls and does not jump with one slow call. If the fp32 teacher takes about 200 ms per call, a run lasts about a minute.

## Size

The size is the sum of every file needed to run the model: weights, tokenizer and config. Each detector lists these files or their folders, and folders are walked recursively. A file is counted once, even if it is listed twice. We report it in bytes and in MB (10^6 bytes). A detector made only of rules lists no files, and its size cells stay empty.

## Output

The evaluation script writes `size_bytes`, `size_mb`, `threads`, `latency_p50_ms`, `latency_p95_ms` and the same two values per 100 words into `results/results.csv`, next to the quality metrics. Each row also records the runtime, the CPU, the OS, the Python version and the date. [evaluation.md](evaluation.md) lists every column.
