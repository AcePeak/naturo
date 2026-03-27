# Iron Rules — All Roles

These rules are absolute. Violation is grounds for immediate removal.

1. **Never close an issue without a merged commit.** If you believe it is already fixed, cite the exact commit hash. If unsure, leave it open.
2. **Never push directly to main.** All code goes through PR + CI green + merge.
3. **One issue = one commit = one PR.** Keep changes atomic and traceable.
4. **All GitHub output in English.** Issue titles, bodies, PR titles, comments, commit messages, code comments. No exceptions.
5. **Assign yourself before working.** `gh issue edit N --add-assignee @me`
6. **Label state machine.** Follow this flow strictly:
   - `status:in-progress` — actively being worked on
   - `status:done` — Dev complete, awaiting QA verification
   - `verified` — QA confirmed the fix works
   - Close — only after `verified` label is present
7. **Never defer issues without Ace's permission.** If you think an issue should be postponed, comment your reasoning and wait for Ace's decision.
8. **Code quality must survive public scrutiny.** The repo is public. Write every line as if the best engineers in the world are reviewing it.
9. **Only operate within the naturo repository root.**
10. **Bug tracking lives in GitHub Issues only.** No other system.
11. **CI red = stop everything.** Fix CI before any new work.
12. **Never say "nothing to do."** If issues are clear, test harder, find gaps, improve code health.
