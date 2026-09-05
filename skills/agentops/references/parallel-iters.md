# Parallel Iters

Read [herdr.md](herdr.md) and [iter.md](iter.md) first.

This command first identifies independent lines of work, then launches one goal-directed iteration chain for each line in the same working directory. Complete the Herdr preflight once, then give each chain its own iter workspace using the root-pane launch and `agent prompt --wait` protocol. Separation is by explicit scope ownership only: file paths, modules, features, tests, or investigation targets. Do not create branches, do not create git worktrees, do not use `wt`, and do not move agents into separate working copies for this command.

Give each chain observable completion criteria that it can satisfy entirely within its scope. Each chain stops immediately when its criteria are satisfied. It also stops when blocked, unsafe, explicitly paused, or after two consecutive passes without material progress. The controller does not finish or integrate the final task; after all chains finish or report their blockers, the user takes over integration.

## User Prompt Shape

When invoking worker chains, use this intent unless the user gave a sharper one:

```text
We want to run /agentops iter, but a single iter thread is very slow.

Identify what and how many parallel iter chains can accelerate this goal. After identifying independent lines of work, define observable completion criteria for each line and launch all of them in the same working directory. Each chain must stop as soon as it satisfies its criteria, and each line must be safely separated from the others by scope. When all chains are done, leave the results for the user to review and integrate toward the final task. It is implicitly understood that launching parallel-iters will not get us to the final goal, because there is more work to be done after the identified parallelizable chains are finished.
```

## Decomposition

1. Capture the final goal, evaluation criteria, constraints, repo state, changed files, project rules, and commands already run.
2. Inspect enough of the repo to identify independent lines of work. Good splits include separate packages, UI surfaces, benchmark families, bug classes, test suites, migration stages, or competing implementation strategies.
3. Give each lane observable completion criteria that are achievable entirely within its assigned scope.
4. Choose the smallest number of lanes that can make real parallel progress. Do not create a lane for tiny cleanup or work that requires constant coordination with another lane.
5. Reject unsafe splits where two lanes would edit the same files, mutate the same data model contract from different directions, or require shared sequencing.
6. If no safe split exists, run normal `iter` instead and explain why parallel chains would collide before proceeding with one sequential chain.
7. Scope separation is the safety mechanism. The lane contract must make ownership concrete enough that two active chains can work without coordinating every edit. If a lane discovers it needs another lane's scope, it must stop and report the collision instead of editing across the boundary.
8. Each chain has its own space in Herdr.
