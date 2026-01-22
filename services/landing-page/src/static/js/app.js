/**
 * CellXGene Explorer - Main Application JavaScript
 * 
 * Constitutional Alignment:
 * - Principle IV (Fail-Fast): Clear error handling and user feedback
 * - Principle VI (Accessibility): User-friendly interactions
 */

// API base URL
const API_BASE = '/api';

// State management
let allDatasets = [];
let filteredDatasets = [];
let statistics = {};

/**
 * Initialize application on page load
 */
document.addEventListener('DOMContentLoaded', async () => {
    console.log('CellXGene Explorer initializing...');
    
    // Setup event listeners
    setupEventListeners();
    
    // Load initial data
    await loadStatistics();
    await loadDatasets();
});

/**
 * Setup all event listeners
 */
function setupEventListeners() {
    // Search
    document.getElementById('search-button').addEventListener('click', handleSearch);
    document.getElementById('search-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleSearch();
    });
    
    // Filters
    document.getElementById('filter-organism').addEventListener('change', applyFilters);
    document.getElementById('filter-tissue').addEventListener('change', applyFilters);
    document.getElementById('filter-assay').addEventListener('change', applyFilters);
    document.getElementById('sort-by').addEventListener('change', applyFilters);
    
    // Clear filters
    document.getElementById('clear-filters').addEventListener('click', clearFilters);
    document.getElementById('reset-filters')?.addEventListener('click', clearFilters);
}

/**
 * Load catalog statistics
 */
async function loadStatistics() {
    try {
        const response = await fetch(`${API_BASE}/statistics`);
        if (!response.ok) throw new Error('Failed to load statistics');
        
        statistics = await response.json();
        displayStatistics(statistics);
    } catch (error) {
        console.error('Error loading statistics:', error);
    }
}

/**
 * Display catalog statistics
 */
function displayStatistics(stats) {
    document.getElementById('stat-datasets').textContent = stats.total_datasets || 0;
    document.getElementById('stat-cells').textContent = formatNumber(stats.total_cells || 0);
    document.getElementById('stat-organisms').textContent = stats.unique_organisms || 0;
    document.getElementById('stat-tissues').textContent = stats.unique_tissues || 0;
    
    // Populate filter dropdowns
    populateFilterDropdown('filter-organism', stats.organisms || []);
    populateFilterDropdown('filter-tissue', stats.tissues || []);
    populateFilterDropdown('filter-assay', stats.assays || []);
}

/**
 * Populate a filter dropdown with options
 */
function populateFilterDropdown(elementId, options) {
    const select = document.getElementById(elementId);
    const currentValue = select.value;
    
    // Keep the "All" option
    select.innerHTML = select.children[0].outerHTML;
    
    options.forEach(option => {
        const optionElement = document.createElement('option');
        optionElement.value = option;
        optionElement.textContent = option;
        select.appendChild(optionElement);
    });
    
    // Restore previous selection if it exists
    if (currentValue && options.includes(currentValue)) {
        select.value = currentValue;
    }
}

/**
 * Load datasets from API
 */
