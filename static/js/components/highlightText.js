function highlightText(text, factChecks) {
    if (!text || !factChecks || factChecks.length === 0) {
        console.log("No text or fact checks to highlight");
        return text;
    }

    let highlightedText = text;
    const sentences = text.match(/[^\.!\?]+[\.!\?]+/g) || [text];
    
    sentences.forEach((sentence) => {
        const check = factChecks.find(c => c.sentence.trim().toLowerCase() === sentence.trim().toLowerCase());
        if (check) {
            console.log(`Highlighting sentence: ${sentence.trim()}`);
            let color;
            switch (check.severity.toLowerCase()) {
                case 'low': color = 'rgba(46, 204, 113, 0.3)'; break;
                case 'medium': color = 'rgba(241, 196, 15, 0.3)'; break;
                case 'high': color = 'rgba(231, 76, 60, 0.3)'; break;
                default: color = 'rgba(189, 195, 199, 0.3)';
            }

            const escapedSentence = sentence.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            const regex = new RegExp(`(${escapedSentence})`, 'gi');
            highlightedText = highlightedText.replace(regex, `<span style="background-color: ${color};" class="fact-check" data-id="${check.id}">$1</span>`);
        }
    });

    return highlightedText;
}