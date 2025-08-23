// JavaScript for LogSense Modal Native App

let currentStep = 0;
let analysisResults = null;

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    updateProgressSteps();
    setupFileUpload();
    setupExpanders();
    setupTabs();
});

// Update progress indicator
function updateProgressSteps() {
    const steps = document.querySelectorAll('.progress-step');
    steps.forEach((step, index) => {
        step.classList.remove('active', 'completed');
        const icon = step.querySelector('.step-icon');
        
        if (index < currentStep) {
            step.classList.add('completed');
            icon.textContent = 'DONE';
        } else if (index === currentStep) {
            step.classList.add('active');
            icon.textContent = 'ACTIVE';
        } else {
            icon.textContent = 'PENDING';
        }
    });
}

// Setup expander functionality
function setupExpanders() {
    const expanders = document.querySelectorAll('.expander-header');
    expanders.forEach(header => {
        header.addEventListener('click', function() {
            const expanderId = this.parentElement.id.replace('-expander', '');
            toggleExpander(expanderId);
        });
    });
}

// Toggle expander
function toggleExpander(expanderId) {
    const content = document.getElementById(expanderId + '-content');
    const arrow = document.querySelector(`#${expanderId}-expander .expander-arrow`);
    
    if (content.classList.contains('expanded')) {
        content.classList.remove('expanded');
        arrow.textContent = '▶';
    } else {
        content.classList.add('expanded');
        arrow.textContent = '▼';
    }
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
function applyContext() {
    // Update session metrics
    updateSessionMetrics();
    
    // Show success message
    const button = event.target;
    const originalText = button.textContent;
    button.textContent = 'Applied!';
    button.style.backgroundColor = '#00c851';
    
    setTimeout(() => {
        button.textContent = originalText;
        button.style.backgroundColor = '';
    }, 2000);
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
        
        if (result.success) {
            analysisResults = result;
            currentStep = 2;
            updateProgressSteps();
            updateSessionMetrics();
            showAnalysisResults(result);
        } else {
            alert('Upload failed: ' + result.error);
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
    if (results.metrics && metricCards) {
        metricCards.innerHTML = Object.entries(results.metrics).map(([key, value]) => `
            <div class="metric-card">
                <div class="metric-value">${value}</div>
                <div class="metric-label">${key}</div>
            </div>
        `).join('');
    }
    
    if (analysisSection) {
        analysisSection.style.display = 'block';
    }
    currentStep = 3;
    updateProgressSteps();
}

// Run ML Analysis
async function runMLAnalysis(analysisType) {
    if (!analysisResults) {
        alert('No analysis results available. Please upload and analyze a file first.');
        return;
    }

    try {
        const response = await fetch('/ml_analysis', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                analysis_type: analysisType
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            const mlResults = document.getElementById('ml-results');
            if (mlResults) {
                mlResults.innerHTML = `
                    <div class="info-card">
                        <h4>${analysisType.toUpperCase()} Analysis Complete</h4>
                        <p>${result.summary || 'Analysis completed successfully.'}</p>
                    </div>
                `;
            }
        } else {
            alert('ML Analysis failed: ' + result.error);
        }
    } catch (error) {
        console.error('ML Analysis error:', error);
        alert('ML Analysis failed: ' + error.message);
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
        
        if (result.success) {
            showReportResults(result, reportType);
            currentStep = 4;
            updateProgressSteps();
        } else {
            alert('Report generation failed: ' + result.error);
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
    
    if (result.ai_summary) {
        content += `
            <div class="info-card">
                <h4>AI Analysis Summary</h4>
                <p>${result.ai_summary.replace(/\n/g, '<br>')}</p>
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