async function loadDatasets() {
    showLoading(true);
    hideError();
    
    try {
        const response = await fetch(`${API_BASE}/datasets`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        allDatasets = data.datasets || [];
        filteredDatasets = allDatasets;
        
        displayDatasets(filteredDatasets);
        showLoading(false);
        
        console.log(`Loaded ${allDatasets.length} datasets`);
    } catch (error) {
        showLoading(false);
        showError('Failed to load datasets', error.message, 'Please check that the server is running and try again.');
        console.error('Error loading datasets:', error);
    }
}

/**
 * Display datasets in the grid
 */
function displayDatasets(datasets) {
    const grid = document.getElementById('dataset-grid');
    const noResults = document.getElementById('no-results');
    
    if (datasets.length === 0) {
        grid.innerHTML = '';
        noResults.style.display = 'block';
        return;
    }
    
    noResults.style.display = 'none';
    grid.innerHTML = datasets.map(dataset => createDatasetCard(dataset)).join('');
    
    // Add click handlers to launch buttons
    datasets.forEach(dataset => {
        const button = document.getElementById(`launch-${dataset.id}`);
        if (button) {
            button.addEventListener('click', () => launchDataset(dataset.id));
        }
    });
}

/**
 * Create HTML for a dataset card
 */
function createDatasetCard(dataset) {
    return `
        <div class="dataset-card" data-id="${dataset.id}">
            <h3>${escapeHtml(dataset.display_name)}</h3>
            <p class="description">${escapeHtml(dataset.description)}</p>
            
            <div class="dataset-metadata">
                <div class="metadata-item">
                    <span class="metadata-label">Organism</span>
                    <span class="metadata-value">${escapeHtml(dataset.organism)}</span>
                </div>
                <div class="metadata-item">
                    <span class="metadata-label">Tissue</span>
                    <span class="metadata-value">${escapeHtml(dataset.tissue)}</span>
                </div>
                <div class="metadata-item">
                    <span class="metadata-label">Assay</span>
                    <span class="metadata-value">${escapeHtml(dataset.assay)}</span>
                </div>
                <div class="metadata-item">
                    <span class="metadata-label">Cells</span>
                    <span class="metadata-value">${formatNumber(dataset.cell_count)}</span>
                </div>
                <div class="metadata-item">
                    <span class="metadata-label">Genes</span>
                    <span class="metadata-value">${formatNumber(dataset.gene_count)}</span>
                </div>
                <div class="metadata-item">
                    <span class="metadata-label">Size</span>
                    <span class="metadata-value">${dataset.file_size_human || 'N/A'}</span>
                </div>
            </div>
            
            <button id="launch-${dataset.id}" class="launch-button">
                🚀 Launch in CellXGene
            </button>
            <div id="progress-${dataset.id}" class="launch-progress" style="display: none;">
                <div class="progress-bar-container">
                    <div id="progress-bar-${dataset.id}" class="progress-bar"></div>
                </div>
                <div id="progress-text-${dataset.id}" class="progress-text">Loading...</div>
            </div>
        </div>
    `;
}

/**
 * Launch a dataset in CellXGene
 */
async function launchDataset(datasetId) {
    const button = document.getElementById(`launch-${datasetId}`);
    const progressContainer = document.getElementById(`progress-${datasetId}`);
    const progressBar = document.getElementById(`progress-bar-${datasetId}`);
    const progressText = document.getElementById(`progress-text-${datasetId}`);
    const originalText = button.textContent;
    
    try {
        // Disable button and show progress bar
        button.disabled = true;
        button.style.display = 'none';
        progressContainer.style.display = 'block';
        progressBar.style.width = '0%';
        progressText.textContent = '🚀 Launching...';
        
        const response = await fetch(`${API_BASE}/datasets/${datasetId}/launch`, {
            method: 'POST'
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.message || 'Failed to launch dataset');
        }
        
        const data = await response.json();
        
        // Show initial progress
        progressBar.style.width = '10%';
        progressText.textContent = '⏳ Loading data...';
        
        // Poll status until container is ready (with progress updates)
        const cellxgeneUrl = await waitForContainerReady(datasetId, progressBar, progressText);
        
        // Complete progress
        progressBar.style.width = '100%';
        progressText.textContent = '✓ Ready! Opening...';
        
        // Open CellXGene in new window
        window.open(cellxgeneUrl, '_blank');
        
        // Reset UI after short delay
        setTimeout(() => {
            button.style.display = 'block';
            progressContainer.style.display = 'none';
            button.disabled = false;
        }, 2000);
        
        console.log(`Launched dataset: ${datasetId}`);
    } catch (error) {
        showError('Launch Failed', error.message, 'Please check that CellXGene service is running.');
        console.error('Error launching dataset:', error);
        
        // Reset UI
        button.style.display = 'block';
        progressContainer.style.display = 'none';
        button.disabled = false;
    }
}

/**
 * Wait for container to be ready by polling status endpoint
 */
async function waitForContainerReady(datasetId, progressBar, progressText, maxAttempts = 180) {
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
        try {
            const response = await fetch(`${API_BASE}/datasets/${datasetId}/status`);
            
            if (!response.ok) {
                throw new Error('Failed to check container status');
            }
            
            const status = await response.json();
            
            if (status.ready && status.cellxgene_url) {
                return status.cellxgene_url;
            }
            
            // Calculate progress (10-95% range, with different rates for different phases)
            const elapsed = attempt + 1;
            let progress, message;
            
            if (elapsed < 30) {
                // Fast progress in first 30 seconds (10-50%)
                progress = 10 + (elapsed / 30) * 40;
                message = `⏳ Loading (${elapsed}s)...`;
            } else if (elapsed < 90) {
                // Slower progress for large files (50-80%)
                progress = 50 + ((elapsed - 30) / 60) * 30;
                message = `⏳ Loading large file (${elapsed}s)...`;
            } else {
                // Very slow progress near the end (80-95%)
                progress = 80 + ((elapsed - 90) / 90) * 15;
                message = `⏳ Almost ready (${elapsed}s)...`;
            }
            
            // Update progress bar and text
            progressBar.style.width = `${Math.min(progress, 95)}%`;
            progressText.textContent = message;
            
            // Wait 1 second before next check
            await new Promise(resolve => setTimeout(resolve, 1000));
            
        } catch (error) {
            console.warn(`Status check attempt ${attempt + 1} failed:`, error);
            // Continue trying
            await new Promise(resolve => setTimeout(resolve, 1000));
        }
    }
    
    throw new Error('Container took too long to start (>3 minutes). Large files may require more time.');
}

