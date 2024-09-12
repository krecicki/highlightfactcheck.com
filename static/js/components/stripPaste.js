document.addEventListener('DOMContentLoaded', function() {
    // Select all input and textarea elements
    const textInputs = document.querySelectorAll('input[type="text"], input[type="email"], input[type="password"], textarea');

    textInputs.forEach(input => {
        input.addEventListener('paste', function(e) {
            // Prevent the default paste behavior
            e.preventDefault();

            // Get the text content from the clipboard
            let text = (e.originalEvent || e).clipboardData.getData('text/plain');

            // Insert the unformatted text at the cursor position
            document.execCommand('insertText', false, text);
        });
    });

    console.log('Paste formatting removal initialized for text inputs');
});