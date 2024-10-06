function cleanPastedText(input) {
    // Step 1: Remove any HTML tags
    let temp = document.createElement("div");
    temp.innerHTML = input;
    let text = temp.textContent || temp.innerText || "";

    // Step 2: Normalize whitespace
    text = text.replace(/\s+/g, " ").trim();

    // Step 3: Remove non-printable and non-ASCII characters
    text = text.replace(/[^\x20-\x7E]/g, "");

    // Step 4: Remove all quotes (single and double)
    text = text.replace(/["']/g, "");

    // Step 5: Remove any remaining invisible characters
    text = text.replace(/[\u200B-\u200D\uFEFF]/g, '');

    return text;
}

async function factCheck() {
    const text = cleanPastedText(document.getElementById('editor').innerText);
    const sentences = text.match(/[^\.!\?]+[\.!\?]+/g) || [text];
    let newSentences = sentences.filter(sentence =>
        !cachedFactChecks.some(check => check?.sentence.trim() === sentence?.trim())
    );

    if (newSentences.length > 0) {
        document.querySelector('.loading').style.display = 'block';
        try {
            const response = await fetch('/check-free', {
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
        } finally {
            document.querySelector('.loading').style.display = 'none';
        }
    }

    // Always update the output, even if no new checks were performed
    updateOutput(text);
}

function updateOutput(text) {
    console.log("Updating output with fact checks:", cachedFactChecks);
    const outputDiv = document.getElementById('output');
    const highlightedText = highlightText(text, cachedFactChecks);
    outputDiv.innerHTML = highlightedText;

    // Add event listeners to highlighted spans
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