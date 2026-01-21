# Implementation Plan: CellXGene Explorer

**Branch**: `001-cellxgene-explorer` | **Date**: 2026-01-14 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-cellxgene-explorer/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Provide a self-contained Docker-based environment for exploring curated single-cell datasets via CellXGene. Users select from available h5ad files through a web landing page, launching CellXGene for interactive visualization. The system uses Docker Compose for orchestration, CellXGene v2.x with Gunicorn/Uvicorn workers for concurrency, Nginx as reverse proxy, and volume-mounted storage for datasets. Metadata follows singlecellschemas.org standards. Designed for deployment on OpenNebula/CyVerse infrastructure with extensibility for additional services.

## Technical Context

**Language/Version**: Python 3.11+ (for custom services), Shell scripting (for orchestration)  
**Primary Dependencies**: 
  - CellXGene v2.x (single-cell visualization)
  - Gunicorn + Uvicorn (ASGI server with 10 workers × 20GB)
  - Nginx (reverse proxy and static file serving)
  - Docker & Docker Compose (containerization and orchestration)
  - Flask/FastAPI (for landing page and dataset catalog service)

**Storage**: 
  - Volume-mounted h5ad files from host filesystem
  - Metadata files per dataset (JSON conforming to http://singlecellschemas.org)
  - Optional: NFS or MinIO for shared storage in multi-node deployments

**Testing**: 
  - pytest (Python unit and integration tests)
  - Docker healthchecks (container validation)
  - End-to-end tests using Playwright or Selenium

**Target Platform**: 
  - Linux (Ubuntu/CentOS) on OpenNebula or CyVerse cloud
  - Docker-compatible infrastructure
  - x86_64 architecture

**Project Type**: Web application (multi-container microservices)  

**Performance Goals**: 
  - 10 concurrent users (one per Gunicorn worker)
  - Dataset selection → CellXGene launch < 30 seconds
  - Support datasets up to 10GB h5ad files

**Constraints**: 
  - 200GB total memory allocation (10 workers × 20GB)
  - Fail-fast validation on startup (constitution alignment)
  - No authentication required (open access per FAIR principles)

**Scale/Scope**: 
  - 10-50 curated datasets
  - 10 concurrent users
  - Single-node or multi-node deployment
  - Extensible for additional web services

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with constitutional principles from `.specify/memory/constitution.md`:

- [x] **Unit Testing Gate**: Plan includes unit test strategy (pytest for Python services, Docker healthchecks, end-to-end tests)
- [x] **Modular Architecture Gate**: Design shows clear module boundaries (landing page service, CellXGene service, Nginx proxy, dataset validator - each containerized)
- [x] **Code Clarity Gate**: Plan commits to descriptive naming, comprehensive docstrings, inline comments for complex logic, README with architecture diagrams
- [x] **Fail-Fast Gate**: Error handling strategy defined - startup validation of all datasets, explicit exceptions, healthchecks, immediate failure on invalid data
- [x] **Documentation Gate**: Comprehensive documentation plan includes README, API docs, deployment guide, troubleshooting guide, architecture diagrams, code comments
- [x] **Accessibility Gate**: Setup instructions designed for Docker beginners, clear error messages with recovery steps, example datasets, step-by-step deployment guide

**Violations**: None. All constitutional principles are satisfied.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
cellxgene_stack/
├── docker-compose.yml              # Multi-container orchestration
├── .env.example                    # Environment variable template
├── README.md                       # Main documentation
│
├── services/
│   ├── landing-page/              # Dataset catalog and selection UI
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── src/
│   │   │   ├── app.py            # Flask/FastAPI application
│   │   │   ├── models/           # Dataset metadata models
│   │   │   ├── routes/           # API endpoints
│   │   │   ├── templates/        # HTML templates
│   │   │   └── static/           # CSS, JS, images
│   │   └── tests/
│   │       ├── unit/
│   │       └── integration/
│   │
│   ├── cellxgene/                 # CellXGene service wrapper
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── entrypoint.sh         # Startup validation script
│   │   ├── gunicorn_conf.py      # Worker configuration
│   │   └── tests/
│   │
│   └── nginx/                     # Reverse proxy configuration
│       ├── Dockerfile
│       ├── nginx.conf
│       └── ssl/                   # SSL certificates (if needed)
│
├── data/                          # Volume-mounted datasets
│   ├── datasets/                  # h5ad files
│   │   ├── dataset1.h5ad
│   │   ├── dataset1.json         # Metadata (singlecellschemas.org)
│   │   ├── dataset2.h5ad
│   │   └── dataset2.json
│   └── logs/                      # Access and error logs
│
├── scripts/                       # Management and deployment scripts
│   ├── validate-datasets.py      # Dataset validation utility
│   ├── deploy.sh                 # Deployment script
│   └── backup-data.sh            # Backup utility
│
├── docs/                          # Additional documentation
│   ├── architecture.md
│   ├── deployment.md
│   ├── troubleshooting.md
│   └── adding-datasets.md
│
└── tests/                         # End-to-end tests
    └── e2e/
        ├── test_landing_page.py
        └── test_cellxgene_launch.py
```

**Structure Decision**: Multi-container web application architecture. Each service (landing page, CellXGene, Nginx) is containerized separately for modularity and independent scaling. Volume mounts separate code from data. This aligns with Docker best practices and constitutional principle II (Modular Architecture).

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations. All constitutional gates passed. The design is intentionally simple and follows best practices:
- Modular containerized services (Principle II)
- Comprehensive testing strategy (Principle I)
- Fail-fast validation (Principle IV)
- Extensive documentation (Principles III, V, VI)

---

## Phase 0: Research ✅

**Status**: Complete  
**Output**: [research.md](research.md)

All technology decisions documented with rationale:
- Docker/Docker Compose for containerization
- CellXGene v2.x with Gunicorn + Uvicorn (10 workers × 4GB)
- Nginx reverse proxy
- Flask/FastAPI for landing page
- Volume-mounted storage
- singlecellschemas.org metadata format
- Fail-fast error handling

## Phase 1: Design ✅

**Status**: Complete  
**Outputs**:
- [data-model.md](data-model.md) - Entities, relationships, validation rules
- [contracts/](contracts/) - API specifications and service contracts
- [quickstart.md](quickstart.md) - Deployment and testing guide

**Key Design Decisions**:
1. **Data Model**: File-based (no database), Dataset and DatasetMetadata entities
2. **API Contract**: REST API with OpenAPI 3.0 specification
3. **Service Architecture**: 3-tier (Landing Page, CellXGene, Nginx)
4. **Testing Strategy**: Unit, integration, contract, and end-to-end tests
5. **Deployment Model**: Single-node Docker Compose, extensible to multi-node

## Constitution Check (Re-evaluated Post-Design)

*All gates remain passed after design phase*

- [x] **Unit Testing Gate**: Testing strategy includes pytest, Docker healthchecks, contract tests, E2E tests - exceeds requirements
- [x] **Modular Architecture Gate**: Clean separation (Landing Page, CellXGene, Nginx, Dataset Validator) with Docker isolation
- [x] **Code Clarity Gate**: Documentation includes: README, architecture diagrams, API docs (OpenAPI), quickstart, troubleshooting guide, inline code comments
- [x] **Fail-Fast Gate**: Comprehensive startup validation, explicit error types, healthchecks - fully implemented
- [x] **Documentation Gate**: Multiple documentation levels created: architecture (data-model), API (contracts), deployment (quickstart), troubleshooting
- [x] **Accessibility Gate**: Quickstart guide designed for Docker beginners, step-by-step with examples, common commands documented, troubleshooting section included

**Violations**: None. Design strengthens constitutional compliance.

---

**Ready for Phase 2**: Run `/speckit.tasks` to generate implementation tasks.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
