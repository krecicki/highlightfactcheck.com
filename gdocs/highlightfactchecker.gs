const API_URL = 'https://highlightfactcheck.com/check';

function onOpen() {
  DocumentApp.getUi()
    .createMenu('Fact Checker')
    .addItem('Fact Check', 'factCheck')
    .addItem('Settings', 'showSettings')
    .addToUi();
}

function factCheck() {
  const doc = DocumentApp.getActiveDocument();
  const selection = doc.getSelection();

  if (!selection) {
    DocumentApp.getUi().alert('Please select some text to fact-check.');
    return;
  }

  const selectedText = selection
    .getRangeElements()
    .map((element) => element.getElement().asText().getText())
    .join(' ');

  // Call your backend API here
  const factCheckResults = callFactCheckAPI(selectedText);
  showSidebar(factCheckResults);
}

function callFactCheckAPI(text) {
  const apiKey = PropertiesService.getUserProperties().getProperty('API_KEY');

  if (!apiKey) {
    throw new Error(
      'API key not set. Please go to Fact Checker > Settings to set your API key.'
    );
  }

  const options = {
    method: 'POST',
    headers: {
      'x-api-key': apiKey,
      'content-type': 'application/json',
    },
    payload: JSON.stringify({ text: text }),
  };
  const response = UrlFetchApp.fetch(API_URL, options);

  console.log('API Response Code:', response.getResponseCode());
  console.log('API Response Content:', response.getContentText());

  if (response.getResponseCode() !== 200) {
    throw new Error(
      'API request failed with status ' + response.getResponseCode()
    );
  }

  const result = JSON.parse(response.getContentText());
  return result;
}

function showSettings() {
  const html = HtmlService.createHtmlOutput(
    `
    <h2>Fact Checker Settings</h2>
    <form id="settingsForm">
      <label for="apiKey">API Key:</label><br>
      <input type="password" id="apiKey" name="apiKey"><br><br>
      <input type="submit" value="Save">
    </form>
    <script>
      function handleSubmit(event) {
        event.preventDefault();
        const apiKey = document.getElementById('apiKey').value;
        google.script.run.withSuccessHandler(onSuccess).saveApiKey(apiKey);
      }
      function onSuccess() {
        alert('API key saved successfully');
      }
      document.getElementById('settingsForm').addEventListener('submit', handleSubmit);
    </script>
  `
  )
    .setWidth(300)
    .setHeight(200);

  DocumentApp.getUi().showModalDialog(html, 'Settings');
}

function saveApiKey(apiKey) {
  PropertiesService.getUserProperties().setProperty('API_KEY', apiKey);
}

function showSidebar(results) {
  const html = HtmlService.createHtmlOutput(createSidebarContent(results))
    .setTitle('Fact Check Results')
    .setWidth(400);
  DocumentApp.getUi().showSidebar(html);
}

function createSidebarContent(results) {
  if (!Array.isArray(results) || results.length === 0) {
    return '<h2>Error</h2><p>No valid fact-check results received.</p>';
  }

  function createFactCheckResult(factCheck, index) {
    const ratingEmoji = getRatingEmoji(factCheck.rating);
    const severityEmoji = getSeverityEmoji(factCheck.severity);
    const ratingColor = getRatingColor(factCheck.rating);

    return `
      <div class="fact-check-result" style="margin-bottom: 20px; border: 1px solid #e9ecef; border-radius: 8px; overflow: hidden;">
        <div class="sentence-header" onclick="toggleSentence(${index})" style="background-color: ${
      index === 0 ? '#e9ecef' : '#f8f9fa'
    }; padding: 10px; cursor: pointer;">
          <span>${factCheck.sentence}</span>
        </div>
        <div id="details-${index}" class="details" style="display: ${
      index === 0 ? 'block' : 'none'
    }; padding: 15px;">
          <div style="display: flex; justify-content: space-between; margin-bottom: 15px;">
            <p style="font-size: 14px; margin: 0;">
              <strong>Rating:</strong> 
              <span style="color: ${ratingColor};">${ratingEmoji} ${
      factCheck.rating
    }</span>
            </p>
            <p style="font-size: 14px; margin: 0;">
              <strong>Severity:</strong> ${severityEmoji} ${factCheck.severity}
            </p>
          </div>
          <div class="explanation-container" style="margin-bottom: 15px; border: 1px solid #e9ecef; border-radius: 8px; overflow: hidden;">
            <div class="explanation-header" onclick="toggleExplanation(${index})" style="background-color: #f8f9fa; padding: 10px; cursor: pointer;">
              <strong>Explanation</strong> <span id="toggle-icon-${index}">▼</span>
            </div>
            <div id="explanation-${index}" class="explanation-content" style="padding: 15px; display: none;">
              ${factCheck.explanation}
            </div>
          </div>
          <p style="margin-bottom: 15px;"><strong>Key Points:</strong></p>
          <ul style="margin-bottom: 15px; padding-left: 20px;">
            ${factCheck.key_points.map((point) => `<li>${point}</li>`).join('')}
          </ul>
          <p style="margin-bottom: 15px;"><strong>Sources:</strong></p>
          <ul style="padding-left: 20px;">
            ${factCheck.source
              .map(
                (src) => `
              <li style="margin-bottom: 5px; word-break: break-all;">
                <a href="${src}" target="_blank" rel="noopener noreferrer" style="color: #007bff; text-decoration: none;">
                  ${src}
                </a>
              </li>
            `
              )
              .join('')}
          </ul>
        </div>
      </div>
    `;
  }

  let html = `
    <h3 style="margin-top: 0; color: #333333; border-bottom: 2px solid #ddd; padding-bottom: 10px;">Fact Check Results</h3>
    ${results
      .map((result, index) => createFactCheckResult(result, index))
      .join('')}
    <script>
      function toggleSentence(index) {
        var allDetails = document.getElementsByClassName('details');
        var allHeaders = document.getElementsByClassName('sentence-header');
        
        for (var i = 0; i < allDetails.length; i++) {
          if (i === index) {
            allDetails[i].style.display = allDetails[i].style.display === 'none' ? 'block' : 'none';
            allHeaders[i].style.backgroundColor = allDetails[i].style.display === 'none' ? '#f8f9fa' : '#e9ecef';
          } else {
            allDetails[i].style.display = 'none';
            allHeaders[i].style.backgroundColor = '#f8f9fa';
          }
        }
      }

      function toggleExplanation(index) {
        var explanation = document.getElementById('explanation-' + index);
        var toggleIcon = document.getElementById('toggle-icon-' + index);
        if (explanation.style.display === 'none') {
          explanation.style.display = 'block';
          toggleIcon.textContent = '▲';
        } else {
          explanation.style.display = 'none';
          toggleIcon.textContent = '▼';
        }
      }
    </script>
  `;

  return html;
}

function getRatingEmoji(rating) {
  const ratingMap = {
    True: '✅',
    'Mostly True': '✅',
    'Half True': '🟨',
    'Mostly False': '❌',
    False: '❌',
    'Pants on Fire': '🔥',
  };
  return ratingMap[rating] || '❓';
}

function getSeverityEmoji(severity) {
  const severityMap = {
    Low: '🟢',
    Medium: '🟠',
    High: '🔴',
  };
  return severityMap[severity] || '⚪';
}

function getRatingColor(rating) {
  const colorMap = {
    True: '#28a745',
    'Mostly True': '#5cb85c',
    'Half True': '#ffc107',
    'Mostly False': '#dc3545',
    False: '#dc3545',
    'Pants on Fire': '#bd2130',
  };
  return colorMap[rating] || '#6c757d';
}
