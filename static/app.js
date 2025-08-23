// Global state
let currentStep = 0;
let contextSubmitted = false;
let analysisData = null;

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('sessionId').textContent = 'LS-' + Date.now().toString(36).toUpperCase();
    updateProgress(0);
    setupEventListeners();
});

// Progress management
function updateProgress(step) {
    currentStep = step;
    const progress = (step / 4) * 100;
    document.getElementById('progressFill').style.width = progress + '%';
}

// Expandable sections
function toggleExpander(header) {
    const content = header.nextElementSibling;
    const arrow = header.querySelector('.expander-arrow');
    
    content.classList.toggle('expanded');
    arrow.classList.toggle('expanded');
    arrow.textContent = content.classList.contains('expanded') ? '▼' : '▶';
}

// Setup event listeners
function setupEventListeners() {
    // Context form submission
    document.getElementById('contextForm').addEventListener('submit', handleContextSubmit);
    
    // File input change
    document.getElementById('fileInput').addEventListener('change', handleFileSelect);
    
    // Analyze button
    document.getElementById('analyzeBtn').addEventListener('click', handleAnalyze);
    
    // Drag and drop
    const uploadArea = document.getElementById('uploadArea');
    uploadArea.addEventListener('dragover', handleDragOver);
    uploadArea.addEventListener('dragleave', handleDragLeave);
    uploadArea.addEventListener('drop', handleDrop);
    
    // Report buttons
    document.getElementById('standardReport').addEventListener('click', () => generateReport('standard'));
    document.getElementById('localAIReport').addEventListener('click', () => generateReport('local_ai'));
    document.getElementById('cloudAIReport').addEventListener('click', () => generateReport('cloud_ai'));
}

// Context form submission
async function handleContextSubmit(e) {
    e.preventDefault();
    
    // Validate required fields
    const userName = document.getElementById('userName').value;
    const appName = document.getElementById('appName').value;
    const issueDescription = document.getElementById('issueDescription').value;
    
    if (!userName || !appName || !issueDescription) {
        alert('Please fill in all required fields marked with *');
        return;
    }
    
    // Collect all form data
    const contextData = {
        user_name: userName,
        app_name: appName,
        app_version: document.getElementById('appVersion').value,
        test_environment: document.getElementById('testEnvironment').value,
        issue_description: issueDescription,
        deployment_method: document.getElementById('deploymentMethod').value,
        build_number: document.getElementById('buildNumber').value,
        build_changes: document.getElementById('buildChanges').value,
        previous_version: document.getElementById('previousVersion').value,
        hw_model: document.getElementById('hwModel').value,
        os_build: document.getElementById('osBuild').value,
        region: document.getElementById('region').value,
        test_run_id: document.getElementById('testRunId').value,
        network_constraints: document.getElementById('networkConstraints').value,
        proxy_config: document.getElementById('proxyConfig').value,
        device_sku: document.getElementById('deviceSku').value,
        notes_private: document.getElementById('notesPrivate').value
    };
    
    try {
        const response = await fetch('/submit_context', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(contextData)
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            contextSubmitted = true;
            updateProgress(1);
            document.getElementById('uploadSection').style.display = 'block';
            
            // Show success message
            const successDiv = document.createElement('div');
            successDiv.className = 'info info-success';
            successDiv.innerHTML = '<strong>Context saved successfully!</strong> You can now upload your log files.';
            document.getElementById('uploadSection').insertBefore(successDiv, document.getElementById('uploadSection').firstChild);
            
            // Scroll to upload section
            document.getElementById('uploadSection').scrollIntoView({ behavior: 'smooth' });
        } else {
            alert('Failed to save context: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        alert('Failed to save context: ' + error.message);
    }
}

// File selection handling
function handleFileSelect(e) {
    const file = e.target.files[0];
    if (file) {
        document.getElementById('fileInfo').innerHTML = `
            <div class="info info-success">
                <strong>File selected:</strong> ${file.name} (${(file.size / 1024).toFixed(1)} KB)
            </div>
        `;
        document.getElementById('fileInfo').style.display = 'block';
        document.getElementById('analyzeBtn').style.display = 'block';
        updateProgress(2);
    }
}

// Drag and drop handlers
function handleDragOver(e) {
    e.preventDefault();
    document.getElementById('uploadArea').classList.add('dragover');
}

function handleDragLeave(e) {
    e.preventDefault();
    document.getElementById('uploadArea').classList.remove('dragover');
}

function handleDrop(e) {
    e.preventDefault();
    document.getElementById('uploadArea').classList.remove('dragover');
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        document.getElementById('fileInput').files = files;
        document.getElementById('fileInput').dispatchEvent(new Event('change'));
    }
}

// Analyze button handler
async function handleAnalyze() {
    if (!contextSubmitted) {
        alert('Please submit the context form first');
        return;
    }
    
    const fileInput = document.getElementById('fileInput');
    const file = fileInput.files[0];
    
    if (!file) {
        alert('Please select a file first');
        return;
    }
    
    const analyzeBtn = document.getElementById('analyzeBtn');
    
    // Show loading
    analyzeBtn.innerHTML = '<span class="spinner"></span>Analyzing...';
    analyzeBtn.disabled = true;
    
    // Create form data
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch('/analyze', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.error) {
            throw new Error(result.error);
        }
        
        // Store analysis data
        analysisData = result;
        
        // Show results
        updateProgress(3);
        document.getElementById('resultsSection').style.display = 'block';
        displayResults(result);
        
        // Scroll to results
        document.getElementById('resultsSection').scrollIntoView({ behavior: 'smooth' });
        
    } catch (error) {
        alert('Analysis failed: ' + error.message);
    } finally {
        analyzeBtn.innerHTML = 'Analyze Log File';
        analyzeBtn.disabled = false;
    }
}

