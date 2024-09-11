chrome.runtime.onInstalled.addListener((details) => {
  chrome.contextMenus.create({
    id: 'factCheckMenu',
    title: 'Fact Check this',
    contexts: ['selection'],
  });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === 'factCheckMenu') {
    chrome.tabs.sendMessage(tab.id, {
      action: 'factCheck',
      text: info.selectionText,
    });
  }
});

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'factCheckAPI') {
    chrome.storage.sync.get(['apiKey'], function (result) {
      const apiKey = result.apiKey;
      //let endpoint = 'http://localhost:5000/check-free';
      let endpoint = 'https://highlightfactcheck.com/check-free'
      let headers = {
        'Content-Type': 'application/json',
      };

      if (apiKey) {
        //endpoint = 'http://localhost:5000/check';
        endpoint = 'https://highlightfactcheck.com/check';
        headers['x-api-key'] = apiKey;
      }

      fetch(endpoint, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify({ text: request.text }),
      })
        .then((response) => {
          if (response.status === 200) {
            return response.json();
          } else if (response.status === 400) {
            return {
              error:
                'Bad Request: The server could not understand the request.',
            };
          } else if (response.status === 401) {
            return {
              error: 'Unauthorized: Please provide a valid API key.',
            };
          } else if (response.status === 429) {
            return {
              error:
                'Forbidden: You have reached the limit of free fact checks. Please <a href="https://highlightfactcheck.com">sign</a> in to continue.',
            };
          } else {
            return {
              error: `HTTP error! status: ${response.status} ${response.statusText}`,
            };
          }
        })
        .then((data) => {
          if (data.error) {
            chrome.tabs.sendMessage(sender.tab.id, {
              action: 'displayError',
              error: data.error,
            });
          } else {
            storeFactCheck(request.text, data);
            chrome.tabs.sendMessage(sender.tab.id, {
              action: 'displayResults',
              results: data,
            });
          }
        })
        .catch((error) => {
          console.error('Network Error:', error);
          chrome.tabs.sendMessage(sender.tab.id, {
            action: 'displayError',
            error:
              'An error occurred while fact-checking. Please check your internet connection and try again.',
          });
        });
    });
  }
  return true;
});

function storeFactCheck(text, result) {
  chrome.storage.local.get({ factChecks: [] }, function (data) {
    let factChecks = data.factChecks;
    factChecks.push({
      text: text,
      // TODO: Only get the first sentence for now. This needs to be fixed.
      result: { ...result[0] },
      timestamp: new Date().toISOString(),
    });
    // Keep only the last 100 fact checks
    if (factChecks.length > 100) {
      factChecks = factChecks.slice(-100);
    }
    chrome.storage.local.set({ factChecks: factChecks }, function () {
      if (chrome.runtime.lastError) {
        console.error('Error storing fact check:', chrome.runtime.lastError);
      }
    });
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
  return emojiMap[severity] || '⚪';
}
