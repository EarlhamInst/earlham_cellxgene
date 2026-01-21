# Quickstart Guide: CellXGene Explorer

**Feature**: 001-cellxgene-explorer  
**Date**: 2026-01-14  
**Purpose**: Quick deployment and validation guide

## Prerequisites

- **Operating System**: Linux (Ubuntu 20.04+ or CentOS 8+)
- **Docker**: Version 20.10+
- **Docker Compose**: Version 2.0+
- **Disk Space**: 300GB+ (for datasets and logs)
- **Memory**: 48GB+ RAM
- **CPU**: 8+ cores recommended
- **Network**: Open port 80 (and 443 for HTTPS)

## Quick Start (5 Minutes)

### Step 1: Clone Repository

```bash
git clone https://github.com/your-org/cellxgene-stack.git
cd cellxgene-stack
```

### Step 2: Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit configuration (use your preferred editor)
nano .env
```

**Minimum required configuration**:
```bash
DATA_DIRECTORY=/data/datasets
LOG_DIRECTORY=/data/logs
NGINX_PORT=80
```

### Step 3: Add Example Dataset

**Option A: Download from 10x Genomics (Recommended)**

Visit the [10x Genomics datasets page](https://www.10xgenomics.com/datasets) and download a PBMC dataset:

```bash
# Create data directories
mkdir -p /data/datasets /data/logs

# Download PBMC 3k dataset (update URL if needed)
# Alternative: Visit https://www.10xgenomics.com/datasets/3-k-pbm-cs-from-a-healthy-donor-1-standard-1-1-0
# and download the "Feature / cell matrix HDF5 (filtered)" file

# After downloading, convert to h5ad format:
# Place the downloaded .h5 file in /data/datasets/ and rename to .h5ad
# Example: mv filtered_feature_bc_matrix.h5 /data/datasets/pbmc_3k.h5ad
```

**Option B: Create Minimal Test Dataset with Python**

```bash
# Install dependencies
pip install scanpy numpy pandas

# Create test dataset
python3 << 'PYTHON_SCRIPT'
import scanpy as sc
import numpy as np
import pandas as pd

# Create minimal test dataset
n_obs = 1000  # 1000 cells
n_vars = 500  # 500 genes

# Random expression matrix
X = np.random.negative_binomial(5, 0.3, (n_obs, n_vars))

# Create AnnData object
adata = sc.AnnData(
    X=X,
    obs=pd.DataFrame(index=[f"Cell_{i}" for i in range(n_obs)]),
    var=pd.DataFrame(index=[f"Gene_{i}" for i in range(n_vars)])
)

# Add basic preprocessing
sc.pp.normalize_total(adata, target_sum=1e4)
sc.pp.log1p(adata)
sc.pp.highly_variable_genes(adata)
sc.pp.pca(adata)
sc.pp.neighbors(adata)
sc.tl.umap(adata)
sc.tl.leiden(adata)

# Save
adata.write_h5ad("/data/datasets/test_dataset.h5ad")
print("Test dataset created: /data/datasets/test_dataset.h5ad")
PYTHON_SCRIPT
```

**Create metadata file** (adjust `dataset_id` to match your h5ad filename):

```bash
cat > /data/datasets/pbmc_3k.json <<'EOF'
{
  "title": "PBMC 3k Dataset",
  "description": "3,000 Peripheral Blood Mononuclear Cells from a Healthy Donor",
  "schema_version": "5.0.0",
  "organism": {
    "ontology": "NCBITaxon",
    "ontology_id": "NCBITaxon:9606",
    "text": "Homo sapiens"
  },
  "tissue": [{
    "ontology": "UBERON",
    "ontology_id": "UBERON:0000178",
    "text": "blood"
  }],
  "cell_count": 2700,
  "feature_count": 32738,
  "dataset_id": "pbmc_3k"
}
EOF
```

Or for the test dataset:

```bash
cat > /data/datasets/test_dataset.json <<'EOF'
{
  "title": "Test Dataset",
  "description": "Minimal test dataset for CellXGene Explorer",
  "schema_version": "5.0.0",
  "organism": {
    "ontology": "NCBITaxon",
    "ontology_id": "NCBITaxon:9606",
    "text": "Homo sapiens"
  },
  "tissue": [{
    "ontology": "UBERON",
    "ontology_id": "UBERON:0000001",
    "text": "test tissue"
  }],
  "cell_count": 1000,
  "feature_count": 500,
  "dataset_id": "test_dataset"
}
EOF
```

**Option C: Use Your Own Dataset**

If you already have h5ad files, simply copy them to `/data/datasets/` and create matching metadata JSON files.

### Step 4: Launch Stack

```bash
# Build and start all services
docker-compose up -d

