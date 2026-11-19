<!--
This is the pull request's full report. Keep every section, in this order,
then the trailer block; a section that does not apply says `None`.

This repository is public: name no unpublished study, no private repository,
no account, address, user, host, or absolute path, and no local environment.
-->

<!-- Title: as CONTRIBUTING.md, "Names", sets it. -->

## Summary

The outcome, in one or two sentences: what changed and why. The reason comes
from a person or an outside report, not from an AI tool; an agent gives it
only as supplied.

## Related issues

`Closes #n` for each issue this pull request completes, `Refs #n` for one it
covers in part, or `None`.

## Problem

What was wrong or missing, with evidence: an issue, a failing check, or an
observed output.

## What changed

How the change was made: files as `path:line`, plus reasoning the diff does
not show. Leave the outcome to the summary.

## Checks run

Each check actually run, as `command → result`, and any human review or
independent reference used to judge correctness. Then a `Not verified:` line
for anything not checked, and why.

- [ ] `python -m pytest -rf`
- [ ] `python -m flake8 polyphys_lab projects tests tools`
- [ ] `python tools/typecheck.py`
- [ ] `git ls-files '*.sh' | xargs shellcheck`, if a shell script or a `study.conf` changed

## Scientific correctness

- [ ] No physical or numerical setting of an input changed, or the change is explained above with its scientific basis
- [ ] The inputs still give the commands of the published runs, or the difference is stated in the study's README, "Checked against the runs"
- [ ] Nothing here was run on a cluster, or what was run is stated above

## Decisions and risks

Trade-offs: the choices made and the alternatives rejected. Then answer:

- How would the change be undone, and what would undoing it cost?
- Does it change an input, a `study.conf`, a manifest, or a file name that a run or a stage reads?
- Does it change any numerical result, and which?

## Notes for review

Where the reviewer should look: what needs line-by-line review, and any
uncertainty, limitation, or follow-up.

<!--
AI assistance: say in this pull request which AI tools you used and for what;
do not guess a model, write `not recorded`. If you wrote this body yourself,
that statement is enough. If an AI agent wrote it, end it with one trailer
block, after a blank line: one
`Assisted-by: <tool>, <model id or not recorded> (<role>)` line for each AI
tool used, then `Checks-run: <check actually run> — <observed result>` for
each check it ran. With no AI tool, leave the block out. Do not include
prompts, secrets, or personal data.
Responsibility for the contribution remains with the contributor; see
`AI-POLICY.md`.
-->
