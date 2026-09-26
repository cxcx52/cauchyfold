# Official estimator records

`raw/` holds the original per-task JSON outputs without alteration. There are 40 finite records: classical and quantum cost models for each of 20 matrices. `inputs/` holds the exact inputs. The ordinary reproduction command regenerates inputs and validates these records without executing attacks.

To rerun attacks separately, enter `reference/explicit-projection`, complete the data reproduction, then install SageMath and the dependencies reported in `environment.json`. Obtain the unmodified upstream source:

```sh
git clone https://github.com/malb/lattice-estimator vendor/lattice-estimator
git -C vendor/lattice-estimator checkout --detach 53da5982597709ba0fdf94ea37a84d822310fd84
sage -python estimator/reestimate.py --output build-estimator
```

This opt-in command creates a new directory and runs all 40 attacks. It never changes `raw/` or the paper results. The runner checks the upstream commit and clean working tree, records per-task outputs and estimator wall/CPU/RSS measurements, and retains errors as errors. These measurements concern the estimator, not the folding protocol. The runner uses a 3600-second per-task limit; timeouts remain UNKNOWN_TIMEOUT.

The quantum MATZOV setting uses the upstream depth-times-width nearest-neighbor convention. A finite estimate with block size above 1024 is marked as extrapolated. The Euclidean SIS branch does not report attack memory or success probability; missing quantities are not filled from a different norm model.
