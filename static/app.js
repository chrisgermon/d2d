// D2D Application JavaScript

let uploadedFileId = null;
let selectedDestination = null;
let destinations = [];

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
    setupUploadArea();
    setupMetadataForm();
    setupDestinations();
    setupButtons();
    loadDestinations();
    checkWorklistData();
});

// Check for worklist data from sessionStorage
function checkWorklistData() {
    const worklistItem = sessionStorage.getItem('worklistItem');
    if (worklistItem) {
        try {
            const item = JSON.parse(worklistItem);
            populateFromWorklist(item);
            sessionStorage.removeItem('worklistItem'); // Clear after use

            // Show notification
            showNotification('Patient data loaded from worklist: ' + item.patient_name);
        } catch (e) {
            console.error('Error loading worklist data:', e);
        }
    }
}

function populateFromWorklist(item) {
    // Show metadata section
    document.getElementById('metadata-section').style.display = 'block';

    // Populate patient information
    if (item.patient_name) {
        document.getElementById('patient-name').value = item.patient_name;
    }
    if (item.patient_id) {
        document.getElementById('patient-id').value = item.patient_id;
    }
    if (item.patient_birth_date) {
        document.getElementById('patient-dob').value = item.patient_birth_date;
    }
    if (item.patient_sex) {
        document.getElementById('patient-sex').value = item.patient_sex;
    }

    // Populate study information
    if (item.accession_number) {
        document.getElementById('accession-number').value = item.accession_number;
    }
    if (item.procedure_description || item.requested_procedure_description) {
        document.getElementById('study-description').value =
            item.procedure_description || item.requested_procedure_description;
    }
    if (item.modality) {
        document.getElementById('modality').value = item.modality;
    }
    if (item.scheduled_physician) {
        document.getElementById('referring-physician').value = item.scheduled_physician;
    }

    // Set study date/time if scheduled
    if (item.scheduled_date) {
        document.getElementById('study-date').value = item.scheduled_date;
    }
    if (item.scheduled_time) {
        document.getElementById('study-time').value = item.scheduled_time;
    }
}

