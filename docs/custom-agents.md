# Custom Agents (Speckit)

This project uses a specification-driven development workflow powered by custom GitHub Copilot agents called **Speckit**. These agents help automate and standardize the feature development lifecycle from specification to implementation.

## What are Custom Agents?

Custom agents are specialized AI assistants configured for specific tasks in the development workflow. They:

- Have focused expertise in one aspect of development (specification, planning, implementation, etc.)
- Follow consistent templates and patterns defined in `.specify/templates/`
- Maintain project standards defined in `.specify/memory/constitution.md`
- Can hand off work to other agents in the workflow
- Are located in `.github/agents/` with configuration in `.github/prompts/`

## Available Agents

### 1. speckit.specify
**Purpose**: Create or update feature specifications from natural language descriptions

**When to use**: 
- Starting a new feature
- Need to document what a feature should do
- Converting user requirements into structured specifications

**What it does**:
- Generates a concise short name for the feature (2-4 words)
- Creates a new branch with format `{number}-{short-name}`
- Creates a `specs/{number}-{short-name}/spec.md` file using the spec template
- Extracts and structures functional and non-functional requirements
- Documents user stories, edge cases, and acceptance criteria

**Handoff to**: `speckit.plan` (build technical plan) or `speckit.clarify` (clarify requirements)

---

### 2. speckit.clarify
**Purpose**: Identify underspecified areas in specifications and gather clarifications

**When to use**:
- After creating a spec but before technical planning
- When the specification has ambiguities or missing details
- Need to reduce implementation risk by clarifying requirements early

**What it does**:
- Scans the spec for ambiguities and coverage gaps
- Asks up to 5 targeted clarification questions across categories:
  - Functional scope & behavior
  - Domain & data model
  - Interaction & UX flow
  - Non-functional quality attributes
  - Integration & external dependencies
  - Edge cases & failure handling
- Records answers directly in the spec file

**Handoff to**: `speckit.plan` (proceed with planning after clarification)

---

### 3. speckit.plan
**Purpose**: Create technical implementation plan from specification

**When to use**:
- After specification is complete and clarified
- Need to translate requirements into technical architecture

**What it does**:
- Reads the feature specification
- Generates `plan.md` with:
  - Technical context (tech stack, libraries, architecture)
  - Research on unknowns and best practices → `research.md`
  - Data model design → `data-model.md`
  - API contracts → `contracts/` directory
  - Quick start guide → `quickstart.md`
- Validates against constitution principles
- Updates agent context files (copilot-instructions.md)

**Handoff to**: `speckit.tasks` (generate implementation tasks) or `speckit.checklist` (create custom checklist)

---

### 4. speckit.tasks
**Purpose**: Generate actionable, dependency-ordered task list

**When to use**:
- After technical plan is complete
- Ready to break down implementation into concrete tasks

**What it does**:
- Reads spec.md, plan.md, and all design artifacts
- Generates `tasks.md` organized by:
  - Phase 1: Setup (project initialization)
  - Phase 2: Foundational (blocking prerequisites)
  - Phase 3+: User stories in priority order (P1, P2, P3...)
  - Final Phase: Polish & cross-cutting concerns
- Each task includes:
  - Sequential ID (T001, T002, etc.)
  - [P] marker if parallelizable
  - [US1], [US2] labels mapping to user stories
  - Exact file paths and descriptions
- Creates dependency graph showing execution order

**Handoff to**: `speckit.analyze` (consistency check) or `speckit.implement` (start implementation)

---

### 5. speckit.analyze
**Purpose**: Cross-artifact consistency and quality analysis (read-only)

**When to use**:
- After tasks.md is generated
- Before starting implementation
- Want to catch inconsistencies, duplications, or ambiguities

**What it does**:
- Analyzes spec.md, plan.md, and tasks.md for:
  - Duplication detection
  - Requirement coverage gaps
  - Task-to-requirement traceability
  - Constitution principle violations
  - Ambiguity detection
  - Technical debt indicators
- **Read-only**: Does not modify files
- Generates structured analysis report
- Offers optional remediation plan

**Handoff to**: `speckit.implement` (proceed with implementation)

---

### 6. speckit.checklist
**Purpose**: Generate custom checklists for specific domains (UX, security, testing, etc.)

