# ShockLink workflow preferences

- Keep work proportional to the request. For clear, localized changes, use a
  compact design summary and direct test-first implementation.
- Use `.worktrees` for isolated feature work.
- Minimize progress updates, planning prose, and documentation artifacts unless
  they are requested or required by higher-priority instructions.
- Prefer targeted tests while developing; run the full test suite once before
  merging.
- Do not use multiple subagents or repeated review cycles unless the user asks
  for them or the change has substantial independent or high-risk parts.
- After a verified feature is ready, merge it directly into `main` without
  asking for an integration choice.
- Keep final handoffs short: summarize the change, verification result, and
  integration state.
