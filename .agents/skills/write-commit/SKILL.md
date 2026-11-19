---
name: write-commit
description: Write and make a commit in this project's format, on a branch that is not the base. Use for every commit, once the maintainer has reviewed the change and its message.
---

# Write a commit

1. Check the branch: `git branch --show-current`. On `main`, stop; create a
   branch first (create-branch).
2. Write the message to a file outside the repository, in this shape;
   `.gitmessage` holds the same shape for commits written in an editor:

   ```text
   <type>(<scope>): <subject>

   <what changed>

   Why: <reason from the issue, the maintainer, or an outside report; omit otherwise, never a placeholder>

   Assisted-by: <tool>, <model identifier or not recorded> (<role>)
   Checks-run: <check actually run> — <observed result>
   Ground-truth-source: <independent source of a reference value>
   ```

   - Subject: imperative, with a type and a scope (an area) from
     CONTRIBUTING.md, "Names".
   - Body: what changed, including which wording or code you were given and
     which you wrote. This is where the detail of your role goes.
   - `Why:` only for a reason from the linked issue, from the maintainer (in
     the pull request or this session), or from an outside report the change
     answers, such as a bug report or a CI failure. Otherwise leave it out.
   - Trailers: one block, after a blank line, with no blank line in it and
     nothing after it. Pick each trailer and the role as AGENTS.md,
     "Provenance", defines them.
3. Scrub the change and the message: search the unstaged diff and the
   message file for what AGENTS.md, "A public repository", forbids, with
   the patterns of `AGENTS.local.md` where that file lists some. A commit
   cannot be taken back once pushed.
4. Show the maintainer the changed paths and the message, and wait for the
   review, as AGENTS.md, "Git", says. Afterwards re-read the files and
   `git diff`; the maintainer may have edited them.
5. Stage only what was approved, by path, and read the staged diff
   (`git diff --cached`). One commit holds one coherent change.
6. Commit from the file: `git commit -F <message file>`. Never add an AI
   `Co-authored-by:` line, and never use `--no-verify`.
7. Check that git reads every trailer: `git log -1 --format='%(trailers)'`.
