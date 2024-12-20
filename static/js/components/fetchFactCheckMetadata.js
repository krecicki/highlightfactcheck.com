async function fetchFactCheckMetadata(url) {
    const DEFAULT_IMAGE_PATH = '/static/images/noimg.png'; // Update this path as needed
    //const DEFAULT_IMAGE_PATH = `{{ url_for('static', filename='images/noimg.png') }}`;
    console.log(`Starting fetchFactCheckMetadata for URL: ${url}`);
    try {
        const response = await fetch(`/proxy?url=${encodeURIComponent(url)}`);
        const htmlContent = await response.text();
        console.log("Raw HTML content:", htmlContent);

        const parser = new DOMParser();
        const doc = parser.parseFromString(htmlContent, 'text/html');
        console.log("Parsed document:", doc);

        const title = doc.querySelector('meta[property="og:title"]')?.content;
        const image = doc.querySelector('meta[property="og:image"]')?.content;

        console.log("Extracted metadata:", { title, image });

        if (!title && !image) {
            console.warn('No og:title or og:image found in the parsed document');
        }
        const PIXABAY = fetchPixabayImage(title);
        console.log("PIXABAY:", {PIXABAY});
        return { 
            title: title || new URL(url).hostname, 
            image: image || DEFAULT_IMAGE_PATH
            //image: image || PIXABAY || DEFAULT_IMAGE_PATH
        };
    } catch (error) {
        console.error('Error in fetchFactCheckMetadata:', error);
        return { title: new URL(url).hostname, image: DEFAULT_IMAGE_PATH };
    }
}