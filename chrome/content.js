let loadingDiv;

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'factCheck') {
    showLoadingIndicator();
    chrome.runtime.sendMessage({
      action: 'factCheckAPI',
      text: request.text,
    });
  } else if (request.action === 'displayResults') {
    hideLoadingIndicator();
    displayFactCheckResults(request.results);
  }
});

function showLoadingIndicator() {
  loadingDiv = document.createElement('div');
  loadingDiv.id = 'fact-check-loading';
  loadingDiv.style.cssText = `
    position: fixed;
    top: 10px;
    right: 10px;
    width: 300px;
    padding: 20px;
    background-color: white;
    border: 1px solid #ccc;
    box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    z-index: 9999;
    text-align: center;
  `;

  loadingDiv.innerHTML = `
    <h3>Fact Checking in Progress</h3>
    <div class="loading-spinner"></div>
    <p>Please wait while we verify the information...</p>
  `;

  const style = document.createElement('style');
  style.textContent = `
    .loading-spinner {
      border: 5px solid #f3f3f3;
      border-top: 5px solid #3498db;
      border-radius: 50%;
      width: 50px;
      height: 50px;
      animation: spin 1s linear infinite;
      margin: 20px auto;
    }
    @keyframes spin {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }
  `;

  document.head.appendChild(style);
  document.body.appendChild(loadingDiv);
}

function hideLoadingIndicator() {
  if (loadingDiv && loadingDiv.parentNode) {
    loadingDiv.parentNode.removeChild(loadingDiv);
  }
}

function displayFactCheckResults(results) {
  const resultDiv = document.createElement('div');
  resultDiv.id = 'fact-check-results';
  resultDiv.style.cssText = `
    position: fixed;
    top: 10px;
    right: 10px;
    width: 300px;
    padding: 20px;
    background-color: #ffffff;
    color: #333333;
    border-radius: 8px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    font-family: Arial, sans-serif;
    z-index: 9999;
  `;

  const factCheck = JSON.parse(results[0]);

  const ratingEmoji = getRatingEmoji(factCheck.rating);
  const severityEmoji = getSeverityEmoji(factCheck.severity);
  const ratingColor = getRatingColor(factCheck.rating);

  resultDiv.innerHTML = `
    <h3 style="margin-top: 0; color: #333333; border-bottom: 2px solid #ddd; padding-bottom: 10px;">Fact Check Results</h3>
    <p style="margin-bottom: 15px;"><strong>Sentence:</strong> ${factCheck.sentence}</p>
    <p style="margin-bottom: 15px;"><strong>Explanation:</strong> ${factCheck.explanation}</p>
    <p style="margin-bottom: 15px; font-size: 18px;">
      <strong>Rating:</strong> 
      <span style="color: ${ratingColor};">${ratingEmoji} ${factCheck.rating}</span>
    </p>
    <p style="margin-bottom: 15px;">
      <strong>Severity:</strong> ${severityEmoji} ${factCheck.severity}
    </p>
    <button id="close-fact-check" style="
      background-color: #007bff;
      color: white;
      border: none;
      padding: 8px 16px;
      border-radius: 4px;
      cursor: pointer;
      float: right;
    ">Close</button>
  `;

  document.body.appendChild(resultDiv);

  document.getElementById('close-fact-check').addEventListener('click', () => {
    document.body.removeChild(resultDiv);
  });
}

function getRatingEmoji(rating) {
  const emojiMap = {
    True: '✅',
    'Mostly True': '✔️',
    'Half True': '↕️',
    'Mostly False': '⚠️',
    False: '❌',
  };
  return emojiMap[rating] || '❓';
}

function getSeverityEmoji(severity) {
  const emojiMap = {
    high: '🔴',
    medium: '🟠',
    low: '🟢',
  };
  return emojiMap[severity.toLowerCase()] || '⚪';
}

function getRatingColor(rating) {
  const colorMap = {
    True: '#28a745',
    'Mostly True': '#5cb85c',
    'Half True': '#ffc107',
    'Mostly False': '#dc3545',
    False: '#dc3545',
  };
  return colorMap[rating] || '#6c757d';
}