// Tab switching
function showTab(tabName) {
    document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    
    event.target.classList.add('active');
    document.getElementById(tabName + 'Tab').classList.add('active');
}

// Display analysis results
function displayResults(result) {
    // Show metric cards
    if (result.events_count !== undefined) {
        const metricsHtml = `
            <div class="metric-card">
                <h3>${result.events_count || 0}</h3>
                <p>Total Events</p>
            </div>
            <div class="metric-card">
                <h3>${result.issues_found || 0}</h3>
                <p>Issues Found</p>
            </div>
            <div class="metric-card">
                <h3>${result.critical_errors || 0}</h3>
                <p>Critical Errors</p>
            </div>
            <div class="metric-card">
                <h3>${result.warnings || 0}</h3>
                <p>Warnings</p>
            </div>
        `;
        document.getElementById('metricCards').innerHTML = metricsHtml;
        document.getElementById('metricCards').style.display = 'grid';
    }
    
    // Display timeline and issues
    displayTimelineResults(result);
    displayIssuesResults(result);
}

// Display timeline results
function displayTimelineResults(result) {
    const timelineDiv = document.getElementById('timelineResults');
    
    if (result.events && result.events.length > 0) {
        let timelineHtml = '<h4>Event Timeline</h4>';
        timelineHtml += '<table class="data-table"><thead><tr><th>Time</th><th>Level</th><th>Message</th></tr></thead><tbody>';
        
        result.events.slice(0, 20).forEach(event => {
            const levelClass = event.level === 'ERROR' ? 'error' : event.level === 'WARNING' ? 'warning' : '';
            timelineHtml += `
                <tr>
                    <td>${event.timestamp || 'N/A'}</td>
                    <td><span class="${levelClass}">${event.level || 'INFO'}</span></td>
                    <td>${event.message || event.content || ''}</td>
                </tr>
            `;
        });
        
        timelineHtml += '</tbody></table>';
        
        if (result.events.length > 20) {
            timelineHtml += `<p><em>Showing first 20 of ${result.events.length} events</em></p>`;
        }
        
        timelineDiv.innerHTML = timelineHtml;
    } else {
        timelineDiv.innerHTML = '<p>No timeline data available</p>';
    }
}

// Display issues results
function displayIssuesResults(result) {
    const issuesDiv = document.getElementById('issuesResults');
    
    if (result.issues && result.issues.length > 0) {
        let issuesHtml = '<h4>Issues Identified</h4>';
        
        result.issues.forEach(issue => {
            issuesHtml += `
                <div class="event-item">
                    <strong>${issue.type || 'Issue'}</strong>: ${issue.description || issue.message || 'No description'}
                    ${issue.count ? `<br><small>Occurrences: ${issue.count}</small>` : ''}
                </div>
            `;
        });
        
        issuesDiv.innerHTML = issuesHtml;
    } else {
        issuesDiv.innerHTML = '<p>No specific issues identified</p>';
    }
}

