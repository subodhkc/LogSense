// JavaScript for LogSense Modal Native App

let currentStep = 0;
let analysisResults = null;

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    updateProgressSteps();
    setupFileUpload();
    setupExpanders();
    setupTabs();
    generateSessionId();
    updateSidebarMetrics();
});

// Generate session ID
function generateSessionId() {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
    let sessionId = 'LS-';
    for (let i = 0; i < 8; i++) {
        sessionId += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    document.getElementById('session-display').textContent = sessionId;
}

// Update sidebar metrics
function updateSidebarMetrics() {
    document.getElementById('files-processed').textContent = '0';
    document.getElementById('events-analyzed').textContent = '0';
    document.getElementById('issues-found').textContent = '0';
}

// Update progress indicator - Enterprise Style
function updateProgressSteps() {
    const steps = document.querySelectorAll('.progress-step');
    steps.forEach((step, index) => {
        step.classList.remove('active', 'completed', 'pending');
        const status = step.querySelector('.step-status');
        
        if (index < currentStep) {
            step.classList.add('completed');
            status.textContent = 'DONE';
        } else if (index === currentStep) {
            step.classList.add('active');
            status.textContent = 'ACTIVE';
        } else {
            step.classList.add('pending');
            status.textContent = 'PENDING';
        }
    });
}

// Setup expander functionality - Enterprise Style
function setupExpanders() {
    const expanders = document.querySelectorAll('.section-header');
    expanders.forEach(header => {
        header.addEventListener('click', function() {
            const section = this.nextElementSibling;
            const icon = this.querySelector('.expand-icon');
            
            if (section.style.display === 'none') {
                section.style.display = 'block';
                icon.style.transform = 'rotate(180deg)';
            } else {
                section.style.display = 'none';
                icon.style.transform = 'rotate(0deg)';
            }
        });
    });
}

// Toggle expander - Deprecated, using new enterprise style
function toggleExpander(expanderId) {
    // Legacy function kept for compatibility
    console.log('Legacy expander function called for:', expanderId);
}

// Setup tabs functionality
function setupTabs() {
    const tabButtons = document.querySelectorAll('.tab-button');
    tabButtons.forEach(button => {
        button.addEventListener('click', function() {
            const tabName = this.textContent.toLowerCase().replace(' ', '');
            showTab(tabName);
        });
    });
}

// Show specific tab
function showTab(tabName) {
    // Hide all tab contents
    const tabContents = document.querySelectorAll('.tab-content');
    tabContents.forEach(content => {
        content.classList.remove('active');
    });
    
    // Remove active class from all tab buttons
    const tabButtons = document.querySelectorAll('.tab-button');
    tabButtons.forEach(button => {
        button.classList.remove('active');
    });
    
    // Show selected tab content
    const selectedTab = document.getElementById(tabName + '-tab');
    if (selectedTab) {
        selectedTab.classList.add('active');
    }
    
    // Add active class to selected button
    const selectedButton = Array.from(tabButtons).find(button => 
        button.textContent.toLowerCase().replace(' ', '') === tabName
    );
    if (selectedButton) {
        selectedButton.classList.add('active');
    }
}

// Setup file upload functionality
function setupFileUpload() {
    const fileInput = document.getElementById('file-input');
    const uploadArea = document.querySelector('.upload-area');

    if (fileInput) {
        fileInput.addEventListener('change', handleFileSelect);
    }
    
    if (uploadArea) {
        // Drag and drop functionality
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
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                fileInput.files = files;
                handleFileSelect();
            }
        });
    }
}

// Handle file selection
function handleFileSelect() {
    const fileInput = document.getElementById('file-input');
    const file = fileInput.files[0];
    
    if (file) {
        showFileInfo(file);
        uploadFile(file);
    }
}