**When to use**:
- Need domain-specific validation checklists
- Want to ensure completeness for specific quality aspects

**What it does**:
- Reads feature specification and plan
- Generates domain-specific checklists in `checklists/` directory
- Common checklist types:
  - UX/Accessibility
  - Security
  - Testing/QA
  - Performance
  - Documentation
- Each checklist is a markdown file with checkboxes

**Handoff to**: `speckit.implement` (implementation checks checklists)

---

### 7. speckit.implement
**Purpose**: Execute implementation plan by processing tasks.md

**When to use**:
- All planning, clarification, and analysis is complete
- Ready to start actual code implementation

**What it does**:
- Checks checklist status (if exists) and warns if incomplete
- Loads all design artifacts (spec, plan, tasks, contracts, etc.)
- Verifies project setup (creates .gitignore, .dockerignore, etc.)
- Executes tasks phase-by-phase:
  - Respects dependencies
  - Runs parallel tasks [P] concurrently
  - Follows TDD approach (tests before implementation)
  - Validates each phase before proceeding
- Reports progress after each completed task
- Marks completed tasks as [X] in tasks.md

---

### 8. speckit.taskstoissues
**Purpose**: Convert tasks.md into actionable GitHub issues

**When to use**:
- Want to track implementation progress in GitHub Issues
- Need to assign work to team members
- Prefer issue-based workflow over tasks.md checkboxes

**What it does**:
- Reads tasks.md
- Creates GitHub issues for each task
- Preserves task IDs, labels, and dependencies
- Links issues to feature specification

---

### 9. speckit.constitution
**Purpose**: Create or update project constitution

**When to use**:
- Setting up project principles and standards
- Updating development guidelines
- Need to encode team agreements

**What it does**:
- Interactive or batch mode for defining principles
- Updates `.specify/memory/constitution.md`
- Ensures all templates stay in sync with principles
- Versions changes (MAJOR/MINOR/PATCH)

## Workflow Overview

```text
┌─────────────────┐
│  User Request   │
│ (Natural Lang.) │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│  speckit.specify        │
│  Create spec.md         │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  speckit.clarify        │
│  Ask clarifications     │
│  Update spec.md         │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  speckit.plan           │
│  Create plan.md         │
│  + research.md          │
│  + data-model.md        │
│  + contracts/           │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  speckit.tasks          │
│  Create tasks.md        │
└────────┬────────────────┘
         │
         ├──────────────────────┐
         │                      │
         ▼                      ▼
┌─────────────────┐   ┌──────────────────┐
│ speckit.analyze │   │ speckit.checklist│
│ Check quality   │   │ Domain checklists│
└─────────────────┘   └──────────────────┘
         │                      │
         └──────────┬───────────┘
                    │
                    ▼
         ┌─────────────────────┐
         │  speckit.implement  │
         │  Execute tasks      │
         │  Write code         │
         └─────────────────────┘
```

## Directory Structure

```text
.github/
├── agents/                          # Agent definitions
│   ├── speckit.specify.agent.md
│   ├── speckit.clarify.agent.md
│   ├── speckit.plan.agent.md
│   ├── speckit.tasks.agent.md
│   ├── speckit.analyze.agent.md
│   ├── speckit.checklist.agent.md
│   ├── speckit.implement.agent.md
│   ├── speckit.taskstoissues.agent.md
│   ├── speckit.constitution.agent.md
│   └── copilot-instructions.md     # Auto-generated context
└── prompts/                         # Agent prompts (internal)
    └── speckit.*.prompt.md

.specify/
├── memory/
│   └── constitution.md              # Project principles
├── scripts/
│   └── bash/
│       ├── setup-plan.sh
│       ├── check-prerequisites.sh
│       └── update-agent-context.sh
└── templates/
    ├── spec-template.md
    ├── plan-template.md
    ├── tasks-template.md
    ├── checklist-template.md
    └── agent-file-template.md

specs/
└── {number}-{feature-name}/         # Generated per feature
    ├── spec.md                      # Feature specification
    ├── plan.md                      # Technical plan
    ├── tasks.md                     # Implementation tasks
    ├── research.md                  # Technical research
    ├── data-model.md                # Data model design
    ├── quickstart.md                # Quick start guide
    ├── contracts/                   # API contracts
    │   └── *.yaml
    └── checklists/                  # Domain checklists
        ├── ux.md
        ├── security.md
        └── testing.md
```

