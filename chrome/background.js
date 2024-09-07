// Function to generate a unique ID
function generateUniqueId() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
    var r = (Math.random() * 16) | 0,
      v = c == 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

// Function to get the user's IP address
function getIP(callback) {
  fetch('https://api.ipify.org?format=json')
    .then((response) => response.json())
    .then((data) => callback(data.ip))
    .catch((error) => {
      console.error('Error fetching IP:', error);
      callback(null);
    });
}

// Function to get or create the unique user ID
function getUserId(callback) {
  chrome.storage.sync.get(['userId', 'userIp'], function (result) {
    if (result.userId && result.userIp) {
      callback(result.userId);
    } else {
      getIP(function (ip) {
        const newUserId = generateUniqueId() + '-' + (ip || 'unknown');
        chrome.storage.sync.set({ userId: newUserId, userIp: ip }, function () {
          callback(newUserId);
        });
      });
    }
  });
}

function generateUUID() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
    var r = (Math.random() * 16) | 0,
      v = c == 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

// Function to get or create user ID
function getUserId(callback) {
  chrome.storage.sync.get(['userId'], function (result) {
    if (result.userId) {
      callback(result.userId);
    } else {
      let newUserId = generateUUID();
      chrome.storage.sync.set({ userId: newUserId }, function () {
        callback(newUserId);
      });
    }
  });
}

chrome.runtime.onInstalled.addListener((details) => {
  chrome.contextMenus.create({
    id: 'factCheckMenu',
    title: 'Fact Check this',
    contexts: ['selection'],
  });

  if (details.reason === 'install') {
    getUserId(function (userId) {
      console.log('New user ID generated on install:', userId);
    });
  }
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
    let results = {
      summary: '',
      error: false,
    };

    getUserId(function (userId) {
    // Replace with your actual API endpoint
    fetch('http://localhost:5000/check-free', {
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
        .then((response) => {
          if (!response.ok) {
            if (response.status === 400) {
              throw new Error(
                'Bad Request: The server could not understand the request.'
              );
            } else if (response.status === 403) {
              throw new Error(
                'Forbidden: You have reached the limit of free fact checks. Please sign in to continue.'
              );
            } else {
              throw new Error(`HTTP error! status: ${response.status}`);
            }
          }

          return response.json();
        })
        .then((data) => {
          results = data;
          storeFactCheck(request.text, data);
        })
        .catch((error) => {
          console.error('Error:', error);
          results.error = true;
          if (
            error.message.startsWith('Bad Request:') ||
            error.message.startsWith('Forbidden:')
          ) {
            results.summary = error.message;
          } else {
            results.summary =
              'An error occurred while fact-checking. Please try again.';
          }
        })
        .finally(() => {
          // Always send a message back to the content script
          chrome.tabs.sendMessage(sender.tab.id, {
            action: 'displayResults',
            results: results,
          });
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
