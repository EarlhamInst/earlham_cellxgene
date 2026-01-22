<!--
  ============================================================================
  SYNC IMPACT REPORT
  ============================================================================
  Version Change: [INITIAL VERSION] → 1.0.0
  Change Type: MAJOR (Initial constitution establishment)
  
  Modified Principles:
  - NEW: I. Unit Testing (Non-Negotiable)
  - NEW: II. Modular Architecture
  - NEW: III. Code Clarity & Documentation
  - NEW: IV. Fail-Fast Error Handling
  - NEW: V. Comprehensive Documentation
  - NEW: VI. Accessibility for All Skill Levels
  
  Added Sections:
  - Development Standards
  - Quality Gates
  - Governance
  
  Removed Sections: None (initial version)
  
  Templates Status:
  ✅ plan-template.md - verified alignment with constitution principles
  ✅ spec-template.md - verified alignment with constitution principles
  ✅ tasks-template.md - verified alignment with constitution principles
  ✅ checklist-template.md - verified alignment with constitution principles
  
  Follow-up TODOs: None
  
  Rationale for version 1.0.0:
  This is the initial establishment of the project constitution. All principles
  are newly defined based on explicit project requirements: mandatory unit testing,
  modular and well-commented code, comprehensive documentation, fail-fast behavior,
  and accessibility for developers at all skill levels.
  ============================================================================
-->

# CellXGene Stack Constitution

## Core Principles

### I. Unit Testing (Non-Negotiable)

**MUST** write unit tests for all functionality. Every feature, module, and significant code path MUST be covered by automated tests.

- Unit tests MUST be written using industry-standard testing frameworks appropriate for the language
- Test coverage SHOULD aim for 80%+ of code paths
- Tests MUST be run before any code is merged to main branch
- Integration tests MUST validate interactions between modules
- Contract tests MUST verify API/interface boundaries

**Rationale**: Unit testing ensures code reliability, catches regressions early, serves as living documentation of expected behavior, and enables confident refactoring. This is non-negotiable because the cost of bugs in production far exceeds the cost of writing tests upfront.

### II. Modular Architecture

**MUST** structure code in discrete, self-contained modules with clear boundaries and single responsibilities.

- Each module MUST have a clearly defined purpose and interface
- Modules MUST minimize dependencies on other modules
- Cross-module communication MUST happen through well-defined interfaces
- Circular dependencies are FORBIDDEN
- Each module SHOULD be independently testable
- Shared utilities MUST be extracted into reusable library modules

**Rationale**: Modular architecture reduces complexity, enables parallel development, simplifies testing, and makes the codebase easier to understand and maintain. Clear module boundaries prevent the "big ball of mud" anti-pattern.

### III. Code Clarity & Documentation

**MUST** prioritize code readability and understandability above all other considerations, including brevity and cleverness.

- Code MUST be self-documenting through clear naming and structure
- All functions/methods MUST have docstrings explaining purpose, parameters, return values, and exceptions
- Complex algorithms or non-obvious logic MUST include inline comments explaining the "why"
- Magic numbers MUST be replaced with named constants
- Variable and function names MUST be descriptive and unambiguous
- Code reviews MUST reject submissions that are difficult to understand

**Rationale**: Code is read far more often than it is written. Clarity ensures that team members (including future self) can quickly understand, modify, and extend the codebase. Well-commented code reduces onboarding time and prevents bugs from misunderstanding.

### IV. Fail-Fast Error Handling

**MUST** detect and report errors immediately when they occur. Silent failures are FORBIDDEN.

- Validate inputs at module boundaries - fail immediately on invalid data
- Use explicit error types/exceptions rather than generic ones
- NEVER catch exceptions without handling or logging them
- NEVER return success when an error has occurred
- Error messages MUST be specific and actionable
- Logging MUST capture context needed to diagnose issues
- Assertion failures MUST terminate execution immediately in development
- Production errors MUST be logged with full context and monitored

**Rationale**: Silent failures create debugging nightmares and data corruption. Failing fast makes bugs obvious during development rather than manifesting as mysterious production issues. Clear error messages reduce diagnosis time from hours to minutes.