# Watch logs (Ctrl+C to exit)
docker-compose logs -f
```

Wait for message: `All datasets validated. Service ready.`

### Step 5: Access Application

Open browser to: **http://localhost**

You should see:
1. Landing page with dataset catalog
2. "PBMC 3k Dataset" listed
3. Click dataset → CellXGene launches

## Validation Checklist

Use this checklist to verify deployment:

- [ ] All containers are running: `docker-compose ps`
- [ ] Health checks passing: `docker-compose ps` shows "healthy"
- [ ] Landing page accessible at http://localhost
- [ ] API responds: `curl http://localhost/api/health`
- [ ] Dataset appears in catalog
- [ ] Clicking dataset launches CellXGene
- [ ] CellXGene loads and displays cells
- [ ] No errors in logs: `docker-compose logs | grep ERROR`

## Common Commands

```bash
# View all logs
docker-compose logs

# View specific service logs
docker-compose logs landing-page
docker-compose logs cellxgene

# Check service health
docker-compose ps

# Restart services
docker-compose restart

# Stop all services
docker-compose down

# Stop and remove volumes (WARNING: deletes data)
docker-compose down -v

# Rebuild after code changes
docker-compose build
docker-compose up -d
```

## Adding a New Dataset

### Manual Method (Simple)

1. **Prepare your h5ad file** (must be valid AnnData format):
   ```bash
   cp your_dataset.h5ad /data/datasets/
   ```

2. **Create metadata JSON**:
   ```bash
   cat > /data/datasets/your_dataset.json <<'EOF'
   {
     "title": "Your Dataset Name",
     "description": "Description of your dataset",
     "schema_version": "5.0.0",
     "organism": {
       "ontology": "NCBITaxon",
       "ontology_id": "NCBITaxon:9606",
       "text": "Homo sapiens"
     },
     "cell_count": 10000,
     "dataset_id": "your_dataset"
   }
   EOF
   ```

3. **Restart services** (to trigger validation):
   ```bash
   docker-compose restart landing-page
   ```

4. **Verify** dataset appears in catalog:
   ```bash
   curl http://localhost/api/datasets | jq '.datasets[] | select(.id=="your_dataset")'
   ```

### Validation Script Method (Recommended)

```bash
# Validate before restart (catches errors early)
docker-compose exec landing-page python /app/scripts/validate-datasets.py \
    --data-dir /data/datasets \
    --dataset your_dataset

# If validation passes, restart
docker-compose restart landing-page
```

## Testing User Stories

### User Story 1: Dataset Selection and Exploration (P1)

**Test**: Can users browse and launch datasets?

```bash
# 1. View landing page
curl http://localhost/ | grep "CellXGene Explorer"

# 2. List datasets via API
curl http://localhost/api/datasets | jq '.datasets[0]'

# 3. Launch dataset
curl -X POST http://localhost/api/datasets/pbmc_3k/launch | jq '.viewer_url'

# 4. Open viewer URL in browser (manual step)
# Expected: CellXGene loads and shows cells
```

**Success Criteria**:
- Dataset catalog displays in < 2 seconds
- Clicking dataset loads CellXGene in < 30 seconds
- All CellXGene features (filtering, clustering) work

### User Story 2: Dataset Management (P2)

**Test**: Can admins add/remove datasets?

```bash
# 1. Add new dataset (see "Adding a New Dataset" above)

# 2. Verify it appears
curl http://localhost/api/datasets | jq '.total'
# Expected: count increases by 1

# 3. Remove dataset
rm /data/datasets/your_dataset.h5ad /data/datasets/your_dataset.json
docker-compose restart landing-page

# 4. Verify it's gone
curl http://localhost/api/datasets | jq '.total'
# Expected: count decreases by 1
```

**Success Criteria**:
- Adding dataset takes < 5 minutes (including metadata creation)
- Service restarts without errors
- Dataset appears/disappears from catalog immediately

### User Story 3: Additional Services (P3)

**Test**: Can additional services be integrated?

```bash
# 1. Add new service to docker-compose.yml
cat >> docker-compose.yml <<'EOF'
  documentation:
    image: nginx:alpine
    volumes:
      - ./docs:/usr/share/nginx/html:ro
    ports:
      - "8080:80"
EOF

# 2. Start new service
docker-compose up -d documentation

# 3. Verify accessible
curl http://localhost:8080/
```

