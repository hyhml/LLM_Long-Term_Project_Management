# ADR-0007: Retrieval must report coverage

- Status: Accepted
- Date: 2026-09-20
- Implemented in: `0.3.0-dev.1`

## Context

An empty search result may mean absence, an incomplete index, missing authorization, an unread source format, excluded pending work, or a stale index. Reporting it as project-wide absence is unsafe in every subject domain.

## Decision

Every retrieval response reports:

- current project revision and index status/source revision;
- records, registered sources, files, or collections actually searched;
- authorized scope that was not searched;
- exclusions, truncation, stale state, and other coverage gaps.

An empty result means only that no match was found within the currently searched, indexed, and authorized scope. It never proves that the project or unsearched sources contain no relevant material.

`index/` is rebuildable acceleration state, not authority. `sources/registry.json` records source metadata and access scope; searching that metadata does not imply that PDF, webpage, dataset, or note bodies were opened.

## Enforcement and consequences

New projects contain an index manifest with explicit coverage and exclusions. The lightweight search tool always returns a coverage object. The generated child skill loads the retrieval protocol only for search or index work.

Responses become more qualified but accurately distinguish “not found here” from “does not exist.” Domain-specific retrieval tools may extend the coverage schema while preserving this rule.
