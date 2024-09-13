async function factCheckmembers() {
    const text = document.getElementById('editor').innerText;
    const sentences = text.match(/[^\.!\?]+[\.!\?]+/g) || [text];

    let newSentences = sentences.filter(sentence =>
        !cachedFactChecks.some(check => check?.sentence.trim() === sentence?.trim())
    );

    if (newSentences.length > 0) {
        document.querySelector('.loading').style.display = 'block';
        try {
            const response = await fetch('/check', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: newSentences.join(' ') }),
            });

            if (!response.ok) {
            if (response.status === 429) {
                showLimitPopup();
                throw new Error('Rate limit exceeded');
            }
            throw new Error(`HTTP error! status: ${response.status}`);
            }

            const newFactChecks = await response.json();
            newFactChecks.forEach(check => {
            const checkWithId = { ...check, id: nextId++ };
            cachedFactChecks.push(checkWithId);
            });
        } catch (error) {
            console.error('Error during fact check:', error);
            // Uncomment the next line if you want to display the error in the output div
            // document.getElementById('output').innerHTML = `<p>Error during fact check: ${error.message}</p>`;
        } finally {
            document.querySelector('.loading').style.display = 'none';
        }
        }

        function showLimitPopup() {
        const popup = document.createElement('div');
        popup.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background-color: white;
            border: 1px solid #ccc;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            z-index: 1000;
        `;
        popup.innerHTML = `
            <h2>Limit Reached</h2>
            <p>You have reached your fact check limit. Please sign up to perform more fact checks. Visit <a href="/login">the login page click here</a> to sign up.</p>
            <button onclick="this.parentElement.remove()">Close</button>
        `;
        document.body.appendChild(popup);
        }

    const outputDiv = document.getElementById('output');
    outputDiv.innerHTML = highlightText(text, cachedFactChecks);

    document.querySelectorAll('.fact-check').forEach(span => {
        span.addEventListener('mouseover', () => {
            const checkId = span.getAttribute('data-id');
            const factCheck = cachedFactChecks.find(check => check.id == checkId);
            if (factCheck) {
                displayFactCheckDetails(factCheck);
            }
        });
    });
}