# ADR-0001: Record architecture decisions

**Status:** Accepted · **Date:** 2026-11-25

## Context
Reviewers (faculty, future maintainers, the author six months from now) need to know
*why* the platform looks the way it does, not just *what* it is.

## Decision
Record each significant decision as a short Markdown ADR in `docs/adr/`, numbered,
immutable once accepted. A changed decision gets a new ADR that supersedes the old one.

## Consequences
+ Decisions are reviewable in pull requests like code.
+ Viva questions about trade-offs ("why not Helm?") have written answers.
− A small writing overhead per decision.
