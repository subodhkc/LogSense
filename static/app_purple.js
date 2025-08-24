// Purple Design LogSense JavaScript
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    setupFileUpload();
    setupDragAndDrop();
    setupFormToggle();
    updateSessionMetrics();
    generateSessionId();
}

// Generate random session ID
function generateSessionId() {
    const sessionId = 'LS-' + Math.random().toString(36).substr(2, 8).toUpperCase();
    document.getElementById('session-id').textContent = sessionId;
}

// Form toggle functionality
function setupFormToggle() {
    const formHeader = document.querySelector('.form-header');
    if (formHeader) {
        formHeader.addEventListener('click', () => toggleSection('user-info'));
    }
}

function toggleSection(sectionId) {
    const section = document.getElementById(sectionId);
    const expandBtn = document.querySelector('.expand-btn');
    
    if (section.style.display === 'none') {
        section.style.display = 'block';
        expandBtn.textContent = '⌄';
    } else {
        section.style.display = 'none';
        expandBtn.textContent = '>';
    }
}

// File upload functionality
function setupFileUpload() {
    const fileInput = document.getElementById('file-input');
    const uploadArea = document.getElementById('upload-area');
    
    fileInput.addEventListener('change', handleFileSelect);
    uploadArea.addEventListener('click', () => fileInput.click());
}

// Drag and drop functionality
function setupDragAndDrop() {
    const uploadArea = document.getElementById('upload-area');
    
    uploadArea.addEventListener('dragover', handleDragOver);
    uploadArea.addEventListener('dragleave', handleDragLeave);
    uploadArea.addEventListener('drop', handleDrop);
}

function handleDragOver(e) {
    e.preventDefault();
    e.currentTarget.classList.add('dragover');
}

function handleDragLeave(e) {
    e.preventDefault();
    e.currentTarget.classList.remove('dragover');
}

function handleDrop(e) {
    e.preventDefault();
    e.currentTarget.classList.remove('dragover');
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        processFile(files[0]);
    }
}

function handleFileSelect(e) {
    const file = e.target.files[0];
    if (file) {
        processFile(file);
    }
}

// Process uploaded file
function processFile(file) {
    showProgress();
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('context', getContextData());
    
    fetch('/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        hideProgress();
        if (data.status === 'success') {
            displayAnalysisResults(data);
            showAnalysisSection();
            updateSessionMetrics(data);
        } else {
            showNotification(data.error || 'Upload failed', 'error');
        }
    })
    .catch(error => {
        hideProgress();
        showNotification('Network error: ' + error.message, 'error');
    });
}

// Get context data from form
function getContextData() {
    const userName = document.getElementById('user-name')?.value || '';
    const appTested = document.getElementById('application-tested')?.value || '';
    const appVersion = document.getElementById('app-version')?.value || '';
    const testEnv = document.getElementById('test-environment')?.value || '';
    
    return JSON.stringify({
        user_name: userName,
        application_tested: appTested,
        application_version: appVersion,
        test_environment: testEnv
    });
}

// Display analysis results
function displayAnalysisResults(data) {
    displayMetricCards(data);
    displayEvents(data.events || []);
}

// Display metric cards
function displayMetricCards(data) {
    const container = document.getElementById('metric-cards');
    container.innerHTML = `
        <div class="metric-card">
            <div class="metric-card-value">${data.events_count || 0}</div>
            <div class="metric-card-label">Total Events</div>
        </div>
        <div class="metric-card">
            <div class="metric-card-value">${data.critical_errors || 0}</div>
            <div class="metric-card-label">Critical Errors</div>
        </div>
        <div class="metric-card">
            <div class="metric-card-value">${data.warnings || 0}</div>
            <div class="metric-card-label">Warnings</div>
        </div>
        <div class="metric-card">
            <div class="metric-card-value">${data.issues_found || 0}</div>
            <div class="metric-card-label">Issues Found</div>
        </div>
    `;
}

