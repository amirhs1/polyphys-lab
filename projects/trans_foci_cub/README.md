# TransFociCub

A ring of small and large monomers among crowders in a periodic cube.

## Paper

Not recorded yet.

## Parts

| Part                | Holds                                                     | State           |
| ------------------- | --------------------------------------------------------- | --------------- |
| `python/`           | `parser.py` (the `TransFociCub` parser), `spec.py` (`SPEC`, `PROBE`, `ANALYSIS`), `tests/` | written         |
| `lammps/`           | input templates, restart inputs, start configuration      | not written yet |
| `slurm/`            | `study.conf` and the wrappers that call `pipeline/`       | not written yet |
| `notebooks/`        | the notebooks                                             | not written yet |
| `runs/manifest.csv` | one row per run name                                      | not written yet |

The package imports as `polyphys_lab.trans_foci_cub`:

```python
from polyphys_lab.trans_foci_cub import TransFociCub, SPEC, PROBE, ANALYSIS
```