**Success Criteria**:
- New service starts without affecting existing services
- Service accessible via configured port
- Data can be shared via volumes if needed

## Troubleshooting

### Issue: Containers won't start

**Symptoms**: `docker-compose up` fails

**Solution**:
```bash
# Check logs
docker-compose logs

# Common causes:
# - Port 80 already in use: change NGINX_PORT in .env
# - Data directory not found: create /data/datasets
# - Permission issues: sudo chown -R 1000:1000 /data
```

### Issue: Dataset validation fails

**Symptoms**: "Dataset validation failed" in logs

**Solution**:
```bash
# View validation errors
docker-compose logs landing-page | grep "validation"

# Common causes:
# - Missing metadata JSON: create {dataset}.json
# - Invalid h5ad file: verify with Python:
python -c "import anndata; anndata.read_h5ad('/data/datasets/your_dataset.h5ad')"

# - JSON schema mismatch: validate at http://singlecellschemas.org
```

### Issue: CellXGene won't load dataset

**Symptoms**: 503 error or blank page

**Solution**:
```bash
# Check CellXGene logs
docker-compose logs cellxgene

# Check memory usage
docker stats

# Common causes:
# - All workers busy: wait or scale up worker count
# - Out of memory: increase Docker memory limit or reduce worker count
# - Invalid dataset: check validation logs
```

### Issue: Slow performance

**Symptoms**: > 30 seconds to load dataset

**Solution**:
```bash
# Check system resources
docker stats

# Increase worker memory (if available):
# Edit docker-compose.yml, increase memory limit

# Reduce worker count if constrained:
# Edit .env: WORKER_COUNT=5

# Check disk I/O:
iostat -x 1
```

## Monitoring

### Basic Health Checks

```bash
# All services healthy
docker-compose ps

# API health endpoint
curl http://localhost/api/health

# Check dataset count
curl http://localhost/api/health | jq '.dataset_count'

# View access logs
tail -f /data/logs/access.log | jq '.'
```

### Advanced Monitoring (Optional)

Add Prometheus + Grafana for metrics:

```yaml
# Add to docker-compose.yml
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    volumes:
      - grafana-data:/var/lib/grafana

volumes:
  prometheus-data:
  grafana-data:
```

## Deployment on OpenNebula/CyVerse

### OpenNebula

1. **Create VM** with specifications:
   - OS: Ubuntu 20.04
   - RAM: 48GB
   - Disk: 300GB
   - vCPUs: 8

2. **Install Docker**:
   ```bash
   curl -fsSL https://get.docker.com | sh
   sudo usermod -aG docker $USER
   ```

3. **Follow Quick Start** above

4. **Configure Firewall**:
   ```bash
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw enable
   ```

### CyVerse

1. **Launch Instance** (Atmosphere/CACAO):
   - Image: Ubuntu 20.04
   - Size: Large (48GB RAM)

2. **Attach Volume** for datasets:
   ```bash
   sudo mkfs.ext4 /dev/vdb
   sudo mkdir /data
   sudo mount /dev/vdb /data
   ```

3. **Install Docker** and **Follow Quick Start**

4. **Use External IP** to access

## Performance Benchmarks

Expected performance on recommended hardware (48GB RAM, 8 cores):

- **Startup time**: 30-60 seconds
- **Dataset scan**: 1-2 seconds per dataset
- **CellXGene launch**: 10-30 seconds
- **Concurrent users**: 10 (one per worker)
- **Dataset size**: Up to 10GB per dataset

## Security Notes

- **No authentication**: Open access by design (FAIR principles)
- **Firewall**: Recommended to restrict IP ranges
- **HTTPS**: Configure Nginx SSL for production
- **Updates**: Regularly update Docker images
- **Backups**: Backup /data directory regularly

## Next Steps

- ✅ Basic deployment working
- → Add more datasets to /data/datasets
- → Configure monitoring (Prometheus/Grafana)
- → Set up automated backups
- → Add documentation service (User Story 3)
- → Configure HTTPS with Let's Encrypt

## Support

- **Logs**: `docker-compose logs`
- **Issues**: Check GitHub issues
- **Docs**: See [docs/](../docs/) directory
- **CellXGene**: https://chanzuckerberg.github.io/cellxgene/

---

**Status**: Quickstart guide complete. Ready for implementation.
