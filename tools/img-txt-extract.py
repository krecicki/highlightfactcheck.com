from PIL import Image
import pytesseract
import re

class MemeTextExtractor:
    def __init__(self):
        pass

    def process_image(self, image):
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