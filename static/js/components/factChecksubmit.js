//document.getElementById('editor').addEventListener('input', debounce(factCheck, 1000));
console.log("factChecksubmit.js loaded");

function initializeFactCheckSubmit() {
    console.log("Initializing fact check submit functionality");
    
    const submitButton = document.getElementById("submit-button");
    const submitButtonMembers = document.getElementById("submit-button-members");
    
    const activeButton = submitButton || submitButtonMembers;
    const activeFunction = submitButton ? factCheck : factCheckmembers;
    
    if (activeButton) {
        console.log(`${activeButton.id} found, adding click listener.`);
        try {
            activeButton.addEventListener('click', function(event) {
                event.preventDefault();
                console.log(`${activeButton.id} clicked, running ${activeFunction.name}.`);
                activeFunction();
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
    document.addEventListener("DOMContentLoaded", initializeFactCheckSubmit);
} else {
    // If it's already loaded, run the function immediately
    initializeFactCheckSubmit();
}

console.log("End of factChecksubmit.js script reached");
//factCheck();