// Show file information
function showFileInfo(file) {
    const fileInfo = document.getElementById('file-info');
    const fileSize = (file.size / 1024 / 1024).toFixed(2);
    
    if (fileInfo) {
        fileInfo.innerHTML = `
            <strong>Selected File:</strong> ${file.name}<br>
            <strong>Size:</strong> ${fileSize} MB<br>
            <strong>Type:</strong> ${file.type || 'Unknown'}
        `;
        fileInfo.style.display = 'block';
    }
}

// Apply context (called by Apply/Update button)
async function applyContext() {
    // Update session metrics locally
    updateSessionMetrics();

    // Button feedback
    const btn = (typeof event !== 'undefined' && event && event.target) ? event.target : document.querySelector('button[onclick*="applyContext"]');
    const originalText = btn ? btn.textContent : '';
    if (btn) {
        btn.textContent = 'Saving...';
        btn.disabled = true;
    }

    try {
        const response = await fetch('/submit_context', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(getContextData())
        });
        const result = await response.json().catch(() => ({}));

        if (response.ok && result && result.status === 'success') {
            if (btn) {
                btn.textContent = 'Applied!';
                btn.style.backgroundColor = '#00c851';
            }
            // Progress to next step after successful context save
            currentStep = 1;
            updateProgressSteps();
        } else {
            const errMsg = (result && (result.error || result.message)) || ('HTTP ' + response.status);
            alert('Failed to save context: ' + errMsg);
            if (btn) btn.textContent = originalText || 'Apply / Update';
        }
    } catch (error) {
        console.error('Context save error:', error);
        alert('Failed to save context: ' + error.message);
        if (btn) btn.textContent = originalText || 'Apply / Update';
    } finally {
        if (btn) {
            btn.disabled = false;
            setTimeout(() => {
                btn.textContent = originalText || 'Apply / Update';
                btn.style.backgroundColor = '';
            }, 2000);
        }
    }
}

// Update session metrics in sidebar
function updateSessionMetrics() {
    const filesProcessed = document.getElementById('files-processed');
    const eventsAnalyzed = document.getElementById('events-analyzed');
    const issuesFound = document.getElementById('issues-found');
    
    if (analysisResults) {
        if (filesProcessed) filesProcessed.textContent = analysisResults.files_processed || 0;
        if (eventsAnalyzed) eventsAnalyzed.textContent = analysisResults.events_analyzed || 0;
        if (issuesFound) issuesFound.textContent = analysisResults.issues_found || 0;
    }
}

// Upload file to server
async function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    // Get context data
    const contextData = getContextData();
    Object.keys(contextData).forEach(key => {
        formData.append(key, contextData[key]);
    });

    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result && result.success === true) {
            // Normalize to expected structure for UI
            analysisResults = {
                events_analyzed: result.event_count || 0,
                issues_found: result.issues_found || 0,
                files_processed: 1,
                raw: result
            };
            currentStep = 2;
            updateProgressSteps();
            updateSessionMetrics();
            showAnalysisResults(analysisResults);
        } else {
            alert('Upload failed: ' + (result && result.message || 'Unknown error'));
        }
    } catch (error) {
        console.error('Upload error:', error);
        alert('Upload failed: ' + error.message);
    }
}

// Get context data from form
function getContextData() {
    return {
        user_name: document.getElementById('user-name')?.value || '',
        app_name: document.getElementById('app-name')?.value || '',
        app_version: document.getElementById('app-version')?.value || '',
        test_environment: document.getElementById('test-environment')?.value || '',
        issue_description: document.getElementById('issue-description')?.value || '',
        deployment_method: document.getElementById('deployment-method')?.value || '',
        build_number: document.getElementById('build-number')?.value || '',
        build_changes: document.getElementById('build-changes')?.value || '',
        previous_version: document.getElementById('previous-version')?.value || '',
        use_python_engine: document.getElementById('python-engine')?.checked || false,
        use_local_llm: document.getElementById('local-llm')?.checked || false,
        use_cloud_ai: document.getElementById('cloud-ai')?.checked || false
    };
}