## How to Use

### Starting a New Feature

1. **Create specification**:
   ```
   /speckit.specify Add user authentication with OAuth2
   ```

2. **Clarify requirements** (optional but recommended):
   ```
   /speckit.clarify
   ```

3. **Create technical plan**:
   ```
   /speckit.plan I am building with Python Flask and PostgreSQL
   ```

4. **Generate tasks**:
   ```
   /speckit.tasks
   ```

5. **Analyze for consistency** (optional):
   ```
   /speckit.analyze
   ```

6. **Generate checklists** (optional):
   ```
   /speckit.checklist Generate security and UX checklists
   ```

7. **Start implementation**:
   ```
   /speckit.implement
   ```

### Viewing Generated Artifacts

All artifacts are created in `specs/{number}-{feature-name}/`:

```bash
# View specification
cat specs/001-user-auth/spec.md

# View technical plan
cat specs/001-user-auth/plan.md

# View tasks
cat specs/001-user-auth/tasks.md

# View contracts
ls specs/001-user-auth/contracts/
```

## Key Concepts

### Constitution
The `.specify/memory/constitution.md` file defines non-negotiable project principles:
- Unit testing (80%+ coverage)
- Modular architecture
- Code clarity & documentation
- Fail-fast error handling
- Comprehensive documentation
- Accessibility for all skill levels

All agents validate work against these principles.

### Templates
Templates in `.specify/templates/` provide consistent structure:
- `spec-template.md`: Feature specification format
- `plan-template.md`: Technical plan format
- `tasks-template.md`: Task list format
- `checklist-template.md`: Checklist format

### Agent Context
The `.github/agents/copilot-instructions.md` file is auto-generated to provide context about:
- Active technologies in the project
- Common commands
- Code style preferences
- Recent changes

This is updated automatically by `speckit.plan` when new technologies are added.

### Task Format
Tasks follow a strict format for consistency:
```
- [ ] T001 [P] [US1] Description with file path
```
- `- [ ]`: Checkbox (unchecked)
- `T001`: Sequential task ID
- `[P]`: Optional parallel marker
- `[US1]`: Optional user story label
- Description with exact file path

## Benefits

1. **Consistency**: All features follow the same structure and process
2. **Traceability**: Clear path from requirements → plan → tasks → implementation
3. **Quality**: Built-in validation against project principles
4. **Documentation**: Automatically generates comprehensive documentation
5. **Collaboration**: Structured artifacts make handoffs easier
6. **Efficiency**: Automates repetitive planning and setup work
7. **Risk Reduction**: Early clarification and analysis catch issues before coding

## Constitution Compliance

This custom agent workflow enforces the project constitution:

- ✅ **Unit Testing**: Tasks include test generation and validation
- ✅ **Modular Architecture**: Plan enforces clear module boundaries
- ✅ **Code Clarity**: Documentation tasks are always included
- ✅ **Fail-Fast**: Error handling tasks are explicit
- ✅ **Documentation**: README, API docs, and guides are generated
- ✅ **Accessibility**: Checklists ensure UX and accessibility coverage

## Troubleshooting

### "Feature branch not found"
- Make sure you're on a feature branch created by `speckit.specify`
- Check branch naming: should be `{number}-{short-name}`

### "Prerequisite file missing"
- Run the prerequisite agent first (e.g., run `speckit.specify` before `speckit.plan`)
- Check `specs/{feature}/` directory for expected files

### "Constitution violation"
- Review `.specify/memory/constitution.md` for violated principles
- Update spec/plan/tasks to comply with principles
- If principle itself needs changing, use `speckit.constitution`

### "Cannot parse JSON output"
- Check that setup scripts are executable
- Verify `.specify/scripts/bash/` scripts exist
- Try running script manually to see raw output

## See Also

- [Architecture](architecture.md) - System design and components
- [API Documentation](api-documentation.md) - REST API reference
- [Deployment Guide](deployment.md) - How to deploy the application
- Main [README](../README.md) - Project overview and quick start
