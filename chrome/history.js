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
      factChecksContainer.innerHTML = '<p>No fact checks yet.</p>';
      return;
    }

    factChecks.forEach(function (check, index) {
      const checkElement = document.createElement('div');
      checkElement.className = 'fact-check-item';

      const parsedFactCheck = JSON.parse(check.result);
      const ratingColor = getRatingColor(parsedFactCheck.rating);

      checkElement.innerHTML = `
        <p><strong>Sentence:</strong> ${parsedFactCheck.sentence}</p>
        <p><strong>Explanation:</strong> ${
          parsedFactCheck.explanation || 'Not available'
        }</p>
        <p class="rating">
          <strong>Rating:</strong> 
          <span style="color: ${ratingColor};">${parsedFactCheck.rating}</span>
        </p>
        <p class="severity"><strong>Severity:</strong> ${
          parsedFactCheck.severity
        }</p>
        <p class="timestamp">Checked on: ${new Date(
          check.timestamp
        ).toLocaleString()}</p>
        <button class="delete-btn" data-index="${
          factChecks.length - 1 - index
        }">Delete</button>
      `;
      factChecksContainer.appendChild(checkElement);
    });

    // Add event listeners to delete buttons
    document.querySelectorAll('.delete-btn').forEach((button) => {
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
