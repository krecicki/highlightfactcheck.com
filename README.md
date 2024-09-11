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

6. Run the application:
   ```
   flask run (from folder containing app.py)
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
- Custom web searches (commented out the call for google cse because of cost)
- News article analysis
- AI-powered claim relevance determination
- Comprehensive fact-check generation

### 3. Database Operations

- `facts_db.py`: Manages fact storage using LanceDB
- `user_db.py`: Handles user data and subscription status in MySQL

### 4. Authentication and Payment

- Auth0 integration for secure user authentication
- Stripe integration for subscription management

## TODO List -  Add them here as you need to.

- [ ] When you load index/search/members the form fires on page load causing a 2024-09-10 20:42:07,004 - WARNING - Invalid input: 'text' is empty or not a string. Received: <class 'str'>
- [ ] Form is submitted in the middle of a person typing and not each time a . ? ! has been entered.
- [ ] .com and similar tld cause the form the split a question up resulting in false answers that are not true.
- [ ] Wheh user hit their limit, the submission is still added to the database and it ends up submitting broken empty data that is later retreived by similarity of future similar questions which stops the actual facts from being saved.

      
- [ ] Develop API documentation for potential future public release
- [ ] Implement user feedback mechanism for continuous improvement
- [ ] Add meme fact checker for image fact checking pipeline. Extract text from pictures, use this as the input. Make a free limited version and unlimited members routes and all them to the html pages.

## Notes for Founders

- The current pricing model is set at $99.99/month for unlimited fact-checks. This can be much less because we ditched google CSE
- The `SIMILARITY_THRESHOLD` in `api_config.py` is currently set to 0.95. We might need to adjust this based on user feedback and system performance.
- The fact-checking system currently uses GPT-4. 
- The Chrome extension is not live to the public yet. This should be a priority for the next development sprint.

