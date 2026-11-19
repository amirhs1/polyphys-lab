# TransFociCyl

A ring of small and large monomers among crowders in a cylinder that is
periodic along its axis.

## Paper

A. Sadeghi, C. Hyeon, Y. Jung, and B.-Y. Ha, "Compaction and clustering
of a heterogeneous polymer by biomolecular crowding," J. Chem. Phys. 161,
184904 (2024), <https://doi.org/10.1063/5.0226892>. Its simulations in a
cylinder are the runs of this folder.

## Parts

| Part                | Holds                                                     | State           |
| ------------------- | --------------------------------------------------------- | --------------- |
| `python/`           | `parser.py` (the `TransFociCyl` parser), `spec.py` (`SPEC`, `PROBE`, `ANALYSIS`), `tests/` | written         |
| `lammps/wca/`, `lammps/wca_short_equilibration/` | the LAMMPS inputs of the runs and their `study.conf`, one folder per variant | written |
| `lammps/start/`     | the start configuration, and the relaxed chain that some runs share with the input that makes it | written |
| `slurm/`            | the wrappers that call `pipeline/`                        | not written yet |
| `notebooks/`        | the notebooks                                             | not written yet |
| `runs/manifest.csv` | one row per run: its variant, run name, state point, replicate, seed, neighbor style and skin, relaxation length, first equilibration timestep, restart period, and processor grid | written |

The package imports as `polyphys_lab.trans_foci_cyl`:

```python
from polyphys_lab.trans_foci_cyl import TransFociCyl, SPEC, PROBE, ANALYSIS
```

## The runs

424 runs, in two variants. Both have the same pair potential, which
names them; they differ in the equilibration before production.

| Variant | `al` | $\phi_c$ | Replicates | Runs |
| --- | --- | --- | --- | --- |
| `wca` | 1, 3 | 0 to 0.44, 12 values | 8 | 192 |
| `wca` | 4, 6 | 0 to 0.44, 12 values | 4 | 96 |
| `wca_short_equilibration` | 5 | 0 to 0.44, 17 values | 8 | 136 |

`al` is the size of the large monomers, `sig2` in the inputs. $\phi_c$ is
the volume fraction of crowders as the parser gives it (`phi_bulk_c`):
the volume of the crowders divided by the volume open to their centers,
a cylinder of diameter $D - a_c$ and length $L$,

$$\phi_c = \frac{N_c (\pi / 6) a_c^3}{(\pi / 4) (D - a_c)^2 L}.$$

Here $N_c$ is the number of crowders (`n_crowd`), $a_c$ their size
(`sig3`), $D = 2R - 1$ the diameter of the cylinder as the parser reads
it (`dcyl`), with $R$ the `r` of the inputs, and $L = 2 l_z$ the period
along the axis, with $l_z$ the `lz` of the inputs. Every run has
$D = 20$.

## LAMMPS inputs

A ring of `n_small` small monomers (type 1, size 1, mass 1) and `n_big`
large monomers (type 2, size `sig2`, mass `mass2`) among `n_crowd`
crowders (type 3, size `sig3`, mass 1), in a cylinder of radius `r`
around the $z$ axis, periodic along $z$ with period 2 `lz`.
Lennard-Jones units; every particle feels a Langevin thermostat at
$T = 1$ with damping time 10.

```text
lammps/
  start/  foci-ring-ns400nl5.data minimized.initial.config.data minimize.lmp
  wca/                      minimize.lmp production.lmp study.conf
  wca_short_equilibration/  minimize.lmp production.lmp study.conf
```

| File | Does |
| --- | --- |
| `minimize.lmp` | relaxes the ring alone, with harmonic bonds and displacements capped, for `relax_steps` steps; writes `minimized.initial.config.data` |
| `production.lmp` | reads the relaxed chain, adds the crowders, equilibrates, then runs `n_loops` loops (20) of 5e6 steps |
| `study.conf` | the LAMMPS version and modules, the sweep (one row per state point and set of replicates), and the SLURM resources |
| `start/foci-ring-ns400nl5.data` | the start configuration: 405 atoms (400 small and 5 large monomers), 405 bonds closing a ring, 3 atom types, 2 bond types |
| `start/minimized.initial.config.data` | the relaxed chain that the crowded runs with `al` = 1 share |
| `start/minimize.lmp` | makes that relaxed chain from the start configuration; every value is written in it |

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
- **Wall.** `fix wall/region` with the `lj126` potential on the
  cylinder: the small monomers, the large monomers, and the crowders are
  repelled with sizes 1, $\sigma_{12}$, and $\sigma_{13}$ and strengths
  `epsilon_small`, `epsilon_big`, and 1, each cut at $2^{1/6}$ times its
  size. The chain's center of mass is kept at $z = 0$.
- **The variants.** Both relax the chain alone, then add the crowders
  and equilibrate. `wca` equilibrates in two stages, 1e6 steps with
  displacements capped and 4e6 plain steps; `wca_short_equilibration`
  runs the capped stage only.
- **The sweep rows.** Besides the state point, a row of `wca` sets the
  neighbor style (`bin` or `multi`) and skin, the relaxation length
  (`relax_steps`), the timestep of the capped stage (`eq1_dt`), and the
  restart period (`restart_every`); in `wca_short_equilibration` these
  are the same for every run and written in its inputs. A row of either
  variant sets the processor grid across the cylinder (`grid_x`,
  `grid_y`): 1 by 1 below 25,000 particles and 2 by 2 from there on. The
  neighbor settings and the grid change speed, not physics.
- **The shared chain.** The crowded runs with `al` = 1 do not relax
  their own chain: their rows have `relax_steps` `shared`, and each run
  folder gets `start/minimized.initial.config.data`, which
  `start/minimize.lmp` made once, in place of `minimize.lmp` and the
  start file.
- **One core for the relaxation.** `minimize.lmp` has no `processors`
  command.
- **No restart input.** No run of this study was finished from a restart
  file.

## Checked against the runs

With variables substituted and evaluated as LAMMPS does, the inputs were
compared, command for command and in order, with the commands that the
runs' logs echo.

- **`production.lmp`** gives the commands of the log of every one of the
  424 runs, from its manifest row. One name differs: the inputs here call
  the crowders' wall fix `F_wall_crowd`.
- **`minimize.lmp`** gives the commands of the relaxation logs of the
  nine runs whose relaxation log was at hand, one or two per `al`, but
  for one command: the runs' inputs had `processors 1 1 *`, which the
  inputs here leave out. The runs read the start file under the name
  `initial_config.data`; the inputs here read it under its own name. In
  the crowded runs with `al` = 3 and 5 the relaxation ran in the
  production job, on its cores; that arrangement was abandoned, since
  the relaxation needs only one core.
- **`start/minimize.lmp`** gives the commands of the log of the
  relaxation that made `start/minimized.initial.config.data`.
- **The `if` command** that sets up `multi` lists in `production.lmp`
  of `wca` is not in the runs' inputs, which each set one neighbor
  style. It compares two words, as the documentation of LAMMPS
  29 Sep 2021, the version of the runs, describes (`if` command).
- **The manifest.** Every value in `runs/manifest.csv` except
  `relax_steps` equals what the run's log echoes, for all 424 runs.
  `relax_steps` was read from the relaxation inputs.

Short runs of every input complete with LAMMPS 30 Sep 2026 - Update 1, a
stock build: `production.lmp` with `bin` and with `multi` lists, on one
and on four cores, and each `minimize.lmp` on one core. No input was run
with the LAMMPS version of the runs.
