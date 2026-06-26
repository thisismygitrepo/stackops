# Parallel Iters

Use `parallel-iters` when the user wants the speed of multiple `/workflows iter` loops and can provide one final goal. Read [herdr.md](herdr.md) and [iter.md](iter.md) first.

This command first identifies independent lines of work, then launches one iterative loop for each line in the same working directory. Separation is by explicit scope ownership only: file paths, modules, features, tests, or investigation targets. Do not create branches, do not create git worktrees, do not use `wt`, and do not move agents into separate working copies for this command.

Each loop iterates until its own scoped line is complete, blocked, unsafe, or explicitly paused. The controller does not finish or integrate the final task; after all loops finish or report their blockers, the user takes over integration.

## User Prompt Shape

When invoking worker loops, use this intent unless the user gave a sharper one:

```text
We want to run /workflows iter, but a single iter thread is very slow.

Identify what and how many parallel iter loops can accelerate this goal. After identifying independent lines of work, launch all of them in the same working directory. Each loop must iterate until it finishes its own line of work, and each line must be safely separated from the others by scope. Do not use branches, worktrees, `wt`, or separate working copies. When all loops are done, leave the results for the user to review and integrate toward the final task.
```

## Decomposition

1. Capture the final goal, evaluation criteria, constraints, repo state, changed files, project rules, and commands already run.
2. Inspect enough of the repo to identify independent lines of work. Good splits include separate packages, UI surfaces, benchmark families, bug classes, test suites, migration stages, or competing implementation strategies.
3. Choose the smallest number of lanes that can make real parallel progress. Do not create a lane for tiny cleanup or work that requires constant coordination with another lane.
4. Reject unsafe splits where two lanes would edit the same files, mutate the same data model contract from different directions, or require shared sequencing.
5. If no safe split exists, run normal `iter` instead and explain why parallel loops would collide.

Scope separation is the safety mechanism. The lane contract must make ownership concrete enough that two active loops can work without coordinating every edit. If a lane discovers it needs another lane's scope, it must stop and report the collision instead of editing across the boundary.