function showNotification(message) {
    // Create notification element
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: #4CAF50;
        color: white;
        padding: 15px 20px;
        border-radius: 5px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        z-index: 1000;
        animation: slideIn 0.3s ease-out;
    `;
    notification.textContent = message;

    document.body.appendChild(notification);

    // Remove after 5 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, 5000);
}

// File Upload
function setupUploadArea() {
    const uploadArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('file-input');

    uploadArea.addEventListener('click', () => fileInput.click());

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
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Upload failed');
        }

        const data = await response.json();
        uploadedFileId = data.file_id;

        // Show file info
        const fileInfo = document.getElementById('file-info');
        fileInfo.style.display = 'block';
        fileInfo.innerHTML = `
            <strong>✓ File uploaded:</strong> ${data.filename}
            (${(data.size / 1024).toFixed(2)} KB)
        `;

        // Show metadata section
        document.getElementById('metadata-section').style.display = 'block';
        document.getElementById('metadata-section').scrollIntoView({ behavior: 'smooth' });

    } catch (error) {
        alert('Upload failed: ' + error.message);
    } finally {
        hideLoading();
    }
}

// Metadata Form
function setupMetadataForm() {
    const form = document.getElementById('metadata-form');
    const inputs = form.querySelectorAll('input, select');

    inputs.forEach(input => {
        input.addEventListener('input', checkMetadataComplete);
    });
}

function checkMetadataComplete() {
    const patientName = document.getElementById('patient-name').value;
    const patientId = document.getElementById('patient-id').value;

    if (patientName && patientId) {
        document.getElementById('destination-section').style.display = 'block';
        document.getElementById('preview-section').style.display = 'block';
        updatePreview();
    }
}

function updatePreview() {
    const metadata = getMetadata();
    const previewContent = document.getElementById('preview-content');

    const displayDob = metadata.patient_birth_date
        ? formatDateToAustralian(metadata.patient_birth_date)
        : 'Not set';

    previewContent.innerHTML = `
        <h3>DICOM Metadata Preview</h3>
        <dl>
            <dt>Patient Name:</dt><dd>${metadata.patient_name}</dd>
            <dt>Patient ID:</dt><dd>${metadata.patient_id}</dd>
            <dt>Date of Birth:</dt><dd>${displayDob}</dd>
            <dt>Sex:</dt><dd>${metadata.patient_sex || 'Not set'}</dd>
            <dt>Study Description:</dt><dd>${metadata.study_description}</dd>
            <dt>Series Description:</dt><dd>${metadata.series_description}</dd>
            <dt>Accession Number:</dt><dd>${metadata.accession_number || 'Not set'}</dd>
            <dt>Referring Physician:</dt><dd>${metadata.referring_physician || 'Not set'}</dd>
        </dl>
        ${selectedDestination ? `
            <h3 style="margin-top: 1.5rem;">Selected Destination</h3>
            <dl>
                <dt>Name:</dt><dd>${selectedDestination.name}</dd>
                <dt>AE Title:</dt><dd>${selectedDestination.ae_title}</dd>
                <dt>Host:</dt><dd>${selectedDestination.host}:${selectedDestination.port}</dd>
            </dl>
        ` : ''}
    `;
}

function getMetadata() {
    return {
        patient_name: document.getElementById('patient-name').value,
        patient_id: document.getElementById('patient-id').value,
        patient_birth_date: document.getElementById('patient-dob').value || null,
        patient_sex: document.getElementById('patient-sex').value || null,
        study_description: document.getElementById('study-description').value,
        series_description: document.getElementById('series-description').value,
        accession_number: document.getElementById('accession-number').value || null,
        referring_physician: document.getElementById('referring-physician').value || null
    };
}

// Destinations
async function loadDestinations() {
    try {
        const response = await fetch('/api/destinations');
        const data = await response.json();
        destinations = data.destinations;
        renderDestinations();
        renderSavedDestinations();
    } catch (error) {
        console.error('Failed to load destinations:', error);
    }
}

function renderDestinations() {
    const list = document.getElementById('destinations-list');

    if (destinations.length === 0) {
        list.innerHTML = '<p style="color: #666;">No destinations configured. Click "Manage Destinations" to add one.</p>';
        return;
    }

    list.innerHTML = destinations.map(dest => `
        <div class="destination-card" onclick="selectDestination('${dest.name}')">
            <h3>${dest.name}</h3>
            <p><strong>AE Title:</strong> ${dest.ae_title}</p>
            <p><strong>Host:</strong> ${dest.host}:${dest.port}</p>
        </div>
    `).join('');
}

function selectDestination(name) {
    selectedDestination = destinations.find(d => d.name === name);

    // Update UI
    document.querySelectorAll('.destination-card').forEach(card => {
        card.classList.remove('selected');
    });
    event.currentTarget.classList.add('selected');

    updatePreview();
}

function setupDestinations() {
    // Manage Destinations button
    document.getElementById('manage-destinations-btn').addEventListener('click', () => {
        document.getElementById('destinations-modal').classList.add('active');
    });

    // Close modal
    document.getElementById('close-modal').addEventListener('click', () => {
        document.getElementById('destinations-modal').classList.remove('active');
    });

    // Destination form
    document.getElementById('destination-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        await saveDestination();
    });

    // Test connection
    document.getElementById('test-connection-btn').addEventListener('click', async () => {
        await testConnection();
    });
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
        const response = await fetch('/api/destinations', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(destination)
        });

        if (!response.ok) throw new Error('Failed to save destination');

        await loadDestinations();
        document.getElementById('destination-form').reset();
        alert('Destination saved successfully!');

    } catch (error) {
        alert('Failed to save destination: ' + error.message);
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
        const response = await fetch('/api/destinations/verify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(destination)
        });

        const data = await response.json();

        if (response.ok) {
            alert('✓ ' + data.message);
        } else {
            alert('✗ Connection failed: ' + data.detail);
        }

    } catch (error) {
        alert('✗ Connection failed: ' + error.message);
    } finally {
        hideLoading();
    }
}

function renderSavedDestinations() {
    const container = document.getElementById('saved-destinations');

    if (destinations.length === 0) {
        container.innerHTML = '<p style="color: #666;">No saved destinations</p>';
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

async function deleteDestination(name) {
    if (!confirm(`Delete destination "${name}"?`)) return;

    showLoading('Deleting destination...');

    try {
        const response = await fetch(`/api/destinations/${encodeURIComponent(name)}`, {
            method: 'DELETE'
        });

        if (!response.ok) throw new Error('Failed to delete destination');

        await loadDestinations();

    } catch (error) {
        alert('Failed to delete destination: ' + error.message);
    } finally {
        hideLoading();
    }
}

// Convert
function setupButtons() {
    document.getElementById('convert-btn').addEventListener('click', convertToDicom);
    document.getElementById('reset-btn').addEventListener('click', resetForm);
    document.getElementById('new-conversion-btn').addEventListener('click', resetForm);
    document.getElementById('view-archives-btn').addEventListener('click', viewArchives);
    document.getElementById('close-archives-modal').addEventListener('click', () => {
        document.getElementById('archives-modal').classList.remove('active');
    });
}

async function convertToDicom() {
    if (!uploadedFileId) {
        alert('Please upload a file first');
        return;
    }

    const sendImmediately = document.getElementById('send-immediately').checked;

    if (sendImmediately && !selectedDestination) {
        alert('Please select a destination or uncheck "Send immediately"');
        return;
    }

    const request = {
        file_id: uploadedFileId,
        metadata: getMetadata(),
        destination: selectedDestination,
        send_immediately: sendImmediately
    };

    showLoading(sendImmediately ? 'Converting and sending...' : 'Converting to DICOM...');

    try {
        const response = await fetch('/api/convert', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(request)
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Conversion failed');
        }

        // Show results
        const resultsContent = document.getElementById('results-content');
        resultsContent.innerHTML = `
            <h3>✓ ${data.message}</h3>
            <dl>
                <dt>SOP Instance UID:</dt><dd>${data.sop_instance_uid}</dd>
                <dt>Study Instance UID:</dt><dd>${data.study_instance_uid}</dd>
                <dt>Series Instance UID:</dt><dd>${data.series_instance_uid}</dd>
                <dt>Archive Path:</dt><dd>${data.dicom_file_path}</dd>
            </dl>
        `;

        // Hide previous sections and show results
        document.getElementById('upload-section').style.display = 'none';
        document.getElementById('metadata-section').style.display = 'none';
        document.getElementById('destination-section').style.display = 'none';
        document.getElementById('preview-section').style.display = 'none';
        document.getElementById('results-section').style.display = 'block';
        document.getElementById('results-section').scrollIntoView({ behavior: 'smooth' });

    } catch (error) {
        alert('Conversion failed: ' + error.message);
    } finally {
        hideLoading();
    }
}

function resetForm() {
    uploadedFileId = null;
    selectedDestination = null;

    document.getElementById('upload-section').style.display = 'block';
    document.getElementById('metadata-section').style.display = 'none';
    document.getElementById('destination-section').style.display = 'none';
    document.getElementById('preview-section').style.display = 'none';
    document.getElementById('results-section').style.display = 'none';

    document.getElementById('file-info').style.display = 'none';
    document.getElementById('metadata-form').reset();
    document.getElementById('file-input').value = '';

    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Archives
async function viewArchives() {
    showLoading('Loading archives...');

    try {
        const response = await fetch('/api/archives');
        const data = await response.json();

        const archivesList = document.getElementById('archives-list');

        if (data.archives.length === 0) {
            archivesList.innerHTML = '<p style="color: #666;">No archived files</p>';
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
                        <a href="/api/archives/${archive.filename}" class="btn btn-secondary" download>Download</a>
                    </div>
                `;
            }).join('');
        }

        document.getElementById('archives-modal').classList.add('active');

    } catch (error) {
        alert('Failed to load archives: ' + error.message);
    } finally {
        hideLoading();
    }
}

// Loading
function showLoading(message) {
    document.getElementById('loading-message').textContent = message;
    document.getElementById('loading-overlay').style.display = 'flex';
}

function hideLoading() {
    document.getElementById('loading-overlay').style.display = 'none';
}
