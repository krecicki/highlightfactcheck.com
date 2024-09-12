console.log("hide-show-output.js loaded");

function initializeHideShow() {
    console.log("Initializing hide-show functionality");
    
    const outputDiv = document.getElementById("output");
    const submitButton = document.getElementById("submit-button");

    if (outputDiv) {
        console.log("Output div found, hiding it.");
        outputDiv.style.display = "none";
    } else {
        console.error("Output div not found!");
        return;
    }

    if (submitButton) {
        console.log("Submit button found, adding click listener.");
        submitButton.addEventListener("click", function() {
            console.log("Submit button clicked, showing output div.");
            outputDiv.style.display = "block";
        });
    } else {
        console.error("Submit button not found!");
    }
}

// Check if the DOM is already loaded
if (document.readyState === "loading") {
    // If not, add event listener
    document.addEventListener("DOMContentLoaded", initializeHideShow);
} else {
    // If it's already loaded, run the function immediately
    initializeHideShow();
}

console.log("End of hide-show-output.js script reached");