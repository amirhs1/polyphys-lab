# HnsCyl

A ring polymer with H-NS proteins among crowders in a cylinder that is periodic along its axis.

## Paper

Not recorded yet.

## Parts

| Part                | Holds                                                     | State           |
| ------------------- | --------------------------------------------------------- | --------------- |
| `python/`           | `parser.py` (the `HnsCyl` parser), `spec.py` (`SPEC`, `PROBE`, `ANALYSIS`), `tests/` | written         |
| `lammps/`           | one folder per variant, with its inputs and `study.conf`; the start configuration | not written yet |
| `slurm/`            | the wrappers that call `pipeline/`                        | not written yet |
| `notebooks/`        | the notebooks                                             | not written yet |
| `runs/manifest.csv` | one row per run                                           | not written yet |

The package imports as `polyphys_lab.hns_cyl`:

```python
from polyphys_lab.hns_cyl import HnsCyl, SPEC, PROBE, ANALYSIS
```
