---
name: loop-prompt
description: Persistent iterative execution pattern for well-defined coding, build, test, refactor, migration, or documentation tasks with explicit completion criteria. Use when the user asks to loop, keep going, iterate until done, use a Ralph-style loop, run a loop prompt, or complete a multi-phase task autonomously with verification and a completion promise.
---

# Loop Prompt

Use this skill to simulate a Ralph-style development loop inside Codex. Codex does not use Claude Code stop hooks, so the loop is procedural: keep iterating within the current turn, inspect prior work, run verification, and only stop when the completion criteria are true or a real blocker is reached.

## Workflow

1. Restate the task as concrete completion criteria.
2. Set an iteration cap when the user did not provide one. Default to 5 focused iterations for small tasks and 10 for larger build tasks.
3. In each iteration:
   - Inspect the current files, tests, logs, and TODOs relevant to the task.
   - Implement the next smallest useful change.
   - Run the strongest practical verification command.
   - Record what changed, what passed, and what remains.
4. Before stopping, audit the original prompt and any TODO phases against the current state.
5. Only claim completion when the completion criteria are genuinely satisfied.

## Completion Promise

If the user provides a completion promise, output it only when the statement is unequivocally true. Do not use the promise to exit early, hide uncertainty, or bypass a blocker.

If no promise is provided, use normal final reporting:

- Completed work
- Verification performed
- Remaining blockers, if any

## When Blocked

Continue through ordinary failures such as failing tests, missing dependencies, type errors, or build errors when they can be diagnosed locally.

Stop and report a blocker only when:

- Required credentials or external access are unavailable.
- The task needs a human decision that cannot be inferred safely.
- Verification depends on a service or account Codex cannot reach.
- The same blocker remains after several concrete attempts.

When blocked, include what was attempted and the next exact action needed.

## Prompt Shape

For best results, encourage prompts with phases and verification:

```markdown
Complete this task in phases:
1. Implement the feature.
2. Add or update tests.
3. Run lint/typecheck/build/tests.
4. Fix failures and repeat.

Completion criteria:
- All listed phases are done.
- Verification passes.
- Output COMPLETE only when true.
```
