# HighlightFactCheck

## Overview

HighlightFactCheck is an advanced AI-powered fact-checking service designed to provide instant, comprehensive analysis of textual content. Our system leverages state-of-the-art language models and multi-source verification to deliver thorough, nuanced fact-checks quickly and efficiently.

### Key Features

- AI-Powered Analysis: Utilizes advanced GPT models for nuanced understanding
- Multi-Source Verification: Checks Google Fact Check Tools, custom web searches, and recent news
- Comprehensive Results: Provides ratings, severity assessments, and detailed explanations
- Continuous Learning: Stores fact-checks for faster future retrievals and improved accuracy
- Rewrite Suggestions: Offers AI-powered suggestions to improve statement accuracy
- Secure Authentication: Utilizes Auth0 for robust user authentication
- Fast Processing: Delivers fact-check results within minutes
- Wide Content Support: Fact-checks articles, social media posts, and more
- Historical Data: Access to previously fact-checked content for quick reference

## Project Structure

```
.
├── app.py                 # Main Flask application
├── fact_checker.py        # Core fact-checking logic
├── db
│   ├── facts_db.py        # Database operations for fact storage
│   └── user_db.py         # User database operations
├── config
│   ├── config.py          # Configuration settings
│   └── api_config.py      # API-specific configuration
├── tools
│   └── logger.py          # Logging utility
├── templates
│   ├── index.html         # Main landing page
│   ├── members.html       # Members area template
│   └── search.html        # Search functionality template
├── static
│   └── images
│       ├── logo-trans.gif # Transparent logo
│       └── chrome-flow.gif # Chrome extension demo
├── requirements.txt       # Project dependencies
└── README.md              # This file
```

## Setup and Installation

1. Clone the repository:
   ```
   git clone https://github.com/your-username/HighlightFactCheck.git
   cd HighlightFactCheck
   ```

2. Create a virtual environment and activate it:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   Create a `.env` file in the root directory and add the following variables:
   ```
   GOOGLE_API_KEY=your_google_api_key
   OPENAI_API_KEY=your_openai_api_key
   AUTH0_CLIENT_ID=your_auth0_client_id
   AUTH0_CLIENT_SECRET=your_auth0_client_secret
   AUTH0_DOMAIN=your_auth0_domain
   APP_SECRET_KEY=your_app_secret_key
   STRIPE_SECRET_KEY=your_stripe_secret_key
   STRIPE_WEBHOOK_SECRET=your_stripe_webhook_secret
   MYSQL_HOST=your_mysql_host
   MYSQL_USER=your_mysql_user
   MYSQL_PASSWORD=your_mysql_password
   MYSQL_DATABASE=your_mysql_database
   MYSQL_PORT=your_mysql_port
   ```

5. Initialize the database:
   ```
   python init_db.py
   ```

6. Run the application:
   ```
   python app.py
   ```

## Core Components

### 1. Flask Application (app.py)

The main Flask application handles routing, user authentication, and integrates all components. Key routes include:

- `/`: Landing page
- `/login`: Auth0 login
- `/callback`: Auth0 callback
- `/members`: Members area
- `/check`: Fact-checking endpoint for paid users
- `/check-free`: Rate-limited fact-checking for free users
- `/webhook`: Stripe webhook for subscription management

### 2. Fact Checker (fact_checker.py)

The core logic for fact-checking, including:

- Sentence tokenization
- Google Fact Check Tools API integration
- Custom web searches
- News article analysis
- AI-powered claim relevance determination
- Comprehensive fact-check generation

### 3. Database Operations

- `facts_db.py`: Manages fact storage using LanceDB
- `user_db.py`: Handles user data and subscription status in MySQL

### 4. Authentication and Payment

- Auth0 integration for secure user authentication
- Stripe integration for subscription management

## API Usage

For internal or future API usage, here's a basic example of how to use the fact-checking endpoint:

```python
import requests

url = "http://localhost:5000/check"
headers = {
    "Content-Type": "application/json",
    "x-user-id": "user_auth0_id"
}
data = {
    "text": "The Earth is flat."
}

response = requests.post(url, json=data, headers=headers)
print(response.json())
```

## TODO List

- [ ] Implement Chrome extension for on-the-fly fact-checking
- [ ] Develop API documentation for potential future public release
- [ ] Enhance multi-language support
- [ ] Implement more robust error handling and logging
- [ ] Optimize database queries for improved performance
- [ ] Add unit tests and integration tests
- [ ] Set up CI/CD pipeline
- [ ] Implement user feedback mechanism for continuous improvement

## Notes for Founders

- The current pricing model is set at $99.99/month for unlimited fact-checks. We may want to consider tiered pricing in the future.
- The `SIMILARITY_THRESHOLD` in `api_config.py` is currently set to 0.95. We might need to adjust this based on user feedback and system performance.
- The fact-checking system currently uses GPT-4. We should monitor token usage and costs, and consider using GPT-3.5-turbo for less complex queries to optimize costs.
- We're currently using LanceDB for fact storage. As we scale, we might need to evaluate other database solutions for improved performance and scalability.
- The Chrome extension is not yet implemented. This should be a priority for the next development sprint.
- We should consider implementing a caching layer to improve response times for frequently checked claims.

Remember to regularly update this README as we develop new features and make significant changes to the system architecture.
