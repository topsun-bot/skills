# ChatGPT Pro External Engineer Brief

Copy this structure into the external conversation and replace every bracketed field. Remove sections that are genuinely inapplicable instead of leaving placeholders.

## Role and trust boundary

You are the external senior engineer for this task. Analyze the supplied source snapshot, research primary sources where necessary, propose the design, and produce a minimal complete implementation artifact.

Your output is advisory until Codex independently reviews and tests it. You cannot assume access to the local repository, private services, credentials, deployment environment, or any file not attached here. Do not claim that you executed a command or verified an environment unless you actually did so in a clearly identified environment.

## Task identity

- Task ID: `[TASK_ID]`
- Title: `[TITLE]`
- ChatGPT mode selected: `[VISIBLE_PRO_MODEL_AND_REASONING_LABEL]`
- Source baseline: `[HEAD_OR_UNBORN_HEAD]`
- Working-tree state represented: `[COMMITTED_HEAD_OR_SANITIZED_SNAPSHOT]`
- Source archive: `[FILENAME]`
- Archive bytes: `[BYTE_SIZE]`
- Archive SHA-256: `[SHA256]`

## Background

`[PRODUCT_CONTEXT_AND_RELEVANT_HISTORY]`

## Goal

`[ONE_PRECISE_OUTCOME]`

## Current architecture and invariants

- `[ARCHITECTURE_FACT]`
- `[BOUNDARY_THAT_MUST_NOT_BREAK]`
- `[RUNTIME_OR_DEPENDENCY_CONSTRAINT]`

## Scope

In scope:

- `[RESEARCH_OR_CHANGE_1]`
- `[RESEARCH_OR_CHANGE_2]`

Out of scope:

- `[NON_GOAL_1]`
- `[NON_GOAL_2]`

## Required deliverables

1. A concise findings and design report tied to concrete source files and primary references.
2. A minimal, complete unified diff or changed-file archive that applies to the supplied baseline.
3. A file-by-file change summary and explanation of important design decisions.
4. Tests added or changed, plus exact commands that Codex should run locally.
5. A list of assumptions, unverified claims, compatibility risks, and remaining work.

## Required verification

- `[LINT_OR_FORMAT_COMMAND]`
- `[TYPECHECK_COMMAND]`
- `[UNIT_OR_CONTRACT_TEST_COMMAND]`
- `[BUILD_COMMAND]`
- `[RELEVANT_E2E_COMMAND]`

Clearly separate:

- tests you actually executed and their environment;
- tests you could not execute and only recommend;
- simulated or mocked evidence;
- any claim that would require staging or production access.

## Prohibited actions and claims

- Do not request or expose passwords, API keys, tokens, cookies, private keys, or personal data.
- Do not assume access to omitted files, private repositories, internal networks, or local services.
- Do not commit, push, open a pull request, deploy, migrate a database, change production configuration, activate production features, or operate on real user data.
- Do not add unrelated refactors, dependency upgrades, formatting churn, or generated artifacts.
- Do not describe a proposed, mocked, or sandbox-only check as local repository or production validation.

## Acceptance criteria

- `[FUNCTIONAL_CRITERION]`
- `[TEST_CRITERION]`
- `[PERFORMANCE_COMPATIBILITY_OR_VISUAL_CRITERION]`
- `[NO_REGRESSION_CRITERION]`

## Response format

Return sections in this order:

1. Findings and evidence
2. Proposed design
3. Implementation artifact
4. Changed files
5. Tests actually run
6. Tests still required locally
7. Risks, assumptions, and unresolved questions

If the supplied source is insufficient, identify the smallest additional non-secret file or fact needed. Continue with all work that does not depend on it.
