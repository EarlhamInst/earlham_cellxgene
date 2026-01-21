# CellXGene Explorer

A self-contained Docker-based environment for exploring curated single-cell datasets using CellXGene. Researchers can browse available datasets through a web interface and launch CellXGene for interactive visualization.

## Features

- 🔬 **Dataset Catalog**: Browse curated single-cell datasets with metadata
- 🚀 **One-Click Launch**: Launch CellXGene viewer for any dataset
- 🐳 **Docker-Based**: Fully containerized for easy deployment
- 📦 **Volume-Mounted Storage**: Add datasets without rebuilding containers
- 🔌 **Extensible**: Add additional services via Docker Compose
- ⚡ **High Concurrency**: Supports 10 concurrent users with 200GB memory allocation

## Quick Start

### Prerequisites

- Docker 20.10+ and Docker Compose 2.0+
- 210GB+ available RAM for full 10-worker configuration
- Linux host (Ubuntu 20.04+, CentOS 8+) or macOS with Docker Desktop

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd cellxgene_stack
```

2. Copy the environment template:
```bash
cp .env.example .env
```

3. Add your datasets to the data directory:
```bash
mkdir -p data/datasets data/logs
# Copy your .h5ad files to data/datasets/
# Metadata is read directly from the h5ad files
```

4. Start the services:
```bash
docker-compose up -d
```

5. Access the landing page at `http://localhost` (or your configured port)

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                         Nginx                           │
│              (Reverse Proxy & Routing)                  │
└─────────────────┬───────────────────────┬───────────────┘
                  │                       │
         ┌────────▼────────┐     ┌───────▼────────┐
         │  Landing Page   │     │   CellXGene    │
         │    (Flask)      │     │  (Gunicorn +   │
         │                 │     │   Uvicorn)     │
         │  - Dataset List │     │  - 10 Workers  │
         │  - Metadata API │     │  - 20GB each   │
         └────────┬────────┘     └───────┬────────┘
                  │                      │
                  └──────────┬───────────┘
                             │
                    ┌────────▼────────┐
                    │  Volume Mount   │
                    │  data/datasets/ │
                    │  - *.h5ad files │
                    └─────────────────┘
```

### Components

- **Nginx**: Reverse proxy routing requests to appropriate services
  - `/` → Landing page web interface
  - `/api/` → Landing page REST API
  - `/cellxgene/` → CellXGene visualization service

- **Landing Page Service**: Python Flask/FastAPI application
  - Scans data directory for h5ad files
  - Extracts embedded metadata from each file
  - Validates metadata against singlecellschemas.org standard
  - Provides REST API for dataset catalog
  - Serves web UI for dataset selection

- **CellXGene Service**: CellXGene v2.x with Gunicorn
  - 10 Uvicorn workers (20GB each)
  - Interactive single-cell data visualization
  - Supports clustering, filtering, gene expression analysis

## Configuration

Edit `.env` to customize:

- **Ports**: Change `NGINX_PORT`, `LANDING_PAGE_PORT`, `CELLXGENE_PORT`
- **Workers**: Adjust `CELLXGENE_WORKERS` (reduces memory if < 10)
- **Memory**: Modify `CELLXGENE_MEMORY_PER_WORKER_GB`
- **Host Paths**: Set `HOST_DATA_DIRECTORY` and `HOST_LOG_DIRECTORY` to absolute paths on your host machine
- **Container Paths**: Set `DATA_DIRECTORY`, `LOG_DIRECTORY` (internal container paths)

**Important**: Before deploying, copy `.env.example` to `.env` and update `HOST_DATA_DIRECTORY` and `HOST_LOG_DIRECTORY` with your actual paths.

## Adding Datasets

1. Place your `.h5ad` file in `data/datasets/`
2. Ensure your h5ad file has metadata embedded in the `.uns` attribute
3. Restart the services: `docker-compose restart landing-page`

The system will automatically extract metadata from the h5ad file's `.uns` attribute.
Required metadata fields can be stored under `adata.uns['metadata']`:
- `name`: Dataset name
- `description`: Dataset description  
- `organism`: Organism name
- `tissue`: Tissue type
- `assay`: Assay technology

Cell and gene counts are automatically extracted from the data dimensions.

Example of adding metadata to an h5ad file:
```python
import anndata

adata = anndata.read_h5ad("your_dataset.h5ad")
adata.uns['metadata'] = {
    "name": "PBMC 3k Dataset",
    "description": "3k PBMCs from a Healthy Donor",
    "organism": "Homo sapiens",
    "tissue": "peripheral blood",
    "assay": "10x 3' v2"
}
adata.write_h5ad("your_dataset.h5ad")
```

## Development

See [docs/architecture.md](docs/architecture.md) for detailed architecture documentation.

See [docs/deployment.md](docs/deployment.md) for OpenNebula/CyVerse deployment instructions.

## Testing

Run tests with:
```bash
# Unit tests
pytest services/landing-page/tests/unit/

# Integration tests
pytest services/landing-page/tests/integration/

# End-to-end tests
pytest tests/e2e/
```

## Troubleshooting

See [docs/troubleshooting.md](docs/troubleshooting.md) for common issues and solutions.

## Constitutional Compliance

This project follows the constitution defined in `.specify/memory/constitution.md`:

- ✅ **Unit Testing**: 80%+ test coverage with pytest
- ✅ **Modular Architecture**: Containerized services with clear boundaries
- ✅ **Code Clarity**: Comprehensive documentation and comments
- ✅ **Fail-Fast**: Startup validation with explicit error messages
- ✅ **Documentation**: README, API docs, deployment guides, troubleshooting
- ✅ **Accessibility**: Designed for users with varying technical expertise

## License

[Specify your license here]

## Support

For issues or questions, please [open an issue](link-to-issues) or consult the documentation in the `docs/` directory.
