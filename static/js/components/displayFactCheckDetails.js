function displayFactCheckDetails(factCheck) {
    const detailsDiv = document.getElementById('fact-check-details');
    function generateKeyPointsHTML(keyPoints) {
        if (!Array.isArray(keyPoints)) {
            console.error('Expected an array of key points');
            return '';
        }

        const listItems = keyPoints.map(point => `<li>${point}</li>`).join('');
        return `
        <style>
            .checkmark-list {
                list-style-type: none;
                padding-left: 1.5em;
            }
            .checkmark-list li:before {
                content: '✓';
                display: inline-block;
                color: #4CAF50;
                font-weight: bold;
                margin-left: -1.5em;
                width: 1.5em;
            }
        </style>
    <p><strong>Key Facts:</strong></p>
    <ul class="checkmark-list">
        ${listItems}
    </ul>
        `.trim();
    }

    // Usage
    const keyPointsHTML = generateKeyPointsHTML(factCheck.key_points);

    detailsDiv.innerHTML = `
    <style>
        .fact-check-source-container {
            display: flex;
            flex-wrap: nowrap;
            overflow-x: auto;
            gap: 10px;
            padding: 10px 0;
        }

        .fact-check-source-box {
            flex: 0 0 auto;
            width: 200px;
            border: 1px solid #ddd;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .fact-check-source-image {
            width: 100%;
            height: 120px;
            object-fit: cover;
        }

        .fact-check-source-link {
            display: block;
            padding: 10px;
            text-align: center;
            text-decoration: none;
            color: #333;
            font-size: 14px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        </style>
        <h3>Fact Check Details</h3>
        <p><strong>Sentence:</strong> ${factCheck.sentence}</p>
        <p><strong>Explanation:</strong> ${factCheck.explanation}</p>
        <p><strong>Rating:</strong> ${factCheck.rating}</p>
        <p><strong>Severity:</strong> ${factCheck.severity}</p>
        <!--<p><strong>Key Points:</strong> ${factCheck.key_points}</p>-->
        <!--<p><strong>Source:</strong> ${factCheck.source.join(', ')}</p>-->
        <p>${keyPointsHTML}</p>
        <div id="source-boxes-container"></div>
    `;
    detailsDiv.style.display = 'block';

    // Create and append the source boxes asynchronously
    createSourceBoxes(factCheck.source).then(sourceBoxes => {
        document.getElementById('source-boxes-container').appendChild(sourceBoxes);
    }).catch(error => {
        console.error('Error creating source boxes:', error);
        document.getElementById('source-boxes-container').textContent = 'Unable to load source information.';
    });
}