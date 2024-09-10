chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'factCheck') {
    showLoadingIndicator();
    chrome.runtime.sendMessage({
      action: 'factCheckAPI',
      text: request.text,
    });
  } else if (request.action === 'displayResults') {
    hideLoadingIndicator();

    const results = request.results;
    displayFactCheckResults(results);
  } else if (request.action === 'displayError') {
    hideLoadingIndicator();
    displayError(request.error);
  }
});

function getErrorDisplayDiv() {
  let errorDiv = document.createElement('div');
  errorDiv.id = 'fact-check-error-display';
  errorDiv.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      background-color: #ff6b6b;
      color: white;
      padding: 15px;
      border-radius: 5px;
      max-width: 300px;
      z-index: 10000;
      display: none;
    `;
  document.body.appendChild(errorDiv);

  return errorDiv;
}

// Function to display error message
function displayError(message) {
  const errorDiv = getErrorDisplayDiv();
  errorDiv.innerHTML = `<div>${message}</div>`;
  errorDiv.style.display = 'block';

  // Hide the error message after 5 seconds
  setTimeout(() => {
    errorDiv.style.display = 'none';
  }, 8000);
}

function showLoadingIndicator() {
  let loadingDiv = document.createElement('div');
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
    <h3 class="uk-h3">Fact Checking in Progress</h3>
    <div class="loading-spinner"></div>
    <p class="uk-text-default uk-text-bold">Please wait while we verify the information...</p>
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
  const loadingDiv = document.getElementById('fact-check-loading');
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
    width: 400px;
    max-height: 80vh;
    padding: 20px;
    background-color: #ffffff;
    color: #333333;
    border-radius: 8px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    font-family: Arial, sans-serif;
    z-index: 9999;
    overflow-y: auto;
    transition: all 0.3s ease;
  `;

  const factCheck = results[0];
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
    <button id="fullscreen-fact-check" style="
      background-color: #28a745;
      color: white;
      border: none;
      padding: 8px 16px;
      border-radius: 4px;
      cursor: pointer;
      margin-right: 10px;
    ">Full Screen</button>
    <button id="close-fact-check" style="
      background-color: #007bff;
      color: white;
      border: none;
      padding: 8px 16px;
      border-radius: 4px;
      cursor: pointer;
    ">Close</button>
  `;

  document.body.appendChild(resultDiv);

  const fullscreenButton = document.getElementById('fullscreen-fact-check');
  const closeButton = document.getElementById('close-fact-check');

  let isFullScreen = false;

  fullscreenButton.addEventListener('click', () => {
    if (isFullScreen) {
      resultDiv.style.top = '10px';
      resultDiv.style.right = '10px';
      resultDiv.style.width = '400px';
      resultDiv.style.height = 'auto';
      resultDiv.style.maxHeight = '80vh';
      fullscreenButton.textContent = 'Full Screen';
    } else {
      resultDiv.style.top = '0';
      resultDiv.style.right = '0';
      resultDiv.style.width = '100%';
      resultDiv.style.height = '100%';
      resultDiv.style.maxHeight = '100%';
      fullscreenButton.textContent = 'Exit Full Screen';
    }
    isFullScreen = !isFullScreen;
  });

  closeButton.addEventListener('click', () => {
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
