// Used with the subscribe button on the page to subscribe with stripe
const stripe = Stripe('{{ config.STRIPE_PUBLISHABLE_KEY }}');

document.getElementById('subscribe').addEventListener('click', async (e) => {
    e.preventDefault();
    try {
        const response = await fetch('/create-checkout-session', {
            method: 'POST',
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const session = await response.json();
        console.log('Received session:', session); // Log the session object

        if (!session.url) {
            throw new Error('No URL provided in the session object');
        }
        
        // Redirect to the URL provided by Stripe
        window.location.href = session.url;
    } catch (error) {
        console.error('Error:', error);
        alert(`An error occurred: ${error.message}. Please check the console and try again.`);
    }
});