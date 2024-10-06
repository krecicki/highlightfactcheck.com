document.addEventListener('DOMContentLoaded', function() {
    const editor = document.getElementById('editor');
    const maxLength = 256; // Set your desired maximum length here

    editor.addEventListener('input', function() {
        const text = this.innerText;
        if (text.length > maxLength) {
            // Prevent default behavior
            event.preventDefault();
            
            // Truncate text
            this.innerText = text.slice(0, maxLength);
            
            // Move cursor to end
            const range = document.createRange();
            const sel = window.getSelection();
            range.selectNodeContents(this);
            range.collapse(false);
            sel.removeAllRanges();
            sel.addRange(range);
        }
    });
});