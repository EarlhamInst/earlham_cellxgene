# Adding Datasets Guide

This guide provides step-by-step instructions for:
- Preparing h5ad files with minimal or complete metadata
- Validating datasets before deployment
- Using the validation script

## Minimal Dataset Requirements

Your h5ad file must be a valid AnnData object with:

### Required Structure
- **X**: Expression matrix (cells × features)
- **obs**: Dataframe with cell information (must have row names/obs_names as cell barcodes)
- **var**: Dataframe with feature information (must have row names/var_names as feature IDs)

That's it! The system will automatically:
- Use the filename as the dataset name
- Count cells and features from the data dimensions
- Set organism, tissue, and assay to "Unknown" if not provided

## Optional Metadata

You can enhance your dataset by adding metadata in `adata.uns['metadata']`:

### Recommended Fields
- `name`: Human-readable dataset name (defaults to filename)
- `description`: Detailed description (defaults to cell/feature count)
- `organism`: Scientific name (e.g., "Homo sapiens")
- `tissue`: Tissue or organ type
- `assay`: Sequencing technology (e.g., "10x 3' v3")

### Additional Optional Fields
- `doi`: Digital Object Identifier
- `publication`: Full citation
- `contributors`: List of contributor names
- `version`: Dataset version
- `date_created`: Creation date
- `license`: Data license
- `tags`: Searchable tags

## Adding Metadata to h5ad Files

```python
import anndata

# Load your dataset
adata = anndata.read_h5ad("your_dataset.h5ad")

# Add minimal metadata (optional - system provides defaults)
adata.uns['metadata'] = {
    "name": "PBMC 3k Dataset",
    "description": "3,000 Peripheral Blood Mononuclear Cells from a Healthy Donor",
    "organism": "Homo sapiens",
    "tissue": "peripheral blood",
    "assay": "10x 3' v3"
}

# Save the file
adata.write_h5ad("your_dataset.h5ad")
```

## What You DON'T Need

These are **not required** and can be added later:
- `.uns` metadata (beyond optional metadata dictionary)
- Embeddings in `obsm` (e.g., UMAP, PCA)
- Graphs in `obsp`
- Additional layers beyond `X`
- Ontology annotations
- Experimental metadata

## Validation Process

Validate datasets before deployment:

```bash
python scripts/validate-datasets.py --data-dir data/datasets
```

This checks:
1. Valid HDF5/h5ad format
2. X matrix exists
3. obs and var dataframes exist with row names
4. Metadata can be extracted or generated

## Examples

### Minimal valid h5ad (Seurat-compatible)
```python
import anndata
import numpy as np
import pandas as pd

# Create minimal structure
X = np.random.rand(100, 50)  # 100 cells, 50 genes
obs = pd.DataFrame(index=[f"cell_{i}" for i in range(100)])
var = pd.DataFrame(index=[f"gene_{i}" for i in range(50)])

adata = anndata.AnnData(X=X, obs=obs, var=var)
adata.write_h5ad("minimal_dataset.h5ad")
# System will auto-generate: name="Minimal Dataset", description="Dataset with 100 cells and 50 features"
```

### With rich metadata
```python
# Add comprehensive metadata
adata.uns['metadata'] = {
    "name": "PBMC 10k",
    "description": "10,000 PBMCs from healthy donor",
    "organism": "Homo sapiens",
    "tissue": "peripheral blood",
    "assay": "10x 3' v3",
    "doi": "10.1234/example",
    "publication": "Smith et al. 2024"
}
adata.write_h5ad("pbmc_10k.h5ad")
```
