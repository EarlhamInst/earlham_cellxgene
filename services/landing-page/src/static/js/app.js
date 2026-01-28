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
    
    // Add click handlers to entire cards
    datasets.forEach(dataset => {
        const card = document.querySelector(`[data-id="${dataset.id}"]`);
        const launchButton = document.getElementById(`launch-${dataset.id}`);
        
        if (card) {
            card.addEventListener('click', (e) => {
                // Prevent double-triggering if button is clicked
                if (e.target === launchButton || launchButton.contains(e.target)) {
                    return;
                }
                launchDataset(dataset.id);
            });
        }
        
        if (launchButton) {
            launchButton.addEventListener('click', (e) => {
                e.stopPropagation();
                launchDataset(dataset.id);
            });
        }
    });
}

/**
 * Create HTML for a dataset card
 */
function createDatasetCard(dataset) {
    // Estimate loading time based on file size (rough approximation)
    const estimateLoadingTime = (sizeStr) => {
        if (!sizeStr) return '';
        const match = sizeStr.match(/([\d.]+)\s*(MB|GB)/);
        if (!match) return '';
        const size = parseFloat(match[1]);
        const unit = match[2];
        const sizeInMB = unit === 'GB' ? size * 1024 : size;
        
        if (sizeInMB < 100) return '~30 seconds';
        if (sizeInMB < 1000) return '~1 minute';
        if (sizeInMB < 3000) return '~2 minutes';
        return '~3 minutes';
    };
    
    const loadTime = estimateLoadingTime(dataset.file_size_human);
    
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
        </div>
    `;
}

/**
 * Launch a dataset in CellXGene
 */
async function launchDataset(datasetId, retryCount = 0) {
    const button = document.getElementById(`launch-${datasetId}`);
    const maxRetries = 2;
    
    try {
        // Disable button and show spinner
        button.disabled = true;
        button.innerHTML = '<span class="spinner"></span>';
        
        console.log(`Launching dataset: ${datasetId}, attempt ${retryCount + 1}`);
        
        const response = await fetch(`${API_BASE}/datasets/${datasetId}/launch`, {
            method: 'POST'
        });
        
        console.log(`Launch response status: ${response.status}`);
        
        if (!response.ok) {
            const errorData = await response.json();
            console.error(`Launch failed:`, errorData);
            // Create error object with full context
            const error = new Error(errorData.message || 'Failed to launch dataset');
            error.errorType = errorData.error_type;
            error.recoveryHint = errorData.recovery_hint;
            throw error;
        }
        
        const data = await response.json();
        console.log(`Launch successful, starting status polling...`);
        
        // Poll status until container is ready
        const cellxgeneUrl = await waitForContainerReady(datasetId);
        
        // Open CellXGene in new window
        window.open(cellxgeneUrl, '_blank');
        
        // Reset UI after short delay
        setTimeout(() => {
            button.innerHTML = '🚀 Launch in CellXGene';
            button.disabled = false;
        }, 2000);
        
        console.log(`Launched dataset: ${datasetId}`);
    } catch (error) {
        console.error('Error launching dataset:', error);
        
        // Check if this looks like an OOM error
        const isOOM = error.message.includes('memory') || 
                      error.message.includes('OOM') || 
                      error.message.includes('killed') ||
                      error.message.includes('137') ||
                      error.errorType === 'ContainerLaunchError';
        
        // Check if timeout
        const isTimeout = error.message.includes('too long') || 
                         error.message.includes('timeout');
        
        // DON'T retry OOM errors - they will just fail again
        // Only retry timeouts
        if (retryCount < maxRetries && isTimeout && !isOOM) {
            console.log(`Retrying launch (attempt ${retryCount + 1}/${maxRetries})...`);
            // Wait a bit before retrying
            await new Promise(resolve => setTimeout(resolve, 2000));
            return launchDataset(datasetId, retryCount + 1);
        }
        
        // Show appropriate error message
        let errorTitle = 'Launch Failed';
        let errorHint = error.recoveryHint || 'Please try again or contact support.';
        
        if (isOOM) {
            errorTitle = 'Out of Memory';
            // Use the hint from API if available, otherwise use default
            if (!error.recoveryHint) {
                errorHint = 'This dataset is too large for current system resources. Try closing other running containers or contact the administrator to increase memory limits.';
            }
        } else if (isTimeout) {
            errorTitle = 'Timeout';
            if (!error.recoveryHint) {
                errorHint = 'The dataset is taking longer than expected to load. Large files (>4GB) may need more time. You can try again or contact the administrator.';
            }
        }
        
        showError(errorTitle, error.message, errorHint);
        
        // Show error state on button
        button.innerHTML = '❌ Failed - Try Again';
        button.disabled = false;
        button.style.background = '#dc3545';
        
        // Reset button after 3 seconds
        setTimeout(() => {
            button.innerHTML = '🚀 Launch in CellXGene';
            button.style.background = '';
        }, 3000);
    }
}

/**
 * Wait for container to be ready by polling status endpoint
 */
async function waitForContainerReady(datasetId, maxAttempts = 180) {
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
        try {
            const response = await fetch(`${API_BASE}/datasets/${datasetId}/status`);
            
            if (!response.ok) {
                throw new Error('Failed to check container status');
            }
            
            const status = await response.json();
            
            console.log(`Status check for ${datasetId}:`, status);
            
            // Check for container failure - these are fatal errors that should not be retried
            if (status.error) {
                console.error(`Fatal error detected for ${datasetId}:`, status);
                if (status.status === 'oom_killed') {
                    throw new Error('Container killed due to out of memory (OOM). This dataset is too large.');
                } else {
                    throw new Error(status.message || 'Container failed to start');
                }
            }
            
            if (status.ready && status.cellxgene_url) {
                return status.cellxgene_url;
            }
            
            // Wait 1 second before next check
            await new Promise(resolve => setTimeout(resolve, 1000));
            
        } catch (error) {
            // If the error message indicates a fatal container failure, propagate it immediately
            if (error.message.includes('OOM') || 
                error.message.includes('killed') || 
                error.message.includes('Container failed')) {
                throw error;  // Don't retry, let the outer catch handle it
            }
            
            // For other errors (network issues, etc), log and continue trying
            console.warn(`Status check attempt ${attempt + 1} failed:`, error.message);
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
    
    // Scroll to error message so user sees it
    errorDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
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
