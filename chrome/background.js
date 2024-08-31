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