// Display events
function displayEvents(events) {
    const container = document.getElementById('events-container');
    
    if (events.length === 0) {
        container.innerHTML = '<div style="text-align: center; color: #6b7280; padding: 2rem;">No events to display</div>';
        return;
    }
    
    container.innerHTML = events.map(event => `
        <div style="padding: 1rem; border-bottom: 1px solid #e5e7eb; background: white; margin-bottom: 1px; border-radius: 4px;">
            <div style="color: #6b7280; font-size: 0.75rem; margin-bottom: 0.5rem;">${event.timestamp || 'Unknown time'}</div>
            <div style="display: inline-block; padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.75rem; font-weight: 500; text-transform: uppercase; margin-right: 0.5rem; ${getLevelStyle(event.level)}">${event.level || 'INFO'}</div>
            <div style="color: #374151; margin-top: 0.5rem;">${event.message || 'No message'}</div>
        </div>
    `).join('');
}

function getLevelStyle(level) {
    const levelLower = (level || 'info').toLowerCase();
    switch (levelLower) {
        case 'error':
        case 'critical':
        case 'fatal':
            return 'background-color: #fee2e2; color: #dc2626;';
        case 'warning':
            return 'background-color: #fef3c7; color: #d97706;';
        default:
            return 'background-color: #dbeafe; color: #2563eb;';
    }
}

// Tab functionality
function showAnalysisTab(tabName) {
    // Hide all tab contents
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Remove active class from all tab buttons
    document.querySelectorAll('.tab-button').forEach(button => {
        button.classList.remove('active');
    });
    
    // Show selected tab content
    document.getElementById(tabName + '-tab').classList.add('active');
    
    // Add active class to clicked button
    event.target.classList.add('active');
}

// ML Analysis functions
function runMLAnalysis(analysisType) {
    const mlResults = document.getElementById('ml-results');
    
    // Check if ML is enabled
    const mlEnabled = document.getElementById('enable-ml').checked;
    if (!mlEnabled) {
        showNotification('ML Insights is disabled. Please enable it in Analysis Settings.', 'warning');
        return;
    }
    
    mlResults.innerHTML = `
        <div style="text-align: center; color: #6b7280; padding: 2rem;">
            <div style="margin-bottom: 1rem;">Running ${analysisType} analysis...</div>
            <div style="width: 100%; height: 4px; background-color: #e5e7eb; border-radius: 2px; overflow: hidden;">
                <div style="width: 0%; height: 100%; background: linear-gradient(90deg, #8b5cf6, #a855f7); animation: progress-animation 2s infinite;"></div>
            </div>
        </div>
    `;
    
    // Simulate ML analysis with GPU
    fetch('/ml_analysis', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            analysis_type: analysisType,
            use_gpu: true
        })
    })
    .then(response => response.json())
    .then(data => {
        displayMLResults(data, analysisType);
    })
    .catch(error => {
        mlResults.innerHTML = `
            <div style="color: #dc2626; padding: 1rem; background-color: #fee2e2; border-radius: 6px;">
                <strong>ML Analysis Failed:</strong> ${error.message}
                <br><small>Note: GPU acceleration may not be available on this server configuration.</small>
            </div>
        `;
    });
}

function displayMLResults(data, analysisType) {
    const container = document.getElementById('ml-results');
    
    if (data.error) {
        container.innerHTML = `
            <div style="color: #dc2626; padding: 1rem; background-color: #fee2e2; border-radius: 6px;">
                <strong>Error:</strong> ${data.error}
            </div>
        `;
        return;
    }
    
    container.innerHTML = `
        <div style="background: white; padding: 1.5rem; border-radius: 8px; border: 1px solid #e5e7eb;">
            <h4 style="color: #374151; margin-bottom: 1rem;">${analysisType.charAt(0).toUpperCase() + analysisType.slice(1)} Analysis Results</h4>
            <div style="color: #6b7280; margin-bottom: 1rem;">
                <strong>Analysis Type:</strong> ${data.analysis_type || analysisType}<br>
                <strong>GPU Acceleration:</strong> ${data.gpu_used ? 'Enabled' : 'CPU Only'}<br>
                <strong>Processing Time:</strong> ${data.processing_time || 'N/A'}
            </div>
            <div style="background: #f9fafb; padding: 1rem; border-radius: 6px;">
                ${data.results || `${analysisType} analysis completed successfully. Results would be displayed here in a production environment.`}
            </div>
        </div>
    `;
}

