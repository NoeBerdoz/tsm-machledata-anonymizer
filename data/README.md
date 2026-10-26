# Data

The data is not stored in git. It is versioned with DVC: git only keeps the small `.dvc` files that point to it.

- `raw/`: the datasets as we downloaded them.
- `prepared/`: the data after the `prepare` stage, ready for training.