### V. Comprehensive Documentation

**MUST** provide complete documentation at multiple levels: architecture overview, usage instructions, API references, and code-level comments.

- Project MUST have a README.md with: purpose, installation, quick start, and contribution guidelines
- Each major module MUST have documentation explaining its purpose and public interface
- API endpoints/functions MUST be documented with examples
- Non-trivial algorithms MUST include references or explanations
- Setup and deployment procedures MUST be documented step-by-step
- Common troubleshooting scenarios MUST be documented
- Documentation MUST be kept in sync with code changes
- Breaking changes MUST be documented in CHANGELOG

**Rationale**: Documentation multiplies developer productivity by reducing time spent figuring out how things work. It enables new team members to contribute quickly and reduces dependency on specific individuals. Good documentation is a force multiplier.

### VI. Accessibility for All Skill Levels

**MUST** design the codebase and documentation to be approachable by developers with varying experience levels, while maintaining professional standards.

- Architecture decisions MUST be explained, not assumed
- Complex patterns MUST include rationale and simpler alternatives considered
- Setup instructions MUST assume minimal prior knowledge
- Error messages MUST be beginner-friendly with suggestions for resolution
- Code examples MUST be provided for common use cases
- Technical jargon MUST be explained or linked to resources
- Onboarding documentation MUST guide new developers through their first contribution
- Internal tooling MUST have clear usage instructions

**Rationale**: The target users include both experienced developers and relative newbies on the team. Making the project accessible to all skill levels expands the contributor pool, reduces onboarding friction, and creates a more inclusive development environment.

## Development Standards

### Code Review Requirements

- All code MUST be reviewed by at least one other developer before merging
- Reviews MUST verify: test coverage, code clarity, documentation updates, and principle compliance
- Reviewers MUST run tests locally before approving
- Breaking changes MUST be explicitly flagged and documented

### Testing Standards

- Unit tests MUST run in under 5 seconds per test file
- Integration tests MUST be isolated and repeatable
- Tests MUST not depend on external services (use mocks/stubs)
- Test data MUST be committed to the repository or generated deterministically
- Flaky tests MUST be fixed immediately or disabled with tracking issue

### Documentation Standards

- Documentation MUST be written in Markdown
- Code examples MUST be tested and working
- Screenshots MUST be kept up-to-date with UI changes
- Documentation MUST live close to the code it describes (prefer inline docs)
- API changes MUST update documentation in the same commit

## Quality Gates

The following gates MUST pass before code can be merged:

1. **Test Gate**: All unit tests and integration tests pass
2. **Coverage Gate**: Test coverage does not decrease (aim for 80%+)
3. **Lint Gate**: Code passes all linting rules with no warnings
4. **Documentation Gate**: All public APIs have documentation
5. **Review Gate**: Code has been reviewed and approved
6. **Constitution Gate**: Code complies with all constitutional principles

Violations of any gate MUST be justified in writing and approved by at least two team members.

## Governance

### Amendment Procedure

This constitution can be amended through the following process:

1. Propose amendment in writing with rationale
2. Discuss with team and gather feedback
3. Achieve consensus or majority approval
4. Update constitution with version bump
5. Update all dependent templates and documentation
6. Communicate changes to all team members

### Versioning Policy

Constitution versions follow semantic versioning:

- **MAJOR**: Backward-incompatible changes (principle removal or redefinition)
- **MINOR**: Additions (new principles or significant expansions)
- **PATCH**: Clarifications, wording improvements, non-semantic fixes

### Compliance Review

- Constitution compliance MUST be reviewed during code review
- Quarterly audits SHOULD be performed to assess overall adherence
- Violations MUST be tracked and patterns addressed
- Complexity that violates principles MUST be justified and documented

### Authority

This constitution supersedes conflicting practices, style guides, or individual preferences. When in doubt, constitutional principles take precedence.

---

**Version**: 1.0.0 | **Ratified**: 2026-01-14 | **Last Amended**: 2026-01-14
