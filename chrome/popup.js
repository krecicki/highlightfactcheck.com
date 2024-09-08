document.addEventListener('DOMContentLoaded', function () {
  document
    .getElementById('history-link')
    .addEventListener('click', function () {
      chrome.tabs.create({ url: 'history.html' });
    });

  document
    .getElementById('options-link')
    .addEventListener('click', function () {
      chrome.tabs.create({ url: 'options.html' });
    });

  document
    .getElementById('purchase-link')
    .addEventListener('click', function () {
      chrome.tabs.create({ url: 'https://highlightfactcheck.com' });
    });
});
