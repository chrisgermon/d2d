// DICOM Upload JavaScript

let selectedFiles = [];
let selectedDestination = null;
let destinations = [];
let currentStep = 1;
let validatedFiles = []; // Store validation results

// API Key Management
function getStoredApiKey() {
    return localStorage.getItem('d2d_api_key') || '';
}

function setStoredApiKey(key) {
    localStorage.setItem('d2d_api_key', key);
}

// Wrapper for fetch that handles API key authentication
async function apiFetch(url, options = {}) {
    const apiKey = getStoredApiKey();
    const headers = {};
    if (apiKey) {
        headers['X-API-Key'] = apiKey;
    }
    if (options.headers) {
        Object.assign(headers, options.headers);
    }
    const { headers: _originalHeaders, ...restOptions } = options;

    const response = await fetch(url, {
        ...restOptions,
        headers
    });

    if (response.status === 401) {
        const shouldPrompt = confirm(
            'API authentication required. Would you like to enter an API key?\n\n' +
            'Click OK to enter a key, or Cancel to go to Settings.'
        );

        if (shouldPrompt) {
            const newKey = prompt('Enter your API key:');
            if (newKey) {
                setStoredApiKey(newKey);
                headers['X-API-Key'] = newKey;
                return fetch(url, { ...restOptions, headers });
            }
        } else {
            window.location.href = '/settings';
            return response;
        }
    }

    return response;
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupUploadArea();
    setupDestinations();
    loadDestinations();
});

// Step Navigation
function updateStepIndicator(step) {
    currentStep = step;
    const steps = document.querySelectorAll('.step');
    const lines = document.querySelectorAll('.step-line');

    steps.forEach((s, index) => {
        const stepNum = index + 1;
        s.classList.remove('active', 'completed');
        if (stepNum < step) {
            s.classList.add('completed');
        } else if (stepNum === step) {
            s.classList.add('active');
        }
    });

    lines.forEach((line, index) => {
        line.classList.remove('completed');
        if (index + 1 < step) {
            line.classList.add('completed');
        }
    });
}

async function goToStep(step) {
    updateStepIndicator(step);

    // Show/hide sections based on step
    document.getElementById('files-section').style.display = step >= 1 ? 'block' : 'none';
    document.getElementById('destination-section').style.display = step >= 2 ? 'block' : 'none';
    document.getElementById('upload-section').style.display = step === 3 ? 'block' : 'none';
    document.getElementById('results-section').style.display = 'none';

    if (step === 2) {
        updateDestinationInfo();
    }

    if (step === 3) {
        // Validate files and show preview
        await validateAndPreviewFiles();
    }

    // Scroll to the relevant section
    if (step === 2) {
        document.getElementById('destination-section').scrollIntoView({ behavior: 'smooth' });
    } else if (step === 3) {
        document.getElementById('upload-section').scrollIntoView({ behavior: 'smooth' });
    }
}

// File Upload Area
function setupUploadArea() {
    const uploadArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('file-input');
    const folderInput = document.getElementById('folder-input');
    const selectFilesBtn = document.getElementById('select-files-btn');
    const selectFolderBtn = document.getElementById('select-folder-btn');

    // Prevent default click on upload area (we have buttons now)
    uploadArea.addEventListener('click', (e) => {
        // Only trigger if clicking directly on upload area, not buttons
        if (e.target === uploadArea || e.target.closest('.upload-content') && !e.target.closest('button')) {
            fileInput.click();
        }
    });

    // Button click handlers
    selectFilesBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        fileInput.click();
    });

    selectFolderBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        folderInput.click();
    });

    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });

    // Handle drop - support both files and folders
    uploadArea.addEventListener('drop', async (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');

        const items = e.dataTransfer.items;
        if (items) {
            // Use DataTransferItemList to handle folders
            await handleDroppedItems(items);
        } else {
            // Fallback for browsers that don't support items
            handleFilesSelected(e.dataTransfer.files);
        }
    });

    fileInput.addEventListener('change', (e) => {
        handleFilesSelected(e.target.files);
    });

    folderInput.addEventListener('change', (e) => {
        handleFolderSelected(e.target.files);
    });
}

