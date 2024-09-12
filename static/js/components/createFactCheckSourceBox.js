function createFactCheckSourceBox(url, title, image) {
    const box = document.createElement('div');
    box.className = 'fact-check-source-box';
    box.innerHTML = `
        <img src="${image}" alt="${title}" class="fact-check-source-image">
        <a href="${url}" target="_blank" rel="noopener noreferrer" class="fact-check-source-link">${title}</a>
    `;
    return box;
}