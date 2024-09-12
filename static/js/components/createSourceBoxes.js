async function createSourceBoxes(sources) {
    const container = document.createElement('div');
    container.className = 'fact-check-source-container';

    let urlList = Array.isArray(sources) ? sources : [sources];
    console.log("URLs to process:", urlList);

    for (const url of urlList) {
        try {
            console.log("Fetching metadata for:", url);
            const { title, image } = await fetchFactCheckMetadata(url);
            console.log("Received metadata:", { title, image });
            const box = createFactCheckSourceBox(url, title, image);
            container.appendChild(box);
        } catch (error) {
            console.error('Error creating source box for URL:', url, error);
        }
    }

    return container;
}