// D2D Application JavaScript - Redesigned Flow

let uploadedFileId = null;
let selectedDestination = null;
let selectedPatient = null;
let destinations = [];
let patients = [];
let filteredPatients = [];
let apiKeyRequired = false;
let currentStep = 1;

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

// Check API security settings on page load
async function checkApiSecurity() {
    try {
        const response = await fetch('/api/settings');
        const data = await response.json();
        apiKeyRequired = data.require_api_key;
    } catch (error) {
        console.error('Failed to check API security:', error);
    }
}

// Format date from YYYY-MM-DD to DD/MM/YYYY (Australian format)
function formatDateToAustralian(dateStr) {
    if (!dateStr) return '';
    const parts = dateStr.split('-');
    if (parts.length === 3) {
        return `${parts[2]}/${parts[1]}/${parts[0]}`;
    }
    return dateStr;
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    checkApiSecurity();
    setupUploadArea();
    setupPatientSearch();
    setupButtons();
    setupDestinations();
    loadDestinations();
    loadPatients(); // Auto-query all sites on page load
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

function goToStep(step) {
    updateStepIndicator(step);

    // Show/hide sections based on step
    document.getElementById('patient-section').style.display = step >= 1 ? 'block' : 'none';
    document.getElementById('upload-section').style.display = step >= 2 ? 'block' : 'none';
    document.getElementById('review-section').style.display = step >= 3 ? 'block' : 'none';
    document.getElementById('results-section').style.display = 'none';

    if (step === 3) {
        updateSummary();
    }
}

// Patient Loading
async function loadPatients() {
    const loadingEl = document.getElementById('patient-loading');
    const listEl = document.getElementById('patient-list');
    const noPatients = document.getElementById('no-patients');

    loadingEl.style.display = 'flex';
    listEl.style.display = 'none';
    noPatients.style.display = 'none';

    try {
        const response = await apiFetch('/api/worklist/query-all', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                host: '10.17.1.21',
                port: 5010,
                calling_ae: 'D2DSERVER'
            })
        });

        if (!response.ok) {
            throw new Error('Failed to query worklist');
        }

        const data = await response.json();
        patients = data.items || [];
        filteredPatients = [...patients];

        loadingEl.style.display = 'none';

        if (patients.length === 0) {
            noPatients.style.display = 'flex';
        } else {
            renderPatientList();
            listEl.style.display = 'flex';
        }
    } catch (error) {
        console.error('Failed to load patients:', error);
        loadingEl.style.display = 'none';
        showError('Failed to load patients: ' + error.message);
        noPatients.style.display = 'flex';
    }
}

function renderPatientList() {
    const listEl = document.getElementById('patient-list');

    if (filteredPatients.length === 0) {
        listEl.innerHTML = `
            <div class="empty-state">
                <p>No patients match your search</p>
            </div>
        `;
        return;
    }

    listEl.innerHTML = filteredPatients.map((patient, index) => `
        <div class="patient-item" onclick="selectPatient(${index})">
            <div class="patient-item-avatar">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                    <circle cx="12" cy="7" r="4"/>
                </svg>
            </div>
            <div class="patient-item-info">
                <div class="patient-item-name">${patient.patient_name || 'Unknown'}</div>
                <div class="patient-item-meta">
                    <span>ID: ${patient.patient_id || 'N/A'}</span>
                    <span>DOB: ${formatDateToAustralian(patient.patient_birth_date) || 'N/A'}</span>
                    <span>Acc: ${patient.accession_number || 'N/A'}</span>
                </div>
                ${patient.procedure_description || patient.requested_procedure_description ?
                    `<div class="patient-item-study">${patient.procedure_description || patient.requested_procedure_description}</div>` : ''}
            </div>
            ${patient.worklist_ae_title || patient.server_ae_title ? `<span class="patient-item-worklist">${patient.worklist_ae_title || patient.server_ae_title}</span>` : ''}
        </div>
    `).join('');
}

