// settings.js
document.addEventListener('DOMContentLoaded', function () {
  const apiKeyInput = document.getElementById('apiKey');
  const saveBtn = document.getElementById('saveBtn');
  const deleteBtn = document.getElementById('deleteBtn');
  const statusElement = document.getElementById('status');

  // Load saved API key
  chrome.storage.sync.get(['apiKey'], function (result) {
    if (result.apiKey) {
      apiKeyInput.value = result.apiKey;
    }
  });

  // Save API key
  saveBtn.addEventListener('click', function () {
    const apiKey = apiKeyInput.value.trim();
    if (apiKey) {
      chrome.storage.sync.set({ apiKey: apiKey }, function () {
        statusElement.textContent = 'API key saved successfully.';
        setTimeout(() => (statusElement.textContent = ''), 3000);
      });
    } else {
      statusElement.textContent = 'Please enter a valid API key.';
    }
  });

  // Delete API key
  deleteBtn.addEventListener('click', function () {
    chrome.storage.sync.remove('apiKey', function () {
      apiKeyInput.value = '';
      statusElement.textContent = 'API key deleted successfully.';
      setTimeout(() => (statusElement.textContent = ''), 3000);
    });
  });
});
