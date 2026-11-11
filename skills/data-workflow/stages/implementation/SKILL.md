# Implementation Guardrails

Apply this skill before making code changes or performing code review.

## 1. Think Before Coding

Before implementing:

- State assumptions explicitly
- If something is uncertain, ask instead of guessing
- If there are multiple valid interpretations, surface them
- If a simpler approach exists, prefer it and say so
- If a requirement is unclear, stop and name the ambiguity

## 2. Simplicity First

Choose the minimum solution that satisfies the request.

- Do not add features that were not requested
- Do not introduce abstractions for one-off use
- Do not add speculative configurability
- Do not write defensive code for impossible cases
- If the solution feels larger than necessary, simplify it
- If the ask is essentially “add a list filter”, implement it as a filter (proto → pass-through → WHERE). Do not invent intermediate flags, one-off helpers, or cross-module signature changes for unrequested edge cases. See project rule **R18**.

Checkpoint:

`Would a senior engineer consider this overcomplicated for the problem?`

If yes, reduce scope.

## 3. Surgical Changes

Touch only the code required for the task.

- Do not clean up unrelated code
- Do not refactor adjacent paths unless required
- Match existing local style and patterns
- Remove only the unused code created by your own change
- If you notice unrelated issues, mention them instead of folding them into the diff

Validation rule:

`Every changed line should trace directly to the request.`

## 4. Goal-Driven Execution

Convert the request into verifiable outcomes before coding.

Use a short plan when the task has multiple steps:

```text
1. [Step] -> verify: [check]
2. [Step] -> verify: [check]
3. [Step] -> verify: [check]
```

Prefer concrete checks such as:

- reproduce the bug with a test, then make it pass
- add invalid-input coverage, then make it pass
- verify behavior before and after a refactor

Weak success criteria like `make it work` are not enough when a stronger check is available.

## 常见错法

- **顺手改无关的债。** 看到了就想一起修。改成在回复里点名，不进这个 diff。
- **「验过了」但没有退出码。** 说的是「应该没问题」。要么贴命令和 exit，要么写「没验成」。
- **新造一套模式。** 旁边已有实现却另起一个抽象。先找有没有可复用的。
- **一次提交太大。** 一个 diff 里塞了几件事，没法一眼看完。
- **把 mid-change 的树留在半坏状态。** 两次提交之间编译不过。
