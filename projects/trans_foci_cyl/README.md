# TransFociCyl

A ring of small and large monomers among crowders in a cylinder that is periodic along its axis.

## Paper

Not recorded yet.

## Parts

| Part                | Holds                                                     | State           |
| ------------------- | --------------------------------------------------------- | --------------- |
| `python/`           | `parser.py` (the `TransFociCyl` parser), `spec.py` (`SPEC`, `PROBE`, `ANALYSIS`), `tests/` | written         |
| `lammps/`           | input templates, restart inputs, start configuration      | not written yet |
| `slurm/`            | `study.conf` and the wrappers that call `pipeline/`       | not written yet |
| `notebooks/`        | the notebooks                                             | not written yet |
| `runs/manifest.csv` | one row per run name                                      | not written yet |

The package imports as `polyphys_lab.trans_foci_cyl`:

```python
from polyphys_lab.trans_foci_cyl import TransFociCyl, SPEC, PROBE, ANALYSIS
```