// Generate reports
async function generateReport(reportType) {
    if (!analysisData) {
        alert('Please analyze a log file first');
        return;
    }
    
    const button = event.target;
    const originalText = button.innerHTML;
    
    // Show loading
    button.innerHTML = '<span class="spinner"></span>Generating...';
    button.disabled = true;
    
    try {
        const response = await fetch('/generate_report', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                report_type: reportType,
                use_local_llm: document.getElementById('useLocalLLM').checked,
                use_cloud_ai: document.getElementById('useCloudAI').checked,
                use_python_engine: document.getElementById('usePythonEngine').checked
            })
        });
        
        const result = await response.json();
        
        if (result.error) {
            throw new Error(result.error);
        }
        
        // Display report results
        displayReportResults(result, reportType);
        
        updateProgress(4);
        
    } catch (error) {
        alert('Report generation failed: ' + error.message);
    } finally {
        button.innerHTML = originalText;
        button.disabled = false;
    }
}

// Display report results
function displayReportResults(result, reportType) {
    const reportDiv = document.getElementById('reportResults');
    
    let reportHtml = `<h4>${reportType.toUpperCase()} Report Generated</h4>`;
    
    if (result.ai_analysis) {
        reportHtml += `
            <div class="ai-section">
                <h5>🤖 AI Analysis</h5>
                <p>${result.ai_analysis}</p>
            </div>
        `;
    }
    
    if (result.summary) {
        reportHtml += `
            <div class="info">
                <strong>Summary:</strong> ${result.summary}
            </div>
        `;
    }
    
    if (result.recommendations && result.recommendations.length > 0) {
        reportHtml += '<h5>Recommendations:</h5><ul>';
        result.recommendations.forEach(rec => {
            reportHtml += `<li>${rec}</li>`;
        });
        reportHtml += '</ul>';
    }
    
    if (result.download_url) {
        reportHtml += `
            <div style="margin-top: 20px;">
                <a href="${result.download_url}" class="btn btn-success" download>📄 Download Report</a>
            </div>
        `;
    }
    
    reportDiv.innerHTML = reportHtml;
}

// ML Analysis functions
async function runClustering() {
    await runMLAnalysis('clustering', 'Run Clustering');
}

async function runSeverityPrediction() {
    await runMLAnalysis('severity', 'Severity Prediction');
}

async function runAnomalyDetection() {
    await runMLAnalysis('anomaly', 'Anomaly Detection');
}

async function runMLAnalysis(analysisType, buttonText) {
    if (!analysisData) {
        alert('Please analyze a log file first');
        return;
    }
    
    const button = event.target;
    const originalText = button.innerHTML;
    
    button.innerHTML = '<span class="spinner"></span>Running...';
    button.disabled = true;
    
    try {
        const response = await fetch('/ml_analysis', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ analysis_type: analysisType })
        });
        
        const result = await response.json();
        
        if (result.error) {
            throw new Error(result.error);
        }
        
        // Display ML results
        displayMLResults(result, analysisType);
        
    } catch (error) {
        alert(`${buttonText} failed: ` + error.message);
    } finally {
        button.innerHTML = originalText;
        button.disabled = false;
    }
}

// Display ML results
function displayMLResults(result, analysisType) {
    const mlDiv = document.getElementById('mlResults');
    
    let resultsHtml = `<h5>${analysisType.toUpperCase()} Results</h5>`;
    
    if (result.clusters) {
        resultsHtml += '<h6>Clusters Found:</h6>';
        result.clusters.forEach((cluster, index) => {
            resultsHtml += `
                <div class="event-item">
                    <strong>Cluster ${index + 1}</strong> (${cluster.size} events)<br>
                    <small>${cluster.description || 'No description'}</small>
                </div>
            `;
        });
    }
    
    if (result.anomalies) {
        resultsHtml += '<h6>Anomalies Detected:</h6>';
        result.anomalies.forEach(anomaly => {
            resultsHtml += `
                <div class="event-item">
                    <strong>Anomaly:</strong> ${anomaly.description}<br>
                    <small>Score: ${anomaly.score}</small>
                </div>
            `;
        });
    }
    
    if (result.predictions) {
        resultsHtml += '<h6>Severity Predictions:</h6>';
        result.predictions.forEach(pred => {
            resultsHtml += `
                <div class="event-item">
                    <strong>${pred.level}:</strong> ${pred.message}<br>
                    <small>Confidence: ${pred.confidence}</small>
                </div>
            `;
        });
    }
    
    mlDiv.innerHTML = resultsHtml;
}
