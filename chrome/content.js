chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'factCheck') {
    chrome.runtime.sendMessage({
      action: 'factCheckAPI',
      text: request.text,
    });
  } else if (request.action === 'displayResults') {
    displayFactCheckResults(request.results);
  }
});

function displayFactCheckResults(results) {
  const resultDiv = document.createElement('div');
  resultDiv.id = 'fact-check-results';
  resultDiv.style.cssText = `
    position: fixed;
    top: 10px;
    right: 10px;
    width: 300px;
    padding: 10px;
    background-color: black;
    border: 1px solid #ccc;
    box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    z-index: 9999;
  `;

  const factCheck = JSON.parse(results[0]);

  resultDiv.innerHTML = `
    <h3>Fact Check Results</h3>
    <p><strong>Sentence:</strong> ${factCheck.sentence}</p>
    <p><strong>Explanation:</strong> ${factCheck.explanation}</p>
    <p><strong>Rating:</strong> ${factCheck.rating}</p>
    <p><strong>Severity:</strong> ${factCheck.severity}</p>
    <button id="close-fact-check">Close</button>
  `;

  document.body.appendChild(resultDiv);

  document.getElementById('close-fact-check').addEventListener('click', () => {
    document.body.removeChild(resultDiv);
  });
}
