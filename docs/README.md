# CellXGene Explorer Documentation

Complete documentation for the CellXGene Explorer project.

## Getting Started

- **[Main README](../README.md)** - Project overview, quick start, and features
- **[Deployment Guide](deployment.md)** - Step-by-step deployment to remote VMs

## Architecture & Design

- **[Architecture](architecture.md)** - System design, components, and data flow
- **[Dynamic Containers](dynamic-containers.md)** - How on-demand container spawning works
- **[Inactivity Timeout](inactivity-timeout.md)** - Automatic container cleanup after 48 hours

## Usage Guides

- **[Adding Datasets](adding-datasets.md)** - How to add new datasets to the catalog
- **[API Documentation](api-documentation.md)** - REST API endpoints and usage

## Customization

- **[Earlham Styling](earlham-styling.md)** - Branding and design implementation

## Operations

- **[Troubleshooting](troubleshooting.md)** - Common issues and solutions
- **[CI Fixes](ci-fixes.md)** - CI/CD pipeline configuration notes

## Quick Links

### Common Tasks

- **Deploy to VM**: See [deployment.md](deployment.md) → Step-by-step guide
- **Add a dataset**: See [adding-datasets.md](adding-datasets.md) → Dataset requirements
- **Fix errors**: See [troubleshooting.md](troubleshooting.md) → Common issues
- **Understand system**: See [architecture.md](architecture.md) → Component overview

### API Reference

- `GET /api/datasets` - List all datasets
- `POST /api/datasets/{id}/launch` - Launch CellXGene for a dataset
- `GET /api/datasets/{id}/status` - Check container status
- `POST /api/datasets/{id}/stop` - Stop a running container
- `GET /api/admin/containers` - Admin panel data

Full API documentation: [api-documentation.md](api-documentation.md)

## Document Index

| Document | Purpose | Audience |
|----------|---------|----------|
| [architecture.md](architecture.md) | System design and components | Developers |
| [deployment.md](deployment.md) | VM deployment guide | DevOps/Admins |
| [api-documentation.md](api-documentation.md) | REST API reference | Developers |
| [adding-datasets.md](adding-datasets.md) | Dataset management | Admins |
| [troubleshooting.md](troubleshooting.md) | Problem resolution | All users |
| [dynamic-containers.md](dynamic-containers.md) | Container lifecycle | Developers |
| [inactivity-timeout.md](inactivity-timeout.md) | Auto-cleanup system | Admins |
| [earlham-styling.md](earlham-styling.md) | Branding guidelines | Designers |
| [ci-fixes.md](ci-fixes.md) | CI/CD notes | Developers |

## Contributing

When adding new documentation:

1. Create `.md` file in the `docs/` directory
2. Add entry to this README's index table
3. Link from main README.md if it's user-facing
4. Follow existing documentation style
