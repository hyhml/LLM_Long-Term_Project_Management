# Change classification and dialogue disclosure

Classify a substantive managed request on two independent axes before choosing files, write authority, versioning, or release behavior.

## Axis 1: change layer

- `project-data`: changes one concrete project's contract, tasks, records, relations, sources, work material, candidate tools, or authorized project artifacts. Accepted management changes use the project transaction and project revision.
- `framework`: changes reusable rules, schemas, templates, scripts, protocols, framework backlog, ADRs, or framework version. It requires explicit framework development mode and must not silently rewrite a concrete project's accepted data.
- `mixed`: contains both; split it into a project-data change and a framework change with separate write paths, versions, validation, and release statements.
- `none/read-only`: inspection, explanation, or planning that changes neither authority.

Classify by what authority changes. Using a framework tool to update one project is still `project-data`. Changing the generic record schema is `framework`, even though its subject is data storage. Creating a new child project with an unchanged initializer creates project data; it does not modify the framework.

## Axis 2: audience

- `runtime-user`: changes behavior or material delivered to people using the released skill or a concrete project.
- `developer`: changes development-only ADRs, tests, diagnostics, migration design, or maintainer material excluded from runtime distribution.
- `both`: affects both groups; maintain distinct artifacts and state what reaches each audience and branch.

Audience is determined by who consumes the result, not by file extension. A user guide may be runtime-facing; an ADR about the same feature is developer-facing.

## Dialogue contract

At the first substantive progress update, state at least:

```text
变更分类：
- 层级：project-data / framework / mixed / none-read-only
- 受众：runtime-user / developer / both
- 生效与写入边界：具体项目 revision、development、main，或无写入
```

Keep this short when classification is obvious. Explain the reason and split plan when it is mixed or ambiguous. If work crosses a boundary later, stop that part, disclose the reclassification, and apply the newly required confirmation/version/release protocol.

In the final response, restate the classification for material changes and report where each class was written, versioned, and released. Do not describe developer-only artifacts as installed runtime behavior, or a framework template change as if it migrated existing project data.