// Handle dropped items (files or folders)
async function handleDroppedItems(items) {
    const files = [];
    const entries = [];

    // Get all entries first
    for (let i = 0; i < items.length; i++) {
        const item = items[i];
        if (item.webkitGetAsEntry) {
            const entry = item.webkitGetAsEntry();
            if (entry) {
                entries.push(entry);
            }
        } else if (item.kind === 'file') {
            files.push(item.getAsFile());
        }
    }

    if (entries.length > 0) {
        // Show scanning progress
        showFolderScanProgress();

        // Process entries (may include folders)
        for (const entry of entries) {
            await processEntry(entry, files);
        }

        hideFolderScanProgress();
    }

    if (files.length > 0) {
        handleFilesSelected(files);
    }
}

// Recursively process file system entries
async function processEntry(entry, files) {
    if (entry.isFile) {
        const file = await getFileFromEntry(entry);
        if (file) {
            files.push(file);
            updateScanCount(files.length);
        }
    } else if (entry.isDirectory) {
        const reader = entry.createReader();
        const entries = await readAllDirectoryEntries(reader);
        for (const childEntry of entries) {
            await processEntry(childEntry, files);
        }
    }
}

// Get file from FileSystemFileEntry
function getFileFromEntry(entry) {
    return new Promise((resolve) => {
        entry.file(
            (file) => resolve(file),
            () => resolve(null) // Ignore errors
        );
    });
}

// Read all entries from a directory (handles pagination)
function readAllDirectoryEntries(reader) {
    return new Promise((resolve) => {
        const entries = [];

        function readEntries() {
            reader.readEntries((results) => {
                if (results.length === 0) {
                    resolve(entries);
                } else {
                    entries.push(...results);
                    readEntries(); // Continue reading
                }
            }, () => resolve(entries)); // Resolve with what we have on error
        }

        readEntries();
    });
}

// Handle folder selection from input
function handleFolderSelected(files) {
    showFolderScanProgress();

    // Filter and add files
    const fileArray = Array.from(files);
    let count = 0;

    for (const file of fileArray) {
        const exists = selectedFiles.some(f => f.name === file.name && f.size === file.size && f.webkitRelativePath === file.webkitRelativePath);
        if (!exists) {
            selectedFiles.push(file);
            count++;
            updateScanCount(selectedFiles.length);
        }
    }

    hideFolderScanProgress();

    // Reset validated files when new files added
    validatedFiles = [];

    renderFilesList();
    updateContinueButton();

    if (count > 0) {
        showNotification(`Added ${count} files from folder`);
    }
}

// Folder scan progress UI
function showFolderScanProgress() {
    document.getElementById('folder-scan-progress').style.display = 'flex';
    document.getElementById('scan-count').textContent = '0';
}

function hideFolderScanProgress() {
    document.getElementById('folder-scan-progress').style.display = 'none';
}

function updateScanCount(count) {
    document.getElementById('scan-count').textContent = count;
}

function handleFilesSelected(files) {
    for (const file of files) {
        // Check if file is already selected
        const exists = selectedFiles.some(f => f.name === file.name && f.size === file.size);
        if (!exists) {
            selectedFiles.push(file);
        }
    }

    // Reset validated files when new files added
    validatedFiles = [];

    renderFilesList();
    updateContinueButton();
}

function renderFilesList() {
    const container = document.getElementById('files-list');
    const selectedFilesEl = document.getElementById('selected-files');
    const fileCountEl = document.getElementById('file-count');

    if (selectedFiles.length === 0) {
        selectedFilesEl.style.display = 'none';
        return;
    }

    selectedFilesEl.style.display = 'block';
    fileCountEl.textContent = selectedFiles.length;

    container.innerHTML = selectedFiles.map((file, index) => `
        <div class="file-card" data-index="${index}">
            <div class="file-card-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                    <polyline points="14 2 14 8 20 8"/>
                </svg>
            </div>
            <div class="file-card-info">
                <div class="file-card-name" title="${file.name}">${truncateFilename(file.name, 40)}</div>
                <div class="file-card-size">${formatFileSize(file.size)}</div>
            </div>
            <button class="file-card-remove" onclick="removeFile(${index})" title="Remove file">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="18" y1="6" x2="6" y2="18"/>
                    <line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
            </button>
        </div>
    `).join('');
}