/**
 * Handle search
 */
function handleSearch() {
    const query = document.getElementById('search-input').value;
    if (query) {
        applyFilters();
    }
}

/**
 * Apply all filters and sorting
 */
function applyFilters() {
    const searchQuery = document.getElementById('search-input').value.toLowerCase();
    const organism = document.getElementById('filter-organism').value;
    const tissue = document.getElementById('filter-tissue').value;
    const assay = document.getElementById('filter-assay').value;
    const sortBy = document.getElementById('sort-by').value;
    
    // Filter datasets
    filteredDatasets = allDatasets.filter(dataset => {
        // Search filter
        if (searchQuery) {
            const matchesSearch = 
                dataset.display_name.toLowerCase().includes(searchQuery) ||
                dataset.description.toLowerCase().includes(searchQuery);
            if (!matchesSearch) return false;
        }
        
        // Organism filter
        if (organism && dataset.organism !== organism) return false;
        
        // Tissue filter
        if (tissue && dataset.tissue !== tissue) return false;
        
        // Assay filter
        if (assay && dataset.assay !== assay) return false;
        
        return true;
    });
    
    // Sort datasets
    filteredDatasets = sortDatasets(filteredDatasets, sortBy);
    
    // Display filtered results
    displayDatasets(filteredDatasets);
}

/**
 * Sort datasets by specified field
 */
function sortDatasets(datasets, sortBy) {
    const sorted = [...datasets];
    
    switch (sortBy) {
        case 'cell_count':
            sorted.sort((a, b) => (b.cell_count || 0) - (a.cell_count || 0));
            break;
        case 'file_size':
            sorted.sort((a, b) => (b.file_size_bytes || 0) - (a.file_size_bytes || 0));
            break;
        case 'name':
        default:
            sorted.sort((a, b) => a.display_name.localeCompare(b.display_name));
            break;
    }
    
    return sorted;
}

/**
 * Clear all filters
 */
function clearFilters() {
    document.getElementById('search-input').value = '';
    document.getElementById('filter-organism').value = '';
    document.getElementById('filter-tissue').value = '';
    document.getElementById('filter-assay').value = '';
    document.getElementById('sort-by').value = 'name';
    
    filteredDatasets = allDatasets;
    displayDatasets(filteredDatasets);
}

/**
 * Show/hide loading indicator
 */
function showLoading(show) {
    document.getElementById('loading').style.display = show ? 'block' : 'none';
    document.getElementById('dataset-grid').style.display = show ? 'none' : 'grid';
}

/**
 * Show error message
 */
function showError(title, message, hint) {
    const errorDiv = document.getElementById('error-message');
    document.getElementById('error-title').textContent = title;
    document.getElementById('error-text').textContent = message;
    document.getElementById('error-hint').textContent = hint || '';
    errorDiv.style.display = 'block';
}

/**
 * Hide error message
 */
function hideError() {
    document.getElementById('error-message').style.display = 'none';
}

/**
 * Format large numbers with commas
 */
function formatNumber(num) {
    if (num === null || num === undefined) return 'N/A';
    return num.toLocaleString();
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
