// Function to fetch image from Pixabay API
async function fetchPixabayImage(q) {
  const apiKey = '45973915-137b93a1e3cc4b43cbe4286ab';
  const query = q;
  const url = `https://pixabay.com/api/?key=${apiKey}&q=${query}&per_page=1&image_type=photo&safesearch=true&editors_choice=true`;

  try {
    const response = await fetch(url);
    const data = await response.json();

    if (data.hits && data.hits.length > 0) {
      const image = data.hits[0];
      console.log('Image URL:', image.largeImageURL);
      console.log('Image tags:', image.tags);
      console.log('Photographer:', image.user);
      // You can do more with the image data here, like displaying it on your webpage
    } else {
      console.log('No images found');
    }
  } catch (error) {
    console.error('Error fetching image:', error);
  }
}

// Call the function
//fetchPixabayImage('query goes here');