function truncateFilename(name, maxLength) {
    if (name.length <= maxLength) return name;
    const ext = name.lastIndexOf('.');
    if (ext > 0) {
        const extension = name.substring(ext);
        const basename = name.substring(0, ext);
        const availableLength = maxLength - extension.length - 3;
        return basename.substring(0, availableLength) + '...' + extension;
    }
    return name.substring(0, maxLength - 3) + '...';
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function removeFile(index) {
    selectedFiles.splice(index, 1);
    validatedFiles = []; // Reset validation
    renderFilesList();
    updateContinueButton();
}

function clearAllFiles() {
    selectedFiles = [];
    validatedFiles = [];
    document.getElementById('file-input').value = '';
    renderFilesList();
    updateContinueButton();
}

function updateContinueButton() {
    const continueBtn = document.getElementById('continue-to-destination-btn');
    continueBtn.disabled = selectedFiles.length === 0;
}

// Destinations
function setupDestinations() {
    document.getElementById('manage-destinations-btn').addEventListener('click', () => {
        document.getElementById('destinations-modal').classList.add('active');
    });

    document.getElementById('close-modal').addEventListener('click', () => {
        document.getElementById('destinations-modal').classList.remove('active');
    });

    document.getElementById('destination-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        await saveDestination();
    });

    document.getElementById('test-connection-btn').addEventListener('click', async () => {
        await testConnection();
    });

    document.getElementById('destination-select').addEventListener('change', (e) => {
        const destName = e.target.value;
        selectedDestination = destinations.find(d => d.name === destName) || null;
        updateDestinationInfo();
        updateUploadButton();
    });
}

async function loadDestinations() {
    try {
        const response = await apiFetch('/api/destinations');
        if (!response.ok) {
            console.error('Failed to load destinations');
            return;
        }
        const data = await response.json();
        destinations = data.destinations;

        // Add default VRG PACS if no destinations exist
        if (destinations.length === 0) {
            const defaultDest = {
                name: 'VRG PACS',
                ae_title: 'AURVCMOD1',
                host: '10.17.1.21',
                port: 104,
                calling_ae_title: 'D2D_SCU'
            };
            await apiFetch('/api/destinations', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(defaultDest)
            });
            destinations = [defaultDest];
        }

        renderDestinationSelect();
        renderSavedDestinations();

        // Auto-select first destination
        if (destinations.length > 0) {
            const select = document.getElementById('destination-select');
            select.value = destinations[0].name;
            selectedDestination = destinations[0];
            updateDestinationInfo();
            updateUploadButton();
        }
    } catch (error) {
        console.error('Failed to load destinations:', error);
    }
}

function renderDestinationSelect() {
    const select = document.getElementById('destination-select');
    select.innerHTML = '<option value="">Select destination...</option>';

    destinations.forEach(dest => {
        const option = document.createElement('option');
        option.value = dest.name;
        option.textContent = `${dest.name} (${dest.ae_title} @ ${dest.host}:${dest.port})`;
        select.appendChild(option);
    });
}

function renderSavedDestinations() {
    const container = document.getElementById('saved-destinations');

    if (destinations.length === 0) {
        container.innerHTML = '<p style="color: var(--text-muted);">No saved destinations</p>';
        return;
    }

    container.innerHTML = destinations.map(dest => `
        <div class="saved-destination">
            <div class="saved-destination-info">
                <h4>${dest.name}</h4>
                <p><strong>Destination AE:</strong> ${dest.ae_title}</p>
                <p><strong>Calling AE:</strong> ${dest.calling_ae_title || 'D2D_SCU'}</p>
                <p><strong>Host:</strong> ${dest.host}:${dest.port}</p>
            </div>
            <button onclick="deleteDestination('${dest.name}')">Delete</button>
        </div>
    `).join('');
}

function updateDestinationInfo() {
    const infoEl = document.getElementById('destination-info');
    const continueBtn = document.getElementById('continue-to-upload-btn');

    if (selectedDestination) {
        document.getElementById('dest-info-name').textContent = selectedDestination.name;
        document.getElementById('dest-info-ae').textContent = selectedDestination.ae_title;
        document.getElementById('dest-info-host').textContent = selectedDestination.host;
        document.getElementById('dest-info-port').textContent = selectedDestination.port;
        document.getElementById('dest-info-calling-ae').textContent = selectedDestination.calling_ae_title || 'D2D_SCU';
        infoEl.style.display = 'block';
        continueBtn.disabled = false;
    } else {
        infoEl.style.display = 'none';
        continueBtn.disabled = true;
    }
}

