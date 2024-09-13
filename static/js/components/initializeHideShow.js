console.log("hide-show-output.js loaded");

function initializeHideShow() {
    console.log("Initializing hide-show functionality");
    
    const outputDiv = document.getElementById("output");
    const submitButton = document.getElementById("submit-button");
    const submitButtonMembers = document.getElementById("submit-button-members");
    
    if (!outputDiv) {
        console.error("Output div not found!");
        return;
    }
    
    console.log("Output div found, hiding it.");
    outputDiv.style.display = "none";
    
    const activeButton = submitButton || submitButtonMembers;
    
    if (activeButton) {
        console.log(`${activeButton.id} found, adding click listener.`);
        try {
            activeButton.addEventListener("click", function() {
                console.log(`${activeButton.id} clicked, showing output div.`);
                outputDiv.style.display = "block";
            });
        } catch (error) {
            console.error("Error adding event listener:", error);
        }
    } else {
        console.log("Neither submit button nor submit button members found.");
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