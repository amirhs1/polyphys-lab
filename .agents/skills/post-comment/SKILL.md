---
name: post-comment
description: Post a short comment on a GitHub issue or pull request. Use when asked to reply to, comment on, or revise your comment on an issue or pull request, not for comments in code.
---

# Post a comment

1. Comment only on the issue or pull request the person running you named.
2. Give the answer first, with evidence as `path:line` or `command → result`.
   End with your trailer block, as AGENTS.md, "Provenance", gives it.
3. Scrub the comment for what AGENTS.md, "A public repository", forbids. A
   comment is public at once, and editing it later keeps its old text in
   the edit history.
4. Post it with `gh issue comment <n> --body-file <file>` or
   `gh pr comment <n> --body-file <file>`.
5. To revise your last comment there, run the same command with
   `--edit-last`.