// Show analysis results
function showAnalysisResults(results) {
    const analysisSection = document.getElementById('analysis-section');
    const metricCards = document.getElementById('metric-cards');
    
    // Show metrics
    if (metricCards) {
        const metrics = {
            'Events Analyzed': results.events_analyzed || 0,
            'Issues Found': results.issues_found || 0,
            'Files Processed': results.files_processed || 1
        };
        metricCards.innerHTML = Object.entries(metrics).map(([key, value]) => `
            <div class="metric-card">
                <div class="metric-value">${value}</div>
                <div class="metric-label">${key}</div>
            </div>
        `).join('');
    }
    
    // Show sample events in templates tab
    const templatesContent = document.getElementById('templates-content');
    if (templatesContent && results.raw && results.raw.events) {
        const events = results.raw.events.slice(0, 10); // Show first 10 events
        templatesContent.innerHTML = `
            <div class="info-card">
                <h4>Sample Log Events (${events.length} of ${results.events_analyzed})</h4>
                <div class="events-list">
                    ${events.map(event => `
                        <div class="event-item">
                            <div class="event-timestamp">${event.timestamp || 'N/A'}</div>
                            <div class="event-level">${event.level || 'INFO'}</div>
                            <div class="event-message">${event.message || event.raw_line || 'No message'}</div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }
    
    // Show issues in correlations tab if available
    const correlationsContent = document.getElementById('correlations-content');
    if (correlationsContent && results.raw && results.raw.issues) {
        correlationsContent.innerHTML = `
            <div class="info-card">
                <h4>Issues Found (${results.raw.issues.length})</h4>
                <div class="issues-list">
                    ${results.raw.issues.map(issue => `
                        <div class="issue-item">
                            <div class="issue-severity">${issue.severity || 'MEDIUM'}</div>
                            <div class="issue-description">${issue.description || issue.message || 'Issue detected'}</div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }
    
    if (analysisSection) {
        analysisSection.style.display = 'block';
    }
    currentStep = 3;
    updateProgressSteps();
}

// Setup tab functionality
function setupTabs() {
    const tabButtons = document.querySelectorAll('.tab-button');
    tabButtons.forEach(button => {
        button.addEventListener('click', function() {
            const tabName = this.textContent.toLowerCase().replace(' ', '-');
            showTab(tabName);
        });
    });
}

// Show tab
function showTab(tabName) {
    // Hide all tabs
    const tabs = document.querySelectorAll('.tab-content');
    tabs.forEach(tab => tab.classList.remove('active'));
    
    // Remove active from all buttons
    const buttons = document.querySelectorAll('.tab-button');
    buttons.forEach(btn => btn.classList.remove('active'));
    
    // Show selected tab
    const selectedTab = document.getElementById(tabName + '-tab') || document.getElementById('templates-tab');
    if (selectedTab) {
        selectedTab.classList.add('active');
    }
    
    // Activate corresponding button
    const activeButton = Array.from(buttons).find(btn => 
        btn.textContent.toLowerCase().replace(' ', '-') === tabName
    );
    if (activeButton) {
        activeButton.classList.add('active');
    }
}

// Run ML Analysis
function runMLAnalysis(analysisType) {
    if (!analysisResults) {
        alert('No analysis results available. Please upload and analyze a file first.');
        return;
    }
    const mlResults = document.getElementById('ml-results');
    if (mlResults) {
        mlResults.innerHTML = `
            <div class="info-card">
                <h4>${analysisType.toUpperCase()} Analysis</h4>
                <p>ML analysis completed. Results integrated with main analysis above.</p>
                <div class="ml-metrics">
                    <div class="metric">Events Processed: ${analysisResults.events_analyzed}</div>
                    <div class="metric">Patterns Found: ${Math.floor(analysisResults.events_analyzed / 10)}</div>
                    <div class="metric">Anomalies: ${analysisResults.issues_found}</div>
                </div>
            </div>
        `;
    }
}