function updateUploadButton() {
    const btn = document.getElementById('continue-to-upload-btn');
    btn.disabled = !selectedDestination;
}

async function saveDestination() {
    const destination = {
        name: document.getElementById('dest-name').value,
        ae_title: document.getElementById('dest-ae-title').value,
        host: document.getElementById('dest-host').value,
        port: parseInt(document.getElementById('dest-port').value),
        calling_ae_title: document.getElementById('dest-calling-ae').value || 'D2D_SCU'
    };

    showLoading('Saving destination...');

    try {
        const response = await apiFetch('/api/destinations', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(destination)
        });

        if (!response.ok) throw new Error('Failed to save destination');

        await loadDestinations();
        document.getElementById('destination-form').reset();
        showNotification('Destination saved successfully!');

    } catch (error) {
        showError('Failed to save destination: ' + error.message);
    } finally {
        hideLoading();
    }
}

async function testConnection() {
    const destination = {
        name: document.getElementById('dest-name').value,
        ae_title: document.getElementById('dest-ae-title').value,
        host: document.getElementById('dest-host').value,
        port: parseInt(document.getElementById('dest-port').value),
        calling_ae_title: document.getElementById('dest-calling-ae').value || 'D2D_SCU'
    };

    showLoading('Testing connection...');

    try {
        const response = await apiFetch('/api/destinations/verify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(destination)
        });

        const data = await response.json();

        if (response.ok) {
            showNotification('Connection successful!');
        } else {
            showError('Connection failed: ' + data.detail);
        }

    } catch (error) {
        showError('Connection failed: ' + error.message);
    } finally {
        hideLoading();
    }
}

async function deleteDestination(name) {
    if (!confirm(`Delete destination "${name}"?`)) return;

    showLoading('Deleting destination...');

    try {
        const response = await apiFetch(`/api/destinations/${encodeURIComponent(name)}`, {
            method: 'DELETE'
        });

        if (!response.ok) throw new Error('Failed to delete destination');

        await loadDestinations();

    } catch (error) {
        showError('Failed to delete destination: ' + error.message);
    } finally {
        hideLoading();
    }
}

