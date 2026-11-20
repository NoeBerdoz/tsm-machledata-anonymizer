# Data

The data is not stored in git. It is versioned with DVC: git only keeps the small `.dvc` files that point to it.

- `raw/`: the datasets as we downloaded them.
- `prepared/`: the data after the `prepare` stage, ready for training.
- `test/`: our test sets, such as the T2 pilot and the [O4 scripted requests](../docs/evaluation.md#scripted-o4-requests). The O4 manifest and its attachments share one `.dvc` file so they are versioned together.