function selectPatient(index) {
    selectedPatient = filteredPatients[index];

    // Update selected patient display
    const selectedEl = document.getElementById('selected-patient');
    const listEl = document.getElementById('patient-list');
    const loadingEl = document.getElementById('patient-loading');
    const noPatients = document.getElementById('no-patients');
    const toolbarEl = document.querySelector('.patient-toolbar');

    document.getElementById('selected-patient-name').textContent = selectedPatient.patient_name || 'Unknown';
    document.getElementById('selected-patient-id').textContent = `ID: ${selectedPatient.patient_id || 'N/A'}`;
    document.getElementById('selected-patient-dob').textContent = `DOB: ${formatDateToAustralian(selectedPatient.patient_birth_date) || 'N/A'}`;
    document.getElementById('selected-patient-sex').textContent = selectedPatient.patient_sex || '';
    document.getElementById('selected-patient-study').textContent =
        selectedPatient.procedure_description || selectedPatient.requested_procedure_description || 'Document Conversion';

    // Show worklist AE title if available
    const worklistEl = document.getElementById('selected-patient-worklist');
    const worklistAeTitle = selectedPatient.worklist_ae_title || selectedPatient.server_ae_title;
    if (worklistEl) {
        worklistEl.textContent = worklistAeTitle ? `Worklist: ${worklistAeTitle}` : '';
        worklistEl.style.display = worklistAeTitle ? 'inline-block' : 'none';
    }

    // Hide list, show selected
    listEl.style.display = 'none';
    loadingEl.style.display = 'none';
    noPatients.style.display = 'none';
    toolbarEl.style.display = 'none';
    selectedEl.style.display = 'block';

    // Move to step 2
    goToStep(2);
    document.getElementById('upload-section').scrollIntoView({ behavior: 'smooth' });
}

function clearSelectedPatient() {
    selectedPatient = null;
    uploadedFileId = null;

    const selectedEl = document.getElementById('selected-patient');
    const listEl = document.getElementById('patient-list');
    const toolbarEl = document.querySelector('.patient-toolbar');
    const uploadedFilesEl = document.getElementById('uploaded-files');

    selectedEl.style.display = 'none';
    toolbarEl.style.display = 'flex';
    uploadedFilesEl.style.display = 'none';
    document.getElementById('files-list').innerHTML = '';

    if (patients.length > 0) {
        listEl.style.display = 'flex';
    } else {
        document.getElementById('no-patients').style.display = 'flex';
    }

    goToStep(1);
    updateConvertButton();
}

function setupPatientSearch() {
    const searchInput = document.getElementById('patient-search');

    searchInput.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase().trim();

        if (!query) {
            filteredPatients = [...patients];
        } else {
            filteredPatients = patients.filter(p =>
                (p.patient_name && p.patient_name.toLowerCase().includes(query)) ||
                (p.patient_id && p.patient_id.toLowerCase().includes(query)) ||
                (p.accession_number && p.accession_number.toLowerCase().includes(query))
            );
        }

        renderPatientList();
    });

    // Refresh button
    document.getElementById('refresh-patients-btn').addEventListener('click', () => {
        document.getElementById('patient-search').value = '';
        loadPatients();
    });

    // Create patient button
    document.getElementById('create-patient-btn').addEventListener('click', createPatient);
}

// Create Patient Modal
function createPatient() {
    document.getElementById('create-patient-modal').classList.add('active');
}

function closeCreatePatientModal() {
    document.getElementById('create-patient-modal').classList.remove('active');
    document.getElementById('create-patient-form').reset();
}

// Setup buttons
function setupButtons() {
    // Close create modal
    document.getElementById('close-create-modal').addEventListener('click', closeCreatePatientModal);

    // Create patient form submit
    document.getElementById('create-patient-form').addEventListener('submit', (e) => {
        e.preventDefault();

        selectedPatient = {
            patient_name: document.getElementById('new-patient-name').value,
            patient_id: document.getElementById('new-patient-id').value,
            patient_birth_date: document.getElementById('new-patient-dob').value || null,
            patient_sex: document.getElementById('new-patient-sex').value || null,
            accession_number: document.getElementById('new-accession').value || null,
            procedure_description: document.getElementById('new-study-description').value || 'Document Conversion',
            modality: document.getElementById('new-modality').value || 'OT',
            referring_physician: document.getElementById('new-referring-physician').value || null
        };

        // Update selected patient display
        document.getElementById('selected-patient-name').textContent = selectedPatient.patient_name;
        document.getElementById('selected-patient-id').textContent = `ID: ${selectedPatient.patient_id}`;
        document.getElementById('selected-patient-dob').textContent = `DOB: ${formatDateToAustralian(selectedPatient.patient_birth_date) || 'N/A'}`;
        document.getElementById('selected-patient-sex').textContent = selectedPatient.patient_sex || '';
        document.getElementById('selected-patient-study').textContent = selectedPatient.procedure_description;

        // Hide list, show selected
        document.getElementById('patient-list').style.display = 'none';
        document.getElementById('patient-loading').style.display = 'none';
        document.getElementById('no-patients').style.display = 'none';
        document.querySelector('.patient-toolbar').style.display = 'none';
        document.getElementById('selected-patient').style.display = 'block';

        closeCreatePatientModal();
        goToStep(2);
        document.getElementById('upload-section').scrollIntoView({ behavior: 'smooth' });
    });

    // Back button
    document.getElementById('back-btn').addEventListener('click', () => {
        goToStep(2);
    });

    // Convert & Send button
    document.getElementById('convert-send-btn').addEventListener('click', convertAndSend);

    // New conversion button
    document.getElementById('new-conversion-btn').addEventListener('click', resetForm);

    // View archives button
    document.getElementById('view-archives-btn').addEventListener('click', viewArchives);
    document.getElementById('close-archives-modal').addEventListener('click', () => {
        document.getElementById('archives-modal').classList.remove('active');
    });

    // Destination select change
    document.getElementById('destination-select').addEventListener('change', (e) => {
        const destName = e.target.value;
        selectedDestination = destinations.find(d => d.name === destName) || null;
        updateConvertButton();
        updateSummary();
    });
}

