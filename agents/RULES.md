# Iron Rules — All Roles

These rules are absolute. Violation is grounds for immediate removal.

1. **Never close an issue without a merged commit.** If you believe it is already fixed, cite the exact commit hash. If unsure, leave it open.
2. **Never push directly to main.** `main` = PyPI release. Only version tags merge into main.
3. **All development happens on `develop`.** Feature branches → PR → `develop`. Only release merges go `develop` → `main`.
4. **One issue = one commit = one PR.** Keep changes atomic and traceable.
5. **All GitHub output in English.** Issue titles, bodies, PR titles, comments, commit messages, code comments. No exceptions.
6. **Assign yourself before working.** `gh issue edit N --add-assignee @me`
7. **Label state machine.** Follow this flow strictly:
   - `status:in-progress` — actively being worked on
   - `status:done` — Dev complete, awaiting QA verification
   - `verified` — QA confirmed the fix works
   - Close — only after `verified` label is present
8. **Never defer issues without Ace's permission.** If you think an issue should be postponed, comment your reasoning and wait for Ace's decision.
9. **Code quality must survive public scrutiny.** The repo is public. Write every line as if the best engineers in the world are reviewing it.
10. **Only operate within the naturo repository root.**
11. **Bug tracking lives in GitHub Issues only.** No other system.
12. **CI red = stop everything.** Fix CI before any new work.
13. **Never say "nothing to do."** If issues are clear, test harder, find gaps, improve code health.
