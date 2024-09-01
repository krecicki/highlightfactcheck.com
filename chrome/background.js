chrome.runtime.onInstalled.addListener(() => {
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
    // Replace with your actual API endpoint
    fetch('http://localhost:5000/check', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ text: request.text }),
    })
      .then((response) => response.json())
      .then((data) => {
        storeFactCheck(request.text, data);
        chrome.tabs.sendMessage(sender.tab.id, {
          action: 'displayResults',
          results: data,
        });
      })
      .catch((error) => {
        console.error('Error:', error);
        chrome.tabs.sendMessage(sender.tab.id, {
          action: 'displayResults',
          results: {
            summary: 'An error occurred while fact-checking. Please try again.',
          },
        });
      });
  }
  // send the response asychronously
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

    console.log('Fack checks: ', factChecks);
    // Keep only the last 100 fact checks
    if (factChecks.length > 100) {
      factChecks = factChecks.slice(-100);
    }
    chrome.storage.local.set({ factChecks: factChecks }, function () {
      if (chrome.runtime.lastError) {
        console.error('Error storing fact check:', chrome.runtime.lastError);
      } else {
        console.log('Fact check stored successfully');
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
