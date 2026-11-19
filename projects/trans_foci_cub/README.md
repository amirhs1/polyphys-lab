# TransFociCub

A ring of small and large monomers among crowders in a periodic cube.

## Paper

A. Sadeghi, C. Hyeon, Y. Jung, and B.-Y. Ha, "Compaction and clustering
of a heterogeneous polymer by biomolecular crowding," J. Chem. Phys. 161,
184904 (2024), <https://doi.org/10.1063/5.0226892>. Its simulations in
free space are the runs of this folder.

## Parts

| Part                | Holds                                                     | State           |
| ------------------- | --------------------------------------------------------- | --------------- |
| `python/`           | `parser.py` (the `TransFociCub` parser), `spec.py` (`SPEC`, `PROBE`, `ANALYSIS`), `tests/` | written         |
| `lammps/wca/`       | the LAMMPS inputs of the runs and their `study.conf`      | written         |
| `lammps/start/`     | the start configuration                                   | written         |
| `slurm/`            | the wrappers that call `pipeline/`                        | not written yet |
| `notebooks/`        | the notebooks                                             | not written yet |
| `runs/manifest.csv` | one row per run: its variant, run name, state point, replicate, seed, neighbor style and skin, and relaxation length | written |

The package imports as `polyphys_lab.trans_foci_cub`:

```python
from polyphys_lab.trans_foci_cub import TransFociCub, SPEC, PROBE, ANALYSIS
```

## The runs

384 runs, in one variant, `wca`, named after its pair potential.

| `al` | $\phi_c$ | Replicates | Runs |
| --- | --- | --- | --- |
| 1, 3, 5 | 0 to 0.4, 12 values | 8 | 288 |
| 4, 6 | 0 to 0.4, 12 values | 4 | 96 |

`al` is the size of the large monomers, `sig2` in the inputs. $\phi_c$ is
the nominal volume fraction of crowders, the volume of the crowders
divided by the volume of the cube,

$$\phi_c = \frac{N_c (\pi / 6) a_c^3}{(2 l)^3}.$$

Here $N_c$ is the number of crowders (`n_crowd`), $a_c$ their size
(`sig3`), and $2 l$ the edge of the cube, with $l$ the `l` of the
inputs.

## LAMMPS inputs

A ring of `n_small` small monomers (type 1, size 1, mass 1) and `n_big`
large monomers (type 2, size `sig2`, mass `mass2`) among `n_crowd`
crowders (type 3, size `sig3`, mass 1), in a periodic cube of edge
2 `l`. Lennard-Jones units; every particle feels a Langevin thermostat
at $T = 1$ with damping time 10.

```text
lammps/
  start/foci-ring-ns400nl5.data
  wca/  minimize.lmp production.lmp restart.lmp study.conf
```

| File | Does |
| --- | --- |
| `minimize.lmp` | relaxes the ring alone, with harmonic bonds and displacements capped, for `relax_steps` steps (1e5 or 2e5); writes `minimized.initial.config.data` |
| `production.lmp` | reads the chain, adds the crowders, equilibrates for 3e6 steps, then runs `n_loops` loops (20) of 5e6 steps |
| `restart.lmp` | finishes an interrupted production run from a restart file |
| `study.conf` | the LAMMPS version and modules, the sweep (one row per state point and set of replicates), and the SLURM resources |
| `start/foci-ring-ns400nl5.data` | the start configuration: 405 atoms (400 small and 5 large monomers), 405 bonds closing a ring, 3 atom types, 2 bond types |

What the inputs of every study share is in
[`projects/README.md`](../README.md): one whole file per input, the run
folder, how to shorten a run, and what a restart file holds.

- **Pair potential.** `lj/cut` with
  $U_{ij}(r) = 4 \epsilon [(\sigma_{ij} / r)^{12} - (\sigma_{ij} / r)^{6}]$
  for particles of types $i$ and $j$ at distance $r$, with $\epsilon = 1$
  and $\sigma_{ij} = (\sigma_i + \sigma_j) / 2$ the mean of their sizes.
  It is cut at its minimum, $2^{1/6} \sigma_{ij}$, and not shifted: the
  forces are those of the Weeks-Chandler-Andersen (WCA) potential, and
  the reported energies are lower than the WCA energies by $\epsilon$
  per pair inside the cutoff.
- **The sweep rows.** Besides the state point, a row sets the neighbor
  style and skin (`neigh_style`, `neigh_skin`), which change speed, not
  physics, and the length of the relaxation (`relax_steps`).
- **One core for the relaxation.** `minimize.lmp` runs on one core, with
  `bin` neighbor lists and a skin of 1 in every run.

## Checked against the runs

With variables substituted, the inputs were compared, command for
command, with the inputs of 18 runs.

- **`production.lmp`** gives 14 of the inputs exactly; the other four
  write a restart file every 5e6 steps instead of 1e6.
- **`minimize.lmp`** gives 14 exactly; the other four use other neighbor
  settings (`multi` lists, or a skin of 0.3).
- **The start file**: the runs read it under the name
  `initial_config.data`; the inputs here read it under its own name.
- **`restart.lmp`**: not matched yet. The four restart inputs compared
  set the loop count and the last loop's length as numbers, and three of
  them set no thermo output period.
- **The `if` command** that sets up `multi` lists is not in the runs'
  inputs, which each set one neighbor style. It compares two words, as
  the documentation of LAMMPS 29 Sep 2021, the version of the runs,
  describes (`if` command).

Every value in `runs/manifest.csv` except `relax_steps` equals what the
run's log echoes, for all 384 runs. `relax_steps` was read from the
relaxation inputs of the 18 runs.

Short runs with `bin` and with `multi` lists, and of `restart.lmp`,
complete with LAMMPS 30 Sep 2026, a stock build. No input was run with
the LAMMPS version of the runs.
