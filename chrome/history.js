document.addEventListener('DOMContentLoaded', function () {
  loadFactChecks();

  document
    .getElementById('clear-all-btn')
    .addEventListener('click', clearAllHistory);
});

function loadFactChecks() {
  chrome.storage.local.get({ factChecks: [] }, function (data) {
    const factChecksContainer = document.getElementById('fact-checks');
    const factChecks = data.factChecks.reverse(); // Show newest first

    factChecksContainer.innerHTML = ''; // Clear existing content

    if (factChecks.length === 0) {
      factChecksContainer.innerHTML =
        '<p class="uk-text-primary">No fact checks yet.</p>';
      return;
    }

    factChecks.forEach(function (check, index) {
      const checkElement = document.createElement('div');
      checkElement.className = 'uk-card uk-body uk-margin uk-padding';

      const parsedFactCheck = check.result;
      const ratingColor = getRatingColor(parsedFactCheck.rating);

      checkElement.innerHTML = `
        <h3 class="uk-h3">Claim</h3>
        <div class="uk-text-default uk-margin-small-top">
        ${parsedFactCheck.sentence}
        </div>
        
        <h3 class="uk-h3 uk-margin-small-top">Explanation</h3>
        <div class="uk-text-default uk-margin-small-top">
        ${parsedFactCheck.explanation || 'Not available'}</div>
        

        
        <ul class="uk-text-default uk-list uk-list-disc uk-margin">
          <li>Rating: <span class="uk-badge">${
            parsedFactCheck.rating
          }</span></li>
          <li>Severity:<span class="uk-badge">${
            parsedFactCheck.severity
          }</span> </li>
          <li>Timestamp: ${new Date(check.timestamp).toLocaleTimeString()}</li>
        </ul>

        <button class="uk-button uk-button-danger" data-index="${
          factChecks.length - 1 - index
        }">Delete</button>`;
      factChecksContainer.appendChild(checkElement);
    });

    // Add event listeners to delete buttons
    document.querySelectorAll('.uk-button-danger').forEach((button) => {
      button.addEventListener('click', function () {
        deleteFactCheck(parseInt(this.getAttribute('data-index')));
      });
    });
  });
}

function deleteFactCheck(index) {
  chrome.storage.local.get({ factChecks: [] }, function (data) {
    let factChecks = data.factChecks;
    factChecks.splice(index, 1); // Remove the item at the specified index
    chrome.storage.local.set({ factChecks: factChecks }, function () {
      loadFactChecks(); // Reload the fact checks after deletion
    });
  });
}

function clearAllHistory() {
  if (confirm('Are you sure you want to clear all fact check history?')) {
    chrome.storage.local.set({ factChecks: [] }, function () {
      loadFactChecks(); // Reload (empty) fact checks after clearing
    });
  }
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
