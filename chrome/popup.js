document.addEventListener('DOMContentLoaded', function () {
  document
    .getElementById('history-link')
    .addEventListener('click', function () {
      chrome.tabs.create({ url: 'history.html' });
    });
});