// File Upload
function setupUploadArea() {
    const uploadArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('file-input');

    uploadArea.addEventListener('click', (e) => {
        // The label handles clicks on the content area natively
        // Only trigger for clicks on the upload-area padding (outside the label)
        const label = uploadArea.querySelector('label');
        if (!label.contains(e.target) && e.target !== fileInput) {
            fileInput.click();
        }
    });

    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        const file = e.dataTransfer.files[0];
        if (file) handleFileUpload(file);
    });

    fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) handleFileUpload(file);
    });
}

async function handleFileUpload(file) {
    showLoading('Uploading file...');

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await apiFetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Upload failed');
        }

        const data = await response.json();
        uploadedFileId = data.file_id;

        // Show uploaded file
        const uploadedFilesEl = document.getElementById('uploaded-files');
        const filesListEl = document.getElementById('files-list');

        filesListEl.innerHTML = `
            <div class="file-item">
                <div class="file-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                        <polyline points="14 2 14 8 20 8"/>
                    </svg>
                </div>
                <div class="file-info">
                    <div class="file-name">${data.filename}</div>
                    <div class="file-size">${(data.size / 1024).toFixed(2)} KB</div>
                </div>
                <button class="file-remove" onclick="removeFile()">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18"/>
                        <line x1="6" y1="6" x2="18" y2="18"/>
                    </svg>
                </button>
            </div>
        `;

        uploadedFilesEl.style.display = 'block';

        // Move to step 3
        goToStep(3);
        updateConvertButton();
        document.getElementById('review-section').scrollIntoView({ behavior: 'smooth' });

    } catch (error) {
        showError('Upload failed: ' + error.message);
    } finally {
        hideLoading();
    }
}

