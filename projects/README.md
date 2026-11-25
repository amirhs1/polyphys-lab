# projects

One folder per study. "Project" and "study" name the same thing.

```text
<study>/
  README.md         the paper, the runs, and the LAMMPS inputs
  python/           parser.py, spec.py, driver.py, corrections.py, tests/
  lammps/           one folder per variant, and start/
  slurm/            thin wrappers that call pipeline/
  notebooks/        the study's notebooks
  runs/manifest.csv one row per run
```

- `python/` installs as `polyphys_lab.<study>`; `pyproject.toml` lists it.
- `README.md` is the study's one README; it also says what the LAMMPS
  inputs simulate. "The study README" below sets its sections.
- `lammps/<variant>/` holds the inputs of one set of runs, each of them
  one whole file with no `include`, and the variant's `study.conf`: its
  LAMMPS version and modules, its sweep, and the resource table that the
  stages in `pipeline/` read. A study whose runs all share their physics
  and numerics has one variant.
- `lammps/start/` holds the start configuration, and the script that
  builds it where one exists.
- `runs/manifest.csv` lists every run of the study by variant and name.

`tests/test_layout.py` checks that every study folder has these parts.

| Folder            | Study          | Package                       |
| ----------------- | -------------- | ----------------------------- |
| `trans_foci_cyl/` | `TransFociCyl` | `polyphys_lab.trans_foci_cyl` |
| `trans_foci_cub/` | `TransFociCub` | `polyphys_lab.trans_foci_cub` |
| `hns_cub/`        | `HnsCub`       | `polyphys_lab.hns_cub`        |

`tests/test_studies.py`, at the repository root, checks every study's
specs against its parser and against the research code's registry.
`tests/test_templates.py`, beside it, checks the LAMMPS inputs, the
`study.conf` files, and the manifest of every study that has a variant
folder. A study's own `python/tests/test_templates.py` holds the checks
of its system: its run names against its parser, its start
configuration, and its resource table.

The private-data tests in each `python/tests/test_parser.py` run only
when `POLYPHYS_DATA_DIR` names a folder of processed artifacts, and are
skipped otherwise.

## The study README

A study's `README.md` says what no single file of the study says: what
spans its files, what spans its runs, and how the files relate to the
published runs. It has these sections, under these headings and in this
order:

| Heading | Says |
| --- | --- |
| `# <Study>` | the system, in one sentence |
| `## Paper` | the citation, and which of the paper's simulations are the runs here |
| `## Parts` | a table of the study's parts and their state, and how the package imports |
| `## The runs` | how many runs and variants there are; a table with one row per variant and group of state points; the definition of each symbol in the table |
| `## LAMMPS inputs` | the system and its units, in one paragraph; the tree of `lammps/`; a table of what each file does; each potential, in a sentence or two with its formula; what differs between the variants and between the sweep rows; last, a list of where the inputs differ from what ran |

A study whose LAMMPS inputs are not written yet has the first three.
`tests/test_layout.py` checks the headings and their order.

The README leaves out:

- **Why the study was done and what it found.** The paper says both.
- **What an input does, step by step.** The comments in the input say
  it; the README gives a sentence or two.
- **What the studies share**, which is in the next section.

## What the studies' inputs share

Each input is one whole file with no `include`. A value that is the same
for every run of a variant is written in its inputs; only a run's sweep
row comes from `study.conf`. The top of each input lists the variables
that it reads from the sweep row.

### The run folder

The sweep generator makes one folder per run, named after the run
(`runs/manifest.csv`, column `run_name`), with:

- `input.lmp`: the variant's `production.lmp` with the run's sweep row
  written as `variable` lines at its top. The production loop jumps back
  into the file by this name.
- `minimize_initial_config.lmp`: the variant's `minimize.lmp`, the same
  way.
- the start file, under its own name.
- an empty `restarts/` folder.

A study README says where its run folders differ.

### Run lengths

Every step count in an input is an `index` variable whose value is the
production one. LAMMPS never redefines an `index` variable, so the first
definition wins: the value on the command line (LAMMPS documentation,
command-line option `-var`), then the one the generator writes at the top
of the input from the sweep row, then the input's own. For example:

    lmp -in input.lmp -var eq1_steps 2000 -var n_loops 10 -var loop_steps 1000

The production loop pads `j` to the width of `n_loops`: with 20 loops the
all-particle files are numbered `j01`, `j02`, ..., `j20`. Each input
defines its step counts near its top, under "Run lengths" or "Run
length".

### Restarts

A restart file holds the atoms, the box, the groups, the pair style with
its coefficients and `pair_modify` settings, the `comm_modify` settings,
and the timestep size, but not the neighbor settings or the fixes
(LAMMPS documentation, `read_restart`). So a restart input sets the
neighbor lists and the fixes again and takes the potential from the
restart file.

## Math in a README

- A symbol or a formula is inline math, `$...$`. A definition that
  deserves a line of its own is a display equation, `$$...$$`, in a
  paragraph of its own: never inside a list item or a table cell.
- Every symbol is defined where it first appears and tied to its name in
  the inputs: for example, $a_c$ is the crowders' size (`sig3`).
- Names of files, variables, and commands stay in backticks, and a step
  count is written as the inputs write it, such as `1e6`.
- GitHub renders the math. After changing a formula, look at the page on
  GitHub.
