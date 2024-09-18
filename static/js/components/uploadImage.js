const imageUpload = document.getElementById('imageUpload');
const resultDiv = document.getElementById('editor');
const uploadButton = document.getElementById('uploadButton');

imageUpload.addEventListener('change', async (event) => {
    const file = event.target.files[0];
    if (file) {
        await uploadImage(file);
    }
});

async function uploadImage(file) {
    const formData = new FormData();
    formData.append('image', file);

    try {
        uploadButton.disabled = true;
        uploadButton.textContent = 'Processing...';
        resultDiv.textContent = 'Extracting text from meme...';

        const response = await axios.post('/meme2txt', formData, {
            headers: {
                'Content-Type': 'multipart/form-data'
            }
        });

        resultDiv.textContent = `${response.data.result}`;
    } catch (error) {
        console.error('Error:', error);
        resultDiv.textContent = `Error: ${error.response?.data?.error || 'An error occurred while processing the image.'}`;
    } finally {
        uploadButton.disabled = false;
        uploadButton.textContent = 'Meme2Text';
        imageUpload.value = ''; // Reset the file input
    }
}