function removeFile() {
    uploadedFileId = null;
    document.getElementById('uploaded-files').style.display = 'none';
    document.getElementById('files-list').innerHTML = '';
    document.getElementById('file-input').value = '';
    goToStep(2);
    updateConvertButton();
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
            // Save it to the backend
            await apiFetch('/api/destinations', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(defaultDest)
            });
            destinations = [defaultDest];
        }

        renderDestinationSelect();
        renderSavedDestinations();

        // Auto-select the first destination (VRG PACS)
        if (destinations.length > 0) {
            const select = document.getElementById('destination-select');
            select.value = destinations[0].name;
            selectedDestination = destinations[0];
            updateConvertButton();
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
                <p><strong>AE Title:</strong> ${dest.ae_title}</p>
                <p><strong>Host:</strong> ${dest.host}:${dest.port}</p>
            </div>
            <button onclick="deleteDestination('${dest.name}')">Delete</button>
        </div>
    `).join('');
}

async function saveDestination() {
    const destination = {
        name: document.getElementById('dest-name').value,
        ae_title: document.getElementById('dest-ae-title').value,
        host: document.getElementById('dest-host').value,
        port: parseInt(document.getElementById('dest-port').value),
        calling_ae_title: document.getElementById('dest-calling-ae').value
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
        calling_ae_title: document.getElementById('dest-calling-ae').value
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

// Summary & Convert
function updateSummary() {
    document.getElementById('summary-patient').textContent = selectedPatient?.patient_name || '-';
    document.getElementById('summary-patient-id').textContent = selectedPatient?.patient_id || '-';
    document.getElementById('summary-accession').textContent = selectedPatient?.accession_number || '-';
    document.getElementById('summary-study').textContent =
        selectedPatient?.procedure_description || selectedPatient?.requested_procedure_description || 'Document Conversion';
    document.getElementById('summary-worklist').textContent =
        selectedPatient?.worklist_ae_title || selectedPatient?.server_ae_title || '-';
    document.getElementById('summary-files').textContent = uploadedFileId ? '1 file' : '0 files';
    document.getElementById('summary-destination').textContent = selectedDestination?.name || 'Not selected';
}

function updateConvertButton() {
    const btn = document.getElementById('convert-send-btn');
    btn.disabled = !selectedPatient || !uploadedFileId || !selectedDestination;
}

async function convertAndSend() {
    if (!selectedPatient || !uploadedFileId || !selectedDestination) {
        showError('Please complete all steps before converting');
        return;
    }

    const metadata = {
        patient_name: selectedPatient.patient_name,
        patient_id: selectedPatient.patient_id,
        patient_birth_date: selectedPatient.patient_birth_date || null,
        patient_sex: selectedPatient.patient_sex || null,
        study_description: selectedPatient.procedure_description || selectedPatient.requested_procedure_description || 'Document Conversion',
        series_description: 'Imported Document',
        accession_number: selectedPatient.accession_number || null,
        referring_physician: selectedPatient.referring_physician || selectedPatient.scheduled_physician || null,
        modality: selectedPatient.modality || 'OT'
    };

    const request = {
        file_id: uploadedFileId,
        metadata: metadata,
        destination: selectedDestination,
        send_immediately: true
    };

    showLoading('Converting and sending to PACS...');

    try {
        const response = await apiFetch('/api/convert', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(request)
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Conversion failed');
        }

        // Show results
        document.getElementById('results-message').textContent = data.message;
        document.getElementById('result-sop-uid').textContent = data.sop_instance_uid;
        document.getElementById('result-study-uid').textContent = data.study_instance_uid;
        document.getElementById('result-series-uid').textContent = data.series_instance_uid;

        // Hide other sections, show results
        document.getElementById('patient-section').style.display = 'none';
        document.getElementById('upload-section').style.display = 'none';
        document.getElementById('review-section').style.display = 'none';
        document.getElementById('results-section').style.display = 'block';
        document.getElementById('results-section').scrollIntoView({ behavior: 'smooth' });

        // Update step indicator to show all complete
        updateStepIndicator(4);

    } catch (error) {
        showError('Conversion failed: ' + error.message);
    } finally {
        hideLoading();
    }
}

function resetForm() {
    uploadedFileId = null;
    selectedDestination = null;
    selectedPatient = null;

    // Reset UI
    document.getElementById('patient-section').style.display = 'block';
    document.getElementById('upload-section').style.display = 'none';
    document.getElementById('review-section').style.display = 'none';
    document.getElementById('results-section').style.display = 'none';

    document.getElementById('selected-patient').style.display = 'none';
    document.querySelector('.patient-toolbar').style.display = 'flex';
    document.getElementById('uploaded-files').style.display = 'none';
    document.getElementById('files-list').innerHTML = '';
    document.getElementById('file-input').value = '';
    document.getElementById('destination-select').value = '';
    document.getElementById('patient-search').value = '';

    if (patients.length > 0) {
        document.getElementById('patient-list').style.display = 'flex';
        filteredPatients = [...patients];
        renderPatientList();
    } else {
        document.getElementById('no-patients').style.display = 'flex';
    }

    goToStep(1);
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Archives
async function viewArchives() {
    showLoading('Loading archives...');

    try {
        const response = await apiFetch('/api/archives');
        if (!response.ok) {
            throw new Error('Failed to load archives');
        }
        const data = await response.json();

        const archivesList = document.getElementById('archives-list');

        if (data.archives.length === 0) {
            archivesList.innerHTML = '<p style="color: var(--text-muted);">No archived files</p>';
        } else {
            archivesList.innerHTML = data.archives.map(archive => {
                const date = new Date(archive.created * 1000).toLocaleString('en-AU', {
                    day: '2-digit',
                    month: '2-digit',
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                    hour12: true
                });
                return `
                    <div class="archive-item">
                        <div class="archive-info">
                            <h4>${archive.filename}</h4>
                            <p>Size: ${(archive.size / 1024).toFixed(2)} KB | Created: ${date}</p>
                        </div>
                        <a href="/api/archives/${archive.filename}" class="btn btn-outline" download>Download</a>
                    </div>
                `;
            }).join('');
        }

        document.getElementById('archives-modal').classList.add('active');

    } catch (error) {
        showError('Failed to load archives: ' + error.message);
    } finally {
        hideLoading();
    }
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