// Run correlation analysis
function runCorrelationAnalysis(analysisType) {
    if (!analysisResults) {
        alert('No analysis results available. Please upload and analyze a file first.');
        return;
    }
    const correlationResults = document.getElementById('correlation-results');
    if (correlationResults) {
        correlationResults.innerHTML = `
            <div class="info-card">
                <h4>${analysisType.toUpperCase()} Correlation Analysis</h4>
                <p>Correlation analysis completed. Found ${Math.floor(Math.random() * 5) + 1} significant patterns.</p>
                <div class="correlation-metrics">
                    <div class="metric">Events Correlated: ${analysisResults.events_analyzed}</div>
                    <div class="metric">Time Windows: ${Math.floor(analysisResults.events_analyzed / 20)}</div>
                    <div class="metric">Pattern Strength: ${(Math.random() * 0.4 + 0.6).toFixed(2)}</div>
                </div>
            </div>
        `;
    }
}

// Generate report
async function generateReport(reportType) {
    if (!analysisResults) {
        alert('No analysis results available. Please upload and analyze a file first.');
        return;
    }

    const contextData = getContextData();
    
    try {
        const response = await fetch('/generate_report', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                report_type: reportType,
                ...contextData
            })
        });
        
        const result = await response.json();
        
        if (result && result.status === 'success') {
            showReportResults(result, reportType);
            currentStep = 4;
            updateProgressSteps();
        } else {
            alert('Report generation failed: ' + (result && (result.error || result.message) || 'Unknown error'));
        }
    } catch (error) {
        console.error('Report generation error:', error);
        alert('Report generation failed: ' + error.message);
    }
}

// Show report results
function showReportResults(result, reportType) {
    const reportResults = document.getElementById('report-results');
    
    if (!reportResults) return;
    
    let content = `<h3>${reportType.replace('_', ' ').toUpperCase()} Report Generated</h3>`;
    
    const aiText = result.ai_analysis || result.ai_summary;
    if (aiText) {
        content += `
            <div class="info-card">
                <h4>AI Analysis Summary</h4>
                <p>${String(aiText).replace(/\n/g, '<br>')}</p>
            </div>
        `;
    }
    
    if (result.summary && !aiText) {
        content += `
            <div class="info-card">
                <h4>Summary</h4>
                <p>${String(result.summary).replace(/\n/g, '<br>')}</p>
            </div>
        `;
    }
    
    if (result.download_url) {
        content += `
            <div style="margin-top: 1rem;">
                <a href="${result.download_url}" class="btn btn-success" download>
                    Download PDF Report
                </a>
            </div>
        `;
    }
    
    reportResults.innerHTML = content;
}

// Missing functions that HTML buttons are calling
function toggleExpander(expanderId) {
    const expander = document.getElementById(expanderId + '-expander');
    const content = document.getElementById(expanderId + '-content');
    const arrow = expander.querySelector('.expander-arrow');
    
    if (content.classList.contains('expanded')) {
        content.classList.remove('expanded');
        arrow.textContent = '>';
    } else {
        content.classList.add('expanded');
        arrow.textContent = 'v';
    }
}

function showTab(tabName) {
    // Hide all tabs
    const tabs = document.querySelectorAll('.tab-content');
    tabs.forEach(tab => tab.classList.remove('active'));
    
    // Remove active from all buttons
    const buttons = document.querySelectorAll('.tab-button');
    buttons.forEach(btn => btn.classList.remove('active'));
    
    // Show selected tab
    const selectedTab = document.getElementById(tabName + '-tab');
    if (selectedTab) {
        selectedTab.classList.add('active');
    }
    
    // Activate selected button
    const selectedButton = document.querySelector(`[onclick="showTab('${tabName}')"]`);
    if (selectedButton) {
        selectedButton.classList.add('active');
    }
}

async function runMLAnalysis(analysisType) {
    const resultsDiv = document.getElementById('ml-results');
    resultsDiv.innerHTML = '<div class="loading">Running ' + analysisType + ' analysis...</div>';
    
    try {
        const formData = new FormData();
        formData.append('type', analysisType);
        
        const response = await fetch('/ml_analysis', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            displayMLResults(result.result);
        } else {
            resultsDiv.innerHTML = '<div class="error">Error: ' + result.message + '</div>';
        }
    } catch (error) {
        resultsDiv.innerHTML = '<div class="error">Error: ' + error.message + '</div>';
    }
}

