# HnsCub

A ring polymer with H-NS proteins among crowders in a periodic cube.

## Paper

Y. Jung, A. Sadeghi, and B.-Y. Ha, "Modeling the compaction of bacterial
chromosomes by biomolecular crowding and the cross-linking protein H-NS,"
Sci. Rep. 14, 139 (2024), <https://doi.org/10.1038/s41598-023-50355-2>.
Its simulations are the runs of this folder.

## Parts

| Part                | Holds                                                     | State           |
| ------------------- | --------------------------------------------------------- | --------------- |
| `python/`           | `parser.py` (the `HnsCub` parser), `spec.py` (`SPEC`, `PROBE`, `ANALYSIS`), `tests/` | written         |
| `lammps/wca_patch/` | the LAMMPS inputs of the runs and their `study.conf` | written |
| `lammps/start/`     | the start configuration and the H-NS molecule | written |
| `slurm/`            | the wrappers that call `pipeline/`                        | not written yet |
| `notebooks/`        | the notebooks                                             | not written yet |
| `runs/manifest.csv` | one row per run: its variant, run name, state point, replicate, seed, and neighbor style | written |

The package imports as `polyphys_lab.hns_cub`:

```python
from polyphys_lab.hns_cub import HnsCub, SPEC, PROBE, ANALYSIS
```

## The runs

560 runs, in one variant. The pair potential names it: every pair is
the Weeks-Chandler-Andersen (WCA) potential but the DNA monomer and H-NS
pole pair, the patch, which attracts.

| Variant | $n_h$ | $\epsilon_{hc}$ | $\phi_c$ | Replicates | Runs |
| --- | --- | --- | --- | --- | --- |
| `wca_patch` | 0, 4, 8, 12, 16, 20, 30 | 0, 1 | 0, and 0.08 to 0.40 in steps of 0.04 | 4 | 560 |

$n_h$ is the number of H-NS proteins (`n_hns` in the inputs) and
$\epsilon_{hc}$ the strength of the pair potential between an H-NS core
and a crowder (`eps34`). $\phi_c$ is the volume fraction of crowders as
the parser gives it (`phi_bulk_c`), the volume of the crowders divided
by that of the cube,

$$\phi_c = \frac{N_c (\pi / 6) a_c^3}{L^3}.$$

Here $N_c$ is the number of crowders (`n_crowd`), $a_c = 2$ their size
(`sig4`), and $L = 2 l = 50$ the side of the cube, with $l$ the `l` of
the inputs. Every run has a ring of $N = 200$ monomers (`N`) with
bending rigidity $k_b = 2$ (`kBend11`).

## LAMMPS inputs

A ring of `N` DNA monomers (type 1, size 1, mass 1) with `n_hns` H-NS
proteins among `n_crowd` crowders (type 4, size `sig4`, mass
`sig4`$^3$), in a periodic cube of side 2 `l`. An H-NS protein is a core
(type 3, size 1, mass 1) with two poles (type 2, size 0.178, mass 1) on
an axis through it, each 0.4 from its center. Lennard-Jones units; every
particle feels a Langevin thermostat at $T = 1$, and the ring's center
of mass is kept at the origin.

```text
lammps/
  start/      dna.data hns.mol
  wca_patch/  minimize.lmp production.lmp study.conf
```

| File | Does |
| --- | --- |
| `start/dna.data` | the start configuration: one ring of 200 monomers, with 200 bonds and 200 angles, and one atom, bond, and angle type |
| `start/hns.mol` | the H-NS protein as a LAMMPS molecule: a core between two poles, two bonds, one angle |
| `wca_patch/minimize.lmp` | relaxes the ring alone in the cube of the run, 1e5 steps with displacements capped and 5e6 plain steps; writes `minimized.dna.data`. Every run runs it first, with its own seed |
| `wca_patch/production.lmp` | reads the relaxed ring, adds the proteins and the crowders, equilibrates for 2e5 steps, then runs `n_loops` loops (10) of 1e7 steps |
| `wca_patch/study.conf` | the LAMMPS version and modules, the sweep (one row per state point), and the SLURM resources |

What the inputs of every study share is in
[`projects/README.md`](../README.md): one whole file per
input, the run folder, how to shorten a run, and what a restart file
holds. Here the run folder also gets `start/hns.mol`, beside the start
file.

