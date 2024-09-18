from PIL import Image
import pytesseract
import re
import tempfile
import os

# Need to use this for meme2text on the server
pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'

class Meme2TxtProcessor:
    @staticmethod
    def extract_text(image_file):
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
            temp_filename = temp_file.name
            # Save the uploaded file to the temporary file
            image_file.save(temp_filename)
        
        try:
            # Open the image
            image = Image.open(temp_filename)
            
            # Extract text
            text = pytesseract.image_to_string(image)
            
            # Process the text
            processed_text = re.sub(r'\s+', ' ', text)  # Replace multiple spaces with single space
            processed_text = processed_text.strip()  # Remove leading/trailing whitespace
            
            # Remove all special characters except R, $, &, ., and ,
            processed_text = re.sub(r'[^a-zA-Z0-9R$&.,\s]', '', processed_text)
            
            # Ensure only one period at the end
            processed_text = processed_text.replace('.', '')  # Remove any existing periods
            processed_text = processed_text.capitalize()  # Capitalize the first letter
            
            # Ensure the text ends with a single period
            if not processed_text.endswith('.'):
                processed_text += '.'
            
            return processed_text
        finally:
            # Clean up the temporary file
            os.unlink(temp_filename)