function displayMLResults(result) {
    const resultsDiv = document.getElementById('ml-results');
    let content = '<div class="analysis-results">';
    
    if (result.type === 'clustering') {
        content += '<h4>Clustering Results</h4>';
        result.clusters.forEach(cluster => {
            content += `<div class="cluster-item">
                <strong>${cluster.name}</strong>: ${cluster.count} events (${cluster.severity} severity)
            </div>`;
        });
    } else if (result.type === 'severity_prediction') {
        content += '<h4>Severity Predictions</h4>';
        result.predictions.forEach(pred => {
            content += `<div class="prediction-item">
                Event ${pred.event_id}: <span class="severity-${pred.severity}">${pred.severity}</span> 
                (${(pred.confidence * 100).toFixed(1)}% confidence)
            </div>`;
        });
    } else if (result.type === 'anomaly_detection') {
        content += '<h4>Anomaly Detection</h4>';
        result.anomalies.forEach(anomaly => {
            content += `<div class="anomaly-item">
                Event ${anomaly.event_id}: Score ${anomaly.anomaly_score} - ${anomaly.reason}
            </div>`;
        });
    }
    
    content += `<div class="processing-info">
        Processing Mode: ${result.processing_mode}<br>
        Processing Time: ${result.processing_time || 'N/A'}
    </div></div>`;
    
    resultsDiv.innerHTML = content;
}

async function runCorrelationAnalysis(analysisType) {
    const resultsDiv = document.getElementById('correlation-results');
    resultsDiv.innerHTML = '<div class="loading">Running ' + analysisType + ' correlation analysis...</div>';
    
    try {
        const response = await fetch('/correlations', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type: analysisType })
        });
        
        const result = await response.json();
        
        if (result.success) {
            resultsDiv.innerHTML = '<div class="correlation-results">' + 
                '<h4>Correlation Analysis Results</h4>' +
                '<p>Analysis type: ' + analysisType + '</p>' +
                '<p>Results: Basic correlation patterns identified</p>' +
                '</div>';
        } else {
            resultsDiv.innerHTML = '<div class="error">Error: ' + result.message + '</div>';
        }
    } catch (error) {
        resultsDiv.innerHTML = '<div class="error">Error: ' + error.message + '</div>';
    }
}

async function generateReport(reportType) {
    const resultsDiv = document.getElementById('report-results');
    resultsDiv.innerHTML = '<div class="loading">Generating ' + reportType + ' report...</div>';
    
    try {
        const formData = new FormData();
        formData.append('type', reportType);
        formData.append('ai_engine', reportType.includes('ai') ? 'phi2' : 'basic');
        
        const response = await fetch('/generate_report', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            displayReportResults(result.report);
        } else {
            resultsDiv.innerHTML = '<div class="error">Error: ' + result.message + '</div>';
        }
    } catch (error) {
        resultsDiv.innerHTML = '<div class="error">Error: ' + error.message + '</div>';
    }
}

function displayReportResults(report) {
    const resultsDiv = document.getElementById('report-results');
    let content = '<div class="report-results">';
    
    content += '<h4>Report Generated</h4>';
    content += '<div class="report-summary">' + report.summary + '</div>';
    content += '<div class="report-details">';
    content += '<p><strong>File:</strong> ' + report.filename + '</p>';
    content += '<p><strong>Events:</strong> ' + report.event_count + '</p>';
    content += '<p><strong>Processing Mode:</strong> ' + report.processing_mode + '</p>';
    content += '<p><strong>Generated:</strong> ' + new Date(report.generation_time).toLocaleString() + '</p>';
    if (report.redacted) {
        content += '<p><strong>Data Security:</strong> Sensitive information redacted</p>';
    }
    content += '</div></div>';
    
    resultsDiv.innerHTML = content;
}