// Correlation Analysis
function runCorrelationAnalysis(analysisType) {
    const correlationResults = document.getElementById('correlation-results');
    
    // Check if correlations are enabled
    const correlationsEnabled = document.getElementById('enable-correlations').checked;
    if (!correlationsEnabled) {
        showNotification('Correlations is disabled. Please enable it in Analysis Settings.', 'warning');
        return;
    }
    
    correlationResults.innerHTML = `
        <div style="text-align: center; color: #6b7280; padding: 2rem;">
            <div style="margin-bottom: 1rem;">Running ${analysisType} analysis...</div>
            <div style="width: 100%; height: 4px; background-color: #e5e7eb; border-radius: 2px; overflow: hidden;">
                <div style="width: 0%; height: 100%; background: linear-gradient(90deg, #8b5cf6, #a855f7); animation: progress-animation 2s infinite;"></div>
            </div>
        </div>
    `;
    
    // Simulate correlation analysis
    setTimeout(() => {
        correlationResults.innerHTML = `
            <div style="background: white; padding: 1.5rem; border-radius: 8px; border: 1px solid #e5e7eb;">
                <h4 style="color: #374151; margin-bottom: 1rem;">${analysisType.charAt(0).toUpperCase() + analysisType.slice(1)} Analysis</h4>
                <div style="background: #f9fafb; padding: 1rem; border-radius: 6px;">
                    ${analysisType} correlation analysis completed. Event relationships and patterns would be displayed here.
                </div>
            </div>
        `;
    }, 2000);
}

// Generate report
function generateReport(reportType) {
    const engines = {
        use_local_llm: document.getElementById('use-local-llm').checked,
        use_cloud_ai: document.getElementById('use-cloud-ai').checked,
        use_python_engine: document.getElementById('use-python-engine').checked
    };
    
    const requestData = {
        report_type: reportType,
        ...engines
    };
    
    showReportProgress();
    
    fetch('/generate_report', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestData)
    })
    .then(response => response.json())
    .then(data => {
        displayReportResults(data);
    })
    .catch(error => {
        const container = document.getElementById('report-results');
        container.innerHTML = `
            <div style="color: #dc2626; padding: 1rem; background-color: #fee2e2; border-radius: 6px;">
                <strong>Report Generation Failed:</strong> ${error.message}
            </div>
        `;
    });
}

function showReportProgress() {
    const container = document.getElementById('report-results');
    container.innerHTML = `
        <div style="text-align: center; color: #6b7280; padding: 2rem;">
            <div style="margin-bottom: 1rem;">Generating report...</div>
            <div style="width: 100%; height: 4px; background-color: #e5e7eb; border-radius: 2px; overflow: hidden;">
                <div style="width: 0%; height: 100%; background: linear-gradient(90deg, #8b5cf6, #a855f7); animation: progress-animation 2s infinite;"></div>
            </div>
        </div>
    `;
}

function displayReportResults(data) {
    const container = document.getElementById('report-results');
    
    if (data.error) {
        container.innerHTML = `
            <div style="color: #dc2626; padding: 1rem; background-color: #fee2e2; border-radius: 6px;">
                <strong>Error:</strong> ${data.error}
            </div>
        `;
        return;
    }
    
    container.innerHTML = `
        <div style="background: white; padding: 1.5rem; border-radius: 8px; border: 1px solid #e5e7eb;">
            <h4 style="color: #374151; margin-bottom: 1rem;">${data.message || 'Report Generated'}</h4>
            <div style="color: #6b7280; margin-bottom: 1rem;">
                <strong>Report Type:</strong> ${data.report_type || 'Standard'}<br>
                <strong>Events Analyzed:</strong> ${data.events_analyzed || 0}<br>
                <strong>Generated:</strong> ${new Date(data.timestamp).toLocaleString()}
            </div>
            
            ${data.summary ? `
                <div style="margin-bottom: 1rem; padding: 1rem; background-color: #f9fafb; border-radius: 6px;">
                    <strong>Summary:</strong> ${data.summary}
                </div>
            ` : ''}
            
            ${data.ai_analysis ? `
                <div style="margin-bottom: 1rem; padding: 1rem; background-color: #eff6ff; border-radius: 6px;">
                    <strong>AI Analysis:</strong><br>
                    <pre style="white-space: pre-wrap; font-family: inherit; margin-top: 0.5rem;">${data.ai_analysis}</pre>
                </div>
            ` : ''}
            
            ${data.recommendations && data.recommendations.length > 0 ? `
                <div style="padding: 1rem; background-color: #f0fdf4; border-radius: 6px;">
                    <strong>Recommendations:</strong>
                    <ul style="margin-top: 0.5rem; padding-left: 1.5rem;">
                        ${data.recommendations.map(rec => `<li>${rec}</li>`).join('')}
                    </ul>
                </div>
            ` : ''}
        </div>
    `;
}

