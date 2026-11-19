---
name: write-test
description: Write or change a test against approved acceptance criteria, with pytest. Use when a change adds or changes a test; not for only running the suite.
---

# Write a test

1. Start from the approved acceptance criteria or test-case list.
2. Name the test after the behavior it protects: the claim that is false if
   it fails.
3. Test one behavior.
4. Take each expected value from a source independent of the code under
   test. A consistency check between files of the repository has no
   reference value; say so in the module docstring.
5. Show that each new test can fail, for a bug before the fix, and say so in
   the pull request. For a check of the repository's files, plant the fault
   in a copy outside the repository, never in the working tree.
6. Never weaken an expectation or paste observed output to make a test pass;
   report the failure.
7. Leave other files' tests as they are; when rewriting a file, carry forward
   every test that still states a valid contract.
8. Run the changed test first, then the full suite.

## pytest here

- **Where tests live.** A check that holds for every study goes in `tests/`
  at the repository root and runs once per study, variant, or input, through
  `@pytest.mark.parametrize` with readable ids. A check of one study's own
  system (its parser, its start configuration, its particle counts) goes in
  `projects/<study>/python/tests/`. `tests/test_layout.py` holds the checks
  of the repository's own layout.
- **Names and docstrings.** `test_<unit>_<behavior>`, with a one-line
  docstring in the present tense stating the behavior, invariant, or
  regression it protects. No issue numbers, and no "Test that".
- **Data.** Put cases in `parametrize`, a fixture, or the test body. A
  module constant holds only a path or a compiled pattern.
- **Errors and numbers.** Check an error with
  `pytest.raises(ErrorType, match="...")` around the one call that raises.
  Compare floating-point results with a stated tolerance,
  `pytest.approx(expected, rel=..., abs=...)` or
  `numpy.testing.assert_allclose`, and say where the tolerance comes from.
- **Generated inputs.** A Hypothesis strategy builds valid inputs directly.
  Do not draw at random and reject, which trips Hypothesis's health check
  for filtered inputs now and then.
- **Private data.** A test marked `private_data` reads the maintainer's
  processed data and is skipped without `POLYPHYS_DATA_DIR`. Never commit
  what it reads, and never print it.
- **Commands.** `python -m pytest <path>::<test name>` for one test, then
  the full suite, as AGENTS.md, "Commands", gives them. Pass `-rf` so a
  failure prints its name.

```python
def test_manifest_identifies_each_run_once(study):
    """No two manifest rows share a variant and a run name."""
```

Not: `"""Test the manifest."""` (it states no claim).