- **Pair potential.** `lj/cut` with
  $U_{ij}(r) = 4 \epsilon_{ij} [(\sigma_{ij} / r)^{12} - (\sigma_{ij} / r)^{6}]$
  for particles of types $i$ and $j$ at distance $r$, shifted to zero at
  its cutoff $r_{c,ij}$ (`pair_modify shift yes`). $\sigma_{ij}$ is the
  mean of the two sizes, and $r_{c,ij} = 2^{1/6} \sigma_{ij}$, written
  1.122462 $\sigma_{ij}$, the minimum of the potential, so these pairs
  are WCA pairs with $\epsilon_{ij} = 1$. Three pairs differ:
  - **The patch**, monomer and pole: $\sigma_{12} = 0.535$, cut at
    $r_{c,12} = 0.685$, beyond the minimum, so it attracts.
    $\epsilon_{12} = 1$ in the equilibration and 29 in production.
  - **Core and crowder:** $\epsilon_{34}$ is the row's `eps34`, 0 or 1.
    With 0 the cores and the crowders do not interact.
  - **Pole and pole:** $\sigma_{22} = 0.178$, cut at 0.2, just beyond
    the minimum, 0.1998.

  Two pairs have no `pair_coeff`, pole and core and pole and crowder.
  LAMMPS mixes their coefficients from those of the like pairs, by the
  geometric rule, its default (LAMMPS documentation, `pair_modify`, and
  `pair_style lj/cut`, "Mixing"): $\epsilon = 1$,
  $\sigma = (\sigma_{ii} \sigma_{jj})^{1/2}$, and the cutoff the
  geometric mean of the two cutoffs, about $2^{1/6} \sigma$ for both.
- **Bonds.** Along the ring, FENE,
  $U(r) = -\frac{1}{2} K R_0^2 \ln[1 - (r / R_0)^2]$ plus the WCA
  potential of the bonded pair, with $K = 30$ and $R_0 = 1.5$ (LAMMPS
  documentation, `bond_style fene`). Between a pole and its core, a
  harmonic bond, $U(r) = K (r - r_0)^2$ with $K = 120$ and $r_0 = 0.4$
  (`bond_style harmonic`). `special_bonds fene` turns the pair
  potential off between bonded atoms.
- **Angles.** `angle_style harmonic`,
  $U(\theta) = K (\theta - \theta_0)^2$ with $\theta_0 = 180°$ (LAMMPS
  documentation, `angle_style harmonic`). Along the ring $K = k_b / 2$:
  LAMMPS writes the potential without the factor $1/2$, so `kBend11` is
  halved (`kBend11Lammps`). The pole-core-pole
  angle has $K = 50$.
- **Thermostat.** `fix langevin` with damping time 1; for the crowders
  the damping time is multiplied by `sig4`$^3$ / `sig4`, 4 (keyword
  `scale`; LAMMPS documentation, `fix langevin`).
- **Protocol.** `minimize.lmp` relaxes the ring alone, with bin
  lists and a skin of 2: 1e5 steps of `nve/limit 0.01` and 5e6 of
  `nve`, at dt 0.01. `production.lmp` then places the proteins, at
  random orientations, and the crowders at random in the cube, and runs
  2e5 steps of `nve/limit 0.01` at dt 0.01 with $\epsilon_{12} = 1$,
  then 10 loops of 1e7 steps of `nve` at dt 0.005 with
  $\epsilon_{12} = 29$. The DNA and the proteins are written every 5000
  steps, all particles every 10000, and a restart file every 1e5.
- **The sweep rows.** Besides the state point, a row sets the neighbor
  style of production: `bin` for the runs without crowders, `multi` for
  the others, with two collections, the DNA and H-NS types and the
  crowders. The skin is 0.3 in both. The neighbor style changes speed,
  not physics.
- **Grids.** No input sets a processor grid. The runs without crowders
  ran on one core; the crowded ones on four, where LAMMPS chose
  1 by 2 by 2. The relaxation runs on one core.
- **The start file.** One bond of `dna.data` is 1.5035 long, beyond
  $R_0$; LAMMPS warns "FENE bond too long" for it and goes on.
- **No restart input.** No run of this study was finished from a
  restart file.

Where the inputs differ from what ran:

- **Run lengths.** The step counts, the loop count, and the restart
  period are `index` variables; the runs' inputs wrote the numbers.
- **The run's name.** `production.lmp` builds `simname` from the row;
  the runs' generator wrote it at the top of the input.
- **The neighbor lists.** The runs' inputs each set one style. Here the
  row names it, an `if` command sets up `multi` lists, and `gRcut1` and
  `gRcut4` are defined for every run, before the
  `neigh_modify collection/type` line that in the runs came first. The
  `if` compares two words, as the documentation of LAMMPS 29 Sep 2021,
  the version of the runs, describes (`if` command).
- **The header of the relaxation.** The generator writes the whole row
  at the top of each input; the runs' relaxation inputs had only
  `kBend11`, `l`, `i`, and `randseed`.
- **The start file's title.** The first line of `start/dna.data`, which
  LAMMPS always skips (LAMMPS documentation, `read_data`), is not the
  runs' copy's.
