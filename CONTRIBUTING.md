# Contributing to polyphys-lab

## Reporting a problem

Bug reports, feature requests, and questions are welcome via
[issues](https://github.com/amirhs1/polyphys-lab/issues); each has a template.
Report a suspected vulnerability privately instead, as
[`SECURITY.md`](SECURITY.md) describes; do not open a public issue for it.

This repository is public, and an issue, a comment, or a pushed commit cannot
be taken back. Attach no private or unpublished data, and name no cluster
account, address, user, host, or path.

## Development setup

```bash
git clone https://github.com/amirhs1/polyphys-lab.git
cd polyphys-lab
python -m pip install -e ".[dev]"
```

Each study's `python/` folder is then importable as `polyphys_lab.<study>`.

### Checklist for each clone

- [ ] `git config core.hooksPath .githooks` has been run, which turns on the
      `commit-msg` hook.
- [ ] `git config fetch.prune true` has been run.
- [ ] `git config commit.template .gitmessage` has been run, for commits
      written in an editor.

## Checks

Run these from the repository root before opening a pull request:

| Check       | Command                                              |
| ----------- | ---------------------------------------------------- |
| All tests   | `python -m pytest -rf`                               |
| One test    | `python -m pytest tests/test_layout.py::<test name>` |
| Lint Python | `python -m flake8 polyphys_lab projects tests tools` |
| Type-check  | `python tools/typecheck.py`                          |
| Lint shell  | `git ls-files '*.sh' \| xargs shellcheck`            |

CI runs the shell lint, the Python lint, the type-check, and the tests on
every pull request, and a further job that runs the tests against PolyPhys
`main` without blocking a merge.

## Submitting a pull request

- Branch from `main`, and name the branch and the pull request title as
  "Names" below sets them.
- `main` is protected: a change reaches it only through a pull request, with
  "Lint shell" and "Lint and test Python" passing on a branch that is up to
  date with `main`.
- Pull requests merge with a merge commit, so each commit lands on `main`
  unchanged; keep every commit coherent.
- Fill in every section of the pull request template; it is the pull
  request's full report.
- Follow [`projects/README.md`](projects/README.md) for a study's folder and
  its README.

## AI-assisted contributions

AI tools are welcome. Read the [AI policy](AI-POLICY.md) before opening a pull
request. The rules most often missed:

- Understand, and be able to explain, everything you submit.
- Say in the pull request which AI tools you used and for what, with
  `not recorded` for a model you cannot name.
- Write issues, pull request descriptions, and replies in your own words, or
  let an AI agent write them. Then you answer for every word, and its text
  ends with its `Assisted-by:` trailer.
- For text you write yourself, the pull-request statement is enough; the
  commit trailers are the maintainers' record, and optional for you.

Pull requests that don't follow the policy may be closed without review.

### Checking an AI tool's commits

- [ ] A test commit made by each tool in use ends with one trailer block that
      includes `Assisted-by:` and no AI `Co-authored-by:`
      (`git log -1 --format=%B`).

### Repository checks for the maintainer

- [ ] `.claude/settings.json` is committed with the attribution block.
- [ ] `.gitmessage` is committed.
- [ ] `.gitignore` has the agent-files block:

  ```gitignore
  # Agent files: local only
  CLAUDE.local.md
  AGENTS.local.md
  .claude/settings.local.json
  .claude/worktrees/
  .claude/.cc-writes/
  ```

## Names

Use a type to describe the kind of change and an area to identify the affected
part of the repository. A commit's scope is its area, and the labels are
`type:<type>` and `area:<area>`.

```text
types: feat fix docs test refactor chore question
areas: projects trans_foci_cub trans_foci_cyl hns_cub hns_cyl pipeline notebooks packaging guide ci agents deps
```

| Type       | Means                                                                                             |
| ---------- | ------------------------------------------------------------------------------------------------- |
| `feat`     | Adds a study's records, a pipeline stage, or a capability of the tooling.                         |
| `fix`      | Corrects something that was wrong.                                                                |
| `docs`     | Changes documentation only, in any area: a README, a comment in an input, a docstring.            |
| `test`     | Adds or corrects tests without changing what they test.                                           |
| `refactor` | Restructures files or code without changing what they do or say.                                  |
| `chore`    | Maintenance that fits no other type, such as a dependency bump.                                   |
| `question` | Asks for information instead of proposing a change; an issue type only, never a branch or commit. |

| Area                                                     | Covers                                                                                                                            |
| -------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `projects`                                               | `projects/README.md`, the cross-study tests in `tests/`, and a change that spans studies                                          |
| `trans_foci_cub`, `trans_foci_cyl`, `hns_cub`, `hns_cyl` | That study's folder under `projects/`                                                                                             |
| `pipeline`                                               | `pipeline/`, `config/`                                                                                                            |
| `notebooks`                                              | `notebooks/`                                                                                                                      |
| `packaging`                                              | `pyproject.toml`, `polyphys_lab/`, `tools/`, `LICENSE`                                                                            |
| `guide`                                                  | `README.md`, `CONTRIBUTING.md`, `SECURITY.md`, `.github/ISSUE_TEMPLATE/`                                                          |
| `ci`                                                     | `.github/workflows/`                                                                                                              |
| `agents`                                                 | `AGENTS.md`, `CLAUDE.md`, `AI-POLICY.md`, `.agents/`, `.claude/`, `.githooks/`, `.gitmessage`, `.github/pull_request_template.md` |
| `deps`                                                   | Dependency versions: the lists in `pyproject.toml` and the action versions in `.github/workflows/`                                |

A new study adds its folder name to the areas. A change that only moves a
dependency version takes the area `deps`, not `packaging` or `ci`.

| Name                          | Form                                   |
| ----------------------------- | -------------------------------------- |
| Branch                        | `<type>/<short-name>`                  |
| Commit and pull request title | `<type>(<area>): <imperative summary>` |
| Issue title                   | `[<area>] <imperative summary>`        |
| Epic                          | A parent issue, titled as an issue     |

Labels combine: one `type:` plus one or more `area:`. There are no
combination labels. Status and priority are not labels. The repository has no
releases yet, so it has no milestone, tag, or release names.

Issue templates set a default type: `type:fix` for a bug report, `type:feat`
for a feature request, and `type:question` for a question.

### Where these names are used

- `.gitmessage`
- `.github/pull_request_template.md`
- `.github/ISSUE_TEMPLATE/*`
- `.agents/skills/create-branch/SKILL.md`,
  `.agents/skills/open-issue/SKILL.md`,
  `.agents/skills/open-pull-request/SKILL.md`,
  `.agents/skills/write-commit/SKILL.md`
- `AGENTS.md`, "Git"

Each of these cites this section.
