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

A ring of `n_small` small monomers (size 1, mass 1) and `n_big` large
monomers (size `sig2`, mass `mass2`) among `n_crowd` crowders (size `sig3`,
mass 1), in a periodic cube of edge `2 l`. Lennard-Jones units; every
particle feels a Langevin thermostat at $T = 1$ with damping time 10.

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

Each input is one whole file with no `include`. A value that is the same
for every run is written in the inputs; only the run's sweep row comes
from `study.conf`.

- **Pair potential.** `lj/cut` with
  $U_{ij}(r) = 4 \epsilon [(\sigma_{ij} / r)^{12} - (\sigma_{ij} / r)^{6}]$
  for two particles of types $i$ and $j$ at distance $r$, where
  $\sigma_{ij} = (\sigma_i + \sigma_j) / 2$ is the mean of their sizes
  and $\epsilon = 1$. Type 1 is a small monomer, type 2 a large monomer,
  and type 3 a crowder. The potential is cut at $2^{1/6} \sigma_{ij}$ and
  not shifted. The cutoff at the minimum of $U_{ij}$ leaves only the
  repulsive part, so the forces are those of the Weeks-Chandler-Andersen
  (WCA) potential. Without the shift, the reported energies are lower
  than the WCA energies by $\epsilon$ per pair inside the cutoff; the
  forces are the same.
- **Relaxation and equilibration.** The chain is relaxed alone, in the
  empty cube of the run, before the crowders are added. With the
  crowders and FENE bonds, the equilibration is 1e6 steps with
  displacements capped at 0.01 (dt 0.02), then 2e6 plain steps (dt 0.01).
- **Neighbor lists.** The neighbor style and skin change speed, not
  physics; each sweep row names its own (`SWEEP` in `study.conf`, columns
  `neigh_style` and `neigh_skin`). The inputs set up `multi` lists with
  an `if` command that compares two words, which the documentation of
  LAMMPS 29 Sep 2021, the version of the runs, describes (`if` command).
  `minimize.lmp` always uses `bin` lists with a skin of 1, and runs on
  one core. The length of the harmonic relaxation is also per sweep row
  (`relax_steps`).

### The run folder

The sweep generator makes one folder per run, named after the run
(`runs/manifest.csv`, column `run_name`), with:

- `input.lmp`: `production.lmp` with the run's sweep row written as
  `variable` lines at its top. The production loop jumps back into the
  file by this name.
- `minimize_initial_config.lmp`: `minimize.lmp`, the same way.
- the start file, under its own name.
- an empty `restarts/` folder.

The variables each input reads from the sweep row are listed at its top.

### Run lengths

Every step count is an `index` variable whose value is the production
one: `relax_steps` in `minimize.lmp`; `eq1_steps`, `eq2_steps`, and
`n_loops` in `production.lmp`; `loop_steps` and `restart_every` in
`production.lmp` and `restart.lmp`. LAMMPS never redefines an `index`
variable, so the first definition wins: the value on the command line
(LAMMPS documentation, command-line option `-var`), then the one the
generator writes at the top of the input (`relax_steps` of the sweep
row), then the input's own. For example:

    lmp -in input.lmp -var eq1_steps 2000 -var n_loops 10 -var loop_steps 1000

The loop pads `j` to the width of `n_loops`: with 20 loops the
all-particle files are numbered `j01`, `j02`, ..., `j20`.

### Restarts

A restart file holds the atoms, the box, the groups, the pair style with
its coefficients and `pair_modify` settings, the `comm_modify` settings,
and the timestep size, but not the neighbor settings or the fixes
(LAMMPS documentation, `read_restart`). So `restart.lmp` sets the
neighbor lists and the fixes again and takes the potential from the
restart file.

### Checked against the runs

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

Every value in `runs/manifest.csv` except `relax_steps` equals what the
run's log echoes, for all 384 runs. `relax_steps` was read from the
relaxation inputs of the 18 runs.

Short runs with `bin` and with `multi` lists, and of `restart.lmp`,
complete with LAMMPS 30 Sep 2026, a stock build. No input was run with
the LAMMPS version of the runs.
