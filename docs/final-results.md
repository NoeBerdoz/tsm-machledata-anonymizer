# Final results

## O4 response corruptions and failures

| Measure | Count |
|---|---:|
| Corruptions injected | 9 |
| Corruptions flagged and shown unchanged | 9 |
| Failures with a visible error | 6 |
| Backend calls across the six failure cases | 0 |

```sh
uv run pytest -q \
  tests/test_app.py::test_response_corruption_is_shown_with_a_warning \
  tests/test_app.py::test_nothing_is_sent_when_the_engine_fails \
  tests/test_app.py::test_nothing_is_sent_when_a_file_is_skipped_or_unreadable
```
