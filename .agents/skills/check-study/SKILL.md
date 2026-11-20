---
name: check-study
description: Check the LAMMPS part of a study folder against its runs, and for the public, before it is committed here. Use this whenever a change adds or touches a study's lammps/ folder, a SWEEP table, runs/manifest.csv, or the "Checked against the runs" section of a study README, even for a one-line edit to an input. It gives the order of the checks and the form of the report. Not for a pipeline stage, a driver, or the notebooks.
---

# Check a study

A study's folder is the record of runs that are done and published, so
every change to it has to answer one question: do these files still give
what ran? This repository is public, so there is a second one: does
anything in them, or in the messages about them, name what is not public?

`projects/README.md` sets the form of each file, and `AGENTS.md`
("Templates, not run folders" and "A public repository") sets the rules.
Read both first. This skill gives the order of the checks and the form of
the report.

## What you need

- **The runs' logs and the inputs the runs used.** They are not in this
  repository. On a machine that has them, `AGENTS.local.md` says where
  they are and how they may be read; never name those places here.
  Without them, run checks 3 to 6 and report checks 1 and 2 as not run.
- **What a log gives.** A run's log is the file LAMMPS writes as it reads
  an input, together with its screen output. Take from it the echoed
  commands, the version line, the processor grid, and the warning and
  error lines. A log echoes each command with its variables substituted,
  so it shows the values a run had; a stored copy of an input may not.
- **Approval.** Adding a study or a variant, and changing a physical or
  numerical setting or a resource request, each need the maintainer's
  yes first (`AGENTS.md`, "Ask first").

## Before the checks

Answer these three; each one can stop the change.

1. **Is every variant published?** A variant folder here holds published
   runs only. Name no other variant, in a file or in a message.
2. **Is each variant one model?** A variant is a set of runs with the
   same potential, the same protocol, and the same LAMMPS build where the
   build changes the model. What differs from run to run inside one (the
   neighbor style, the skin, a relaxation length, a stage's timestep, the
   restart period, the processor grid) is a column of `SWEEP`. If the
   change finds or makes a difference in a physical or numerical setting,
   list it for the maintainer, who decides whether it is a variant, a
   column, or a mistake. That is a scientific judgment, and it is not
   yours to make.
3. **Does a file differ from the runs on purpose?** A default written
   out or left out, or a typo in a fix ID corrected, is listed in the
   study README, under "Checked against the runs", so a reader does not
   have to find it.

## The checks

Run them in this order: a manifest that disagrees with the logs makes
every later check meaningless.

1. **The manifest against the logs.** Every column of every row of
   `runs/manifest.csv` equals what the run's log echoes. Every log has a
   row and every row a log.
2. **The inputs against the runs.** Each input, with a run's row
   substituted and its `equal` variables evaluated and printed as LAMMPS
   prints them (`%.15g`), gives the commands the run's log echoes, in
   order.
3. **Planted faults.** In a copy outside the repository, plant one fault
   for each check and each test, and count how many are caught. A check
   that has never failed has not been shown to work. Never plant a fault
   in the working tree.
4. **Short local runs.** Every variant, with each neighbor style, each
   grid, and each restart input, with step counts shortened by `-var`
   (`projects/README.md`, "Run lengths") and few crowders. The local
   LAMMPS is usually not the version of the runs; say which it is.
   Nothing runs on a cluster.
5. **The scrub.** Search the diff, the commit message, and the pull
   request body for what `AGENTS.md`, "A public repository", forbids,
   with the patterns of `AGENTS.local.md` where that file lists some. A
   push cannot be taken back.
6. **The gate** of `AGENTS.md`, "Commands", and `shellcheck` on each
   `study.conf` by name: the gate's shell lint lists `*.sh` files only,
   so it does not reach one.

Run checks 1, 2, and 4 again after any change to an input or to a
`study.conf`. Report every check as a count, in this form:

```text
Manifest against logs: <n> of <n> rows equal
Inputs against runs:   production <n> of <n> exact; minimize <n> of <n>
  differs: <command>, in <k> runs: on purpose | open
Planted faults:        <caught> of <planted> caught
Short runs:            <n> cases complete; LAMMPS <local>, runs <theirs>
Scrub:                 <hits> hits read, <left> left
Gate:                  pytest <passed>/<skipped>/<xfailed>; flake8;
                       typecheck; ShellCheck
Not checked:           <what, and why>
```

## The README section

"Checked against the runs" says, for each input, what it was compared
with and in how many runs, what differs on purpose, and what was not
checked. From `projects/trans_foci_cyl/README.md`:

> **`production.lmp`** gives the commands of the log of every one of the
> 424 runs, from its manifest row. One name differs: the inputs here call
> the crowders' wall fix `F_wall_crowd`.

Not: "The inputs were checked against the runs." It gives no count and
hides the difference.

## Hand off

Leave every change unstaged, list the paths, and show the commit message
and the pull request body, as `AGENTS.md`, "Git", says. In the body, copy
the report into "Checks run", and tick a box under "Scientific
correctness" only for what a check showed.