// Templates functionality
document.addEventListener('change', function(e) {
    if (e.target.id === 'show-templates') {
        const templatesContainer = document.getElementById('templates-container');
        const templatesEnabled = document.getElementById('enable-templates').checked;
        
        if (!templatesEnabled) {
            showNotification('Templates is disabled. Please enable it in Analysis Settings.', 'warning');
            e.target.checked = false;
            return;
        }
        
        if (e.target.checked) {
            templatesContainer.innerHTML = `
                <div style="background: white; padding: 1.5rem; border-radius: 8px; border: 1px solid #e5e7eb;">
                    <h4 style="color: #374151; margin-bottom: 1rem;">Template Patterns</h4>
                    <div style="background: #f9fafb; padding: 1rem; border-radius: 6px;">
                        Template pattern analysis would be displayed here. This includes structural patterns found in the log files.
                    </div>
                </div>
            `;
        } else {
            templatesContainer.innerHTML = '';
        }
    }
});

// Utility functions
function showAnalysisSection() {
    document.getElementById('analysis-section').style.display = 'block';
}

function showProgress() {
    document.getElementById('progress-container').style.display = 'block';
    animateProgress();
}

function hideProgress() {
    document.getElementById('progress-container').style.display = 'none';
}

function animateProgress() {
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    
    let progress = 0;
    const interval = setInterval(() => {
        progress += Math.random() * 10;
        if (progress > 90) progress = 90;
        
        progressFill.style.width = progress + '%';
        progressText.textContent = `Processing... ${Math.round(progress)}%`;
        
        if (progress >= 90) {
            clearInterval(interval);
        }
    }, 200);
}

function updateSessionMetrics(data = {}) {
    document.getElementById('files-processed').textContent = data.events_count ? '1' : '0';
    document.getElementById('events-analyzed').textContent = data.events_count || '0';
    document.getElementById('issues-found').textContent = data.issues_found || '0';
}

function showNotification(message, type = 'info') {
    const notificationId = type + '-notification';
    let notification = document.getElementById(notificationId);
    
    if (!notification) {
        notification = document.createElement('div');
        notification.id = notificationId;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 1rem 1.5rem;
            border-radius: 8px;
            max-width: 400px;
            z-index: 1000;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            font-weight: 500;
        `;
        
        if (type === 'error') {
            notification.style.backgroundColor = '#fee2e2';
            notification.style.color = '#dc2626';
            notification.style.border = '1px solid #fecaca';
        } else if (type === 'warning') {
            notification.style.backgroundColor = '#fef3c7';
            notification.style.color = '#d97706';
            notification.style.border = '1px solid #fed7aa';
        } else {
            notification.style.backgroundColor = '#dbeafe';
            notification.style.color = '#2563eb';
            notification.style.border = '1px solid #bfdbfe';
        }
        
        document.body.appendChild(notification);
    }
    
    notification.innerHTML = message;
    
    // Auto-hide
    setTimeout(() => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, type === 'error' ? 5000 : 3000);
}

// Add CSS animation for progress bars
const style = document.createElement('style');
style.textContent = `
    @keyframes progress-animation {
        0% { transform: translateX(-100%); }
        100% { transform: translateX(400%); }
    }
`;
document.head.appendChild(style);