// File Validation and Preview
async function validateAndPreviewFiles() {
    const validationLoading = document.getElementById('validation-loading');
    const previewEl = document.getElementById('dicom-preview');
    const summaryEl = document.getElementById('review-summary');
    const actionsEl = document.getElementById('upload-actions');

    // Show loading
    validationLoading.style.display = 'flex';
    previewEl.style.display = 'none';
    summaryEl.style.display = 'none';
    actionsEl.style.display = 'none';

    validatedFiles = [];

    // Validate each file
    for (const file of selectedFiles) {
        try {
            const formData = new FormData();
            formData.append('file', file);

            const response = await apiFetch('/api/dicom/validate', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();
            validatedFiles.push({
                file: file,
                ...data
            });
        } catch (error) {
            validatedFiles.push({
                file: file,
                valid: false,
                filename: file.name,
                error: error.message
            });
        }
    }

    // Hide loading
    validationLoading.style.display = 'none';

    // Render preview table
    renderPreviewTable();

    // Update summary
    updateSummary();

    // Show UI elements
    previewEl.style.display = 'block';
    summaryEl.style.display = 'block';
    actionsEl.style.display = 'flex';
}

function renderPreviewTable() {
    const tableBody = document.getElementById('preview-table-body');
    const validCount = validatedFiles.filter(f => f.valid).length;
    const invalidCount = validatedFiles.filter(f => !f.valid).length;

    document.getElementById('valid-count').textContent = validCount;
    document.getElementById('invalid-count').textContent = invalidCount;

    tableBody.innerHTML = validatedFiles.map(f => {
        const statusIcon = f.valid
            ? `<span class="status-icon status-valid" title="Valid DICOM">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                    <polyline points="22 4 12 14.01 9 11.01"/>
                </svg>
               </span>`
            : `<span class="status-icon status-invalid" title="${f.error || 'Invalid DICOM'}">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"/>
                    <line x1="15" y1="9" x2="9" y2="15"/>
                    <line x1="9" y1="9" x2="15" y2="15"/>
                </svg>
               </span>`;

        const formatDate = (dateStr) => {
            if (!dateStr || dateStr.length !== 8) return dateStr || '-';
            return `${dateStr.substring(6,8)}/${dateStr.substring(4,6)}/${dateStr.substring(0,4)}`;
        };

        const formatName = (name) => {
            if (!name) return '-';
            // Convert DICOM format (LASTNAME^FIRSTNAME) to display format
            const parts = name.split('^');
            if (parts.length >= 2) {
                return `${parts[1]} ${parts[0]}`;
            }
            return name;
        };

        return `
            <tr class="${f.valid ? '' : 'row-invalid'}">
                <td>${statusIcon}</td>
                <td class="filename-cell" title="${f.filename}">${truncateFilename(f.filename, 25)}</td>
                <td>${f.valid ? formatName(f.patient_name) : '-'}</td>
                <td>${f.valid ? (f.patient_id || '-') : '-'}</td>
                <td>${f.valid ? (f.study_description || '-') : (f.error || 'Invalid')}</td>
                <td>${f.valid ? (f.modality || '-') : '-'}</td>
                <td>${f.valid ? formatDate(f.study_date) : '-'}</td>
                <td>${f.valid ? (f.accession_number || '-') : '-'}</td>
            </tr>
        `;
    }).join('');
}

// Summary
function updateSummary() {
    const validCount = validatedFiles.filter(f => f.valid).length;

    document.getElementById('summary-files').textContent = `${validCount} valid file${validCount !== 1 ? 's' : ''} (${selectedFiles.length} total)`;
    document.getElementById('summary-destination').textContent = selectedDestination?.name || '-';
    document.getElementById('summary-calling-ae').textContent = selectedDestination?.calling_ae_title || 'D2D_SCU';
    document.getElementById('summary-dest-ae').textContent = selectedDestination?.ae_title || '-';
    document.getElementById('summary-dest-details').textContent = selectedDestination
        ? `${selectedDestination.host}:${selectedDestination.port}`
        : '-';

    // Disable upload button if no valid files
    const uploadBtn = document.getElementById('upload-send-btn');
    uploadBtn.disabled = validCount === 0;
    if (validCount === 0) {
        uploadBtn.textContent = 'No Valid Files to Upload';
    } else {
        uploadBtn.innerHTML = `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="22" y1="2" x2="11" y2="13"/>
                <polygon points="22 2 15 22 11 13 2 9 22 2"/>
            </svg>
            Upload & Send ${validCount} File${validCount !== 1 ? 's' : ''} to PACS
        `;
    }
}

// Upload and Send
async function uploadAndSend() {
    const validFiles = validatedFiles.filter(f => f.valid);

    if (validFiles.length === 0 || !selectedDestination) {
        showError('No valid DICOM files to upload');
        return;
    }

    showProgress();
    updateProgress(0, validFiles.length, 'Preparing upload...');

    try {
        const formData = new FormData();

        // Add only valid files
        for (const vf of validFiles) {
            formData.append('files', vf.file);
        }

        // Add destination as JSON string
        formData.append('destination', JSON.stringify(selectedDestination));

        updateProgress(0, validFiles.length, 'Uploading files to server...');

        const response = await apiFetch('/api/dicom/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        hideProgress();

        if (!response.ok) {
            throw new Error(data.detail || 'Upload failed');
        }

        // Show results
        showResults(data);

    } catch (error) {
        hideProgress();
        showError('Upload failed: ' + error.message);
    }
}

function showResults(data) {
    // Hide other sections
    document.getElementById('files-section').style.display = 'none';
    document.getElementById('destination-section').style.display = 'none';
    document.getElementById('upload-section').style.display = 'none';
    document.getElementById('results-section').style.display = 'block';

    // Update step indicator
    updateStepIndicator(4);

    // Update stats
    document.getElementById('stat-successful').textContent = data.successful;
    document.getElementById('stat-failed').textContent = data.failed;
    document.getElementById('stat-total').textContent = data.total_files;

    // Update header based on success
    const headerEl = document.getElementById('results-header');
    const iconEl = document.getElementById('results-icon');
    const titleEl = document.getElementById('results-title');
    const messageEl = document.getElementById('results-message');

    if (data.failed === 0) {
        headerEl.classList.remove('error');
        headerEl.classList.add('success');
        iconEl.innerHTML = `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                <polyline points="22 4 12 14.01 9 11.01"/>
            </svg>
        `;
        titleEl.textContent = 'Upload Complete';
        messageEl.textContent = data.message;
    } else if (data.successful > 0) {
        headerEl.classList.remove('success', 'error');
        iconEl.innerHTML = `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/>
                <line x1="12" y1="8" x2="12" y2="12"/>
                <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
        `;
        titleEl.textContent = 'Partial Upload';
        messageEl.textContent = data.message;
    } else {
        headerEl.classList.remove('success');
        headerEl.classList.add('error');
        iconEl.innerHTML = `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/>
                <line x1="15" y1="9" x2="9" y2="15"/>
                <line x1="9" y1="9" x2="15" y2="15"/>
            </svg>
        `;
        titleEl.textContent = 'Upload Failed';
        messageEl.textContent = data.message;
    }

    // Render results list
    const resultsListEl = document.getElementById('results-list');
    resultsListEl.innerHTML = data.results.map(result => `
        <div class="result-item ${result.success ? 'result-success' : 'result-error'}">
            <div class="result-icon">
                ${result.success
                    ? `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                        <polyline points="22 4 12 14.01 9 11.01"/>
                       </svg>`
                    : `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"/>
                        <line x1="15" y1="9" x2="9" y2="15"/>
                        <line x1="9" y1="9" x2="15" y2="15"/>
                       </svg>`
                }
            </div>
            <div class="result-info">
                <div class="result-filename">${result.filename}</div>
                <div class="result-meta">
                    ${result.patient_name ? `<span>Patient: ${result.patient_name}</span>` : ''}
                    ${result.patient_id ? `<span>ID: ${result.patient_id}</span>` : ''}
                    ${result.modality ? `<span>Modality: ${result.modality}</span>` : ''}
                    ${result.accession_number ? `<span>Accession: ${result.accession_number}</span>` : ''}
                </div>
                <div class="result-message">${result.message}</div>
            </div>
        </div>
    `).join('');

    // Scroll to results
    document.getElementById('results-section').scrollIntoView({ behavior: 'smooth' });
}

function resetForm() {
    selectedFiles = [];
    validatedFiles = [];
    document.getElementById('file-input').value = '';

    // Reset UI
    document.getElementById('files-section').style.display = 'block';
    document.getElementById('destination-section').style.display = 'none';
    document.getElementById('upload-section').style.display = 'none';
    document.getElementById('results-section').style.display = 'none';

    document.getElementById('selected-files').style.display = 'none';
    document.getElementById('files-list').innerHTML = '';

    goToStep(1);
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Progress
function showProgress() {
    document.getElementById('progress-overlay').style.display = 'flex';
}

function hideProgress() {
    document.getElementById('progress-overlay').style.display = 'none';
}

function updateProgress(current, total, message) {
    const percent = total > 0 ? (current / total) * 100 : 0;
    document.getElementById('progress-fill').style.width = `${percent}%`;
    document.getElementById('progress-message').textContent = message;
    document.getElementById('progress-count').textContent = `${current} / ${total} files`;
}

// Error handling
function showError(message) {
    const alertEl = document.getElementById('error-alert');
    document.getElementById('error-message').textContent = message;
    alertEl.style.display = 'flex';
}

function dismissError() {
    document.getElementById('error-alert').style.display = 'none';
}

// Notifications
function showNotification(message) {
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: #10b981;
        color: white;
        padding: 15px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 2000;
        animation: slideIn 0.3s ease-out;
    `;
    notification.textContent = message;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Loading
function showLoading(message) {
    document.getElementById('loading-message').textContent = message;
    document.getElementById('loading-overlay').style.display = 'flex';
}

function hideLoading() {
    document.getElementById('loading-overlay').style.display = 'none';
}
