# Core imports
from flask import Flask, render_template, request, jsonify, redirect, render_template, session, url_for
from flask_cors import CORS
import requests
from dotenv import load_dotenv, find_dotenv
import traceback
import logging
import json
import os
import database
from config import Config

# Fact-checking imports
import nltk
from nltk.tokenize import sent_tokenize
import openai
from googleapiclient.discovery import build
from duckduckgo_search import DDGS
from datetime import datetime
import httpx
import time
import random
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from pydantic import BaseModel
from typing import Optional
from pandas import DataFrame, notnull
import numpy as np

# LanceDB is used to checking if a sentence has been fact-checked before running the LLM on it & search results.
import lancedb
from lancedb.pydantic import LanceModel, Vector
from lancedb.embeddings import get_registry
from typing import List, Optional
from datetime import date

# Auth0 imports
from os import environ as env
from urllib.parse import quote_plus, urlencode
from authlib.integrations.flask_client import OAuth

# Payment imports
import stripe

# Generate a random API key imports
import string
import secrets

# Core flask app
app = Flask(__name__)
CORS(app)
app.config.from_object(Config) # get config information 
stripe.api_key = app.config["STRIPE_SECRET_KEY"] # Initilize Stripe with your SK


# Initiate Auth0
oauth = OAuth(app)
app.secret_key = env.get("APP_SECRET_KEY")

# Initiate Auth0
oauth.register(
    "auth0",
    client_id=app.config["AUTH0_CLIENT_ID"],
    client_secret=app.config["AUTH0_CLIENT_SECRET"],
    client_kwargs={"scope": "openid profile email"},
    server_metadata_url=f'https://{app.config["AUTH0_DOMAIN"]}/.well-known/openid-configuration'
)

# Set up logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Set the LLM model at OpenAI and load the environment variables for API keys
OPENAI_MODEL = "gpt-4o-mini"
SIMILARITY_THRESHOLD = 0.8


# Set up LanceDB connection and model for sentence embeddings
db = lancedb.connect(os.path.dirname(os.path.abspath(__file__))+"/db")
model = get_registry().get(
    "sentence-transformers").create(name="BAAI/bge-small-en-v1.5", device="cpu")

# Define the FactChecked model for LanceDB
class FactChecked(LanceModel):
    sentence: str = model.SourceField()
    explanation: str
    rating: str
    severity: str
    key_points: List[str]
    source: Optional[str] = None
    check_date: Optional[date] = None
    vector: Vector(model.ndims()) = model.VectorField()

# Function to create or migrate the table
def create_or_migrate_table():
    if "facts_checked" in db.table_names():
        old_table = db.open_table("facts_checked")
        if set(old_table.schema.names): #!= set(FactChecked.model_fields.keys())
            print("Migrating existing table to new schema...")
            db.drop_table("facts_checked")
            return create_new_table()
        else:
            print("Using existing table.")
            return old_table
    else:
        print("Creating new empty table.")
        return create_new_table()

# Function to create a new table
def create_new_table():
    return db.create_table("facts_checked", schema=FactChecked)


def add_fact_if_not_exists(table: lancedb.table.Table, fact):
    # Check if a fact with the same sentence already exists
    print(f"Searching for existing fact: '{fact['sentence']}'")
    existing_facts = table.search(
        fact["sentence"], query_type="vector").limit(1).to_pandas()

    result = existing_facts.iloc[0] if len(existing_facts) > 0 else None

    if result is None:
        # IF there's no similar facts at all, add the fact
        table.add([fact])
        print(f"\nAdded new fact: '{fact['sentence']}'")
    elif result is not None:
        # If there's a similar fact, check the similarity
        # and only add the fact if the similarity is less than 0.8
        similarity = 1 / (1 + fact['_distance'])
        if similarity < SIMILARITY_THRESHOLD:
            table.add([fact])
            print(f"\nAdded new fact: '{fact['sentence']}'")
    else:
        print(f"\nFact already exists: '{fact['sentence']}'")


# Custom JSON encoder for LanceDB objects
class LanceDBJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        elif isinstance(obj, set):
            return list(obj)
        return super().default(obj)

# FactChecker class for fact-checking logic
class FactChecker:
    def __init__(self, table: lancedb.table.Table):
        self.table = table
        self.google_base_url = 'https://factchecktools.googleapis.com/v1alpha1/claims:search'
        self.google_api_key = os.environ.get('GOOGLE_API_KEY')
        openai.api_key = os.environ.get('OPENAI_API_KEY')
        self.custom_search_service = build(
            "customsearch", "v1", developerKey=self.google_api_key)
        self.ddgs = DDGS()
        self.logger = logging.getLogger(__name__)

    def get_fact_checks(self, text):
        params = {
            'key': self.google_api_key,
            'query': text
        }
        response = requests.get(self.google_base_url, params=params)
        return response.json()

    def get_severity(self, rating):
        rating = rating.lower()
        if rating in ['false', 'pants on fire!', 'mostly false']:
            return 'high'
        elif rating in ['half true', 'mixture']:
            return 'medium'
        elif rating in ['mostly true', 'true']:
            return 'low'
        else:
            return 'unknown'

    def _do_fact_check(self, sentence: str, idx: int) -> dict:
        self.logger.debug(
            f"No exact match found. Performing new fact check for: {sentence}")
        fact_checks = self.get_fact_checks(sentence)
        self.logger.debug(f"Received fact checks for sentence {idx}")
        if 'claims' in fact_checks and fact_checks['claims']:
            relevant_claim = self.find_relevant_claim(
                sentence, fact_checks['claims'])
            if relevant_claim:
                rating = relevant_claim.get('claimReview', [{}])[
                    0].get('textualRating', 'Unknown')
                return {
                    'id': idx,
                    'sentence': sentence,
                    'explanation': relevant_claim.get('text', ''),
                    'rating': rating,
                    'severity': self.get_severity(rating)
                }
            else:
                return self.get_custom_search_fact_check(sentence, idx)
        else:
            return self.get_custom_search_fact_check(sentence, idx)

    # Analyzes the text and returns a list of fact-checks
    def analyze_text(self, text):
        sentences = sent_tokenize(text)
        self.logger.debug(f"Tokenized {len(sentences)} sentences")
        results = []
        for i, sentence in enumerate(sentences, 1):
            try:
                self.logger.debug(f"Analyzing sentence {i}: {sentence}")

                # Check LanceDB for existing fact check
                query_results: DataFrame = self.table.search(sentence, query_type="vector").limit(
                    1).to_pandas()

                # If no exact match found, proceed with normal fact-checking
                if query_results.empty:
                    results.append(self._do_fact_check(sentence, i))
                else:
                    fact = query_results.iloc[0]
                    similarity = 1 / (1 + fact['_distance'])
                    if similarity >= SIMILARITY_THRESHOLD:
                        result = {
                            'id': int(i),
                            'sentence': str(fact['sentence']),
                            'explanation': str(fact['explanation']),
                            'rating': str(fact['rating']),
                            'severity': str(fact['severity']),
                            'key_points': fact['key_points'].tolist() if isinstance(fact['key_points'], np.ndarray) else fact['key_points'],
                            'source': str(fact['source']),
                            'check_date': fact['check_date'].isoformat() if notnull(fact['check_date']) else None,
                        }
                        results.append(result)
                        self.logger.debug(
                            f"Retrieved existing fact check for sentence {i}: {sentence}")
                    else:
                        results.append(self._do_fact_check(sentence, i))

            except Exception as e:
                self.logger.error(f"Error analyzing sentence {i}: {str(e)}")
                self.logger.error(traceback.format_exc())
                results.append({
                    'id': i,
                    'sentence': sentence,
                    'explanation': 'Error in fact-checking',
                    'rating': 'Unknown',
                    'severity': 'unknown'
                })
        return results

    def find_relevant_claim(self, sentence, claims):
        for claim in claims:
            if self.is_claim_relevant(sentence, claim['text']):
                return claim
        return None

    def is_claim_relevant(self, sentence, claim_text) -> bool:
        class ClaimRelevanceModel(BaseModel):
            relevance: bool

        prompt = f"""
        Determine if the following claim is relevant to the given sentence.
        Sentence: "{sentence}"
        Claim: "{claim_text}"
        Is this claim directly relevant to the sentence? Respond with only True or False.
        """

        response = openai.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that determines if claims are relevant to given sentences."},
                {"role": "user", "content": prompt}
            ],
            response_format=ClaimRelevanceModel
        )
        return response.choices[0].message.parsed.relevance

    def get_custom_search_results(self, query):
        try:
            res = self.custom_search_service.cse().list(
                q=query, cx=self.google_api_key, num=10).execute()
            return res.get('items', [])
        except Exception as e:
            print(f"Error in custom search: {str(e)}")
            return []

    def search_news(self, keywords: str, region: str = "wt-wt", safesearch: str = "moderate",
                    timelimit: str | None = None, max_results: int | None = None) -> list[dict[str, str]]:
        results = self.ddgs.news(
            keywords=keywords,
            region=region,
            safesearch=safesearch,
            timelimit=timelimit,
            max_results=max_results
        )
        print(f"DuckDuckGo Results: {results}")
        return list(results)  # Convert generator to list

    def get_url_content(self, url, max_retries=5):
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        ]

        for attempt in range(max_retries):
            try:
                headers = {
                    'User-Agent': random.choice(user_agents),
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Referer': 'https://www.google.com/',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                }

                with httpx.Client(timeout=15.0, follow_redirects=True) as client:
                    response = client.get(url, headers=headers)
                    response.raise_for_status()

                    final_url = str(response.url)
                    if urlparse(final_url).path == '/' and urlparse(url).path != '/':
                        print(
                            f"Redirected to main page for URL {url}. Attempting to find content.")
                        return self.extract_relevant_content(response.text, url)

                    content = response.text
                    extracted_content = self.extract_relevant_content(
                        content, url)
                    if not extracted_content:
                        print(
                            f"Failed to extract content from {url}. Using fallback method.")
                        return self.fallback_content_extraction(url)

                    return extracted_content

            except httpx.HTTPStatusError as e:
                print(f"HTTP error {e.response.status_code} for URL {url}")
                if e.response.status_code == 403:
                    print("Access forbidden. Trying with different headers.")
                    headers['Cookie'] = 'accept_cookies=1'
                elif e.response.status_code in [404, 500, 502, 503, 504]:
                    print(f"Server error. Skipping URL.")
                    return None
                else:
                    print(f"Unhandled HTTP error. Skipping URL.")
                    return None
            except Exception as e:
                print(
                    f"An unexpected error occurred while fetching URL {url}: {str(e)}")
                return None

            wait_time = 2 ** attempt + random.uniform(0, 1)
            print(f"Retrying in {wait_time:.2f} seconds...")
            time.sleep(wait_time)

        print(
            f"Failed to fetch content from {url} after {max_retries} attempts")
        return None

    def is_content_valid(self, content):
        soup = BeautifulSoup(content, 'html.parser')
        text_content = soup.get_text(strip=True)
        return len(text_content) > 500  # Adjust this threshold as needed

    def extract_relevant_content(self, html_content, url):
        soup = BeautifulSoup(html_content, 'html.parser')

        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        # Try to find the main content area
        main_content = (
            soup.find('main') or
            soup.find('article') or
            soup.find('div', class_='content') or
            soup.find('div', class_='article-body') or
            soup.find('div', id='article-body')
        )

        if main_content:
            text_content = main_content.get_text(separator='\n', strip=True)
        else:
            # If no main content area found, get all paragraph text
            paragraphs = soup.find_all('p')
            text_content = '\n'.join([p.get_text(strip=True)
                                      for p in paragraphs])

        # If we still don't have much content, fall back to all text
        if len(text_content) < 100:  # Lowered threshold
            text_content = soup.get_text(separator='\n', strip=True)

        if len(text_content) < 100:  # If still not enough content
            return None

        # Return first 5000 characters
        return f"Extracted content from {url}:\n\n{text_content[:5000]}..."

    def fallback_content_extraction(self, url):
        # For MSN video pages
        if 'msn.com' in url and '/video/' in url:
            video_id = url.split('/')[-1]
            api_url = f"https://assets.msn.com/content/view/v2/Detail/en-ie/{video_id}"

            try:
                response = httpx.get(api_url)
                data = response.json()
                title = data.get('title', '')
                description = data.get('description', '')
                return f"Video content from {url}:\n\nTitle: {title}\n\nDescription: {description}"
            except Exception as e:
                print(f"Error fetching video content: {str(e)}")

        # For other MSN pages
        elif 'msn.com' in url:
            try:
                response = httpx.get(url)
                soup = BeautifulSoup(response.text, 'html.parser')
                script_tag = soup.find(
                    'script', {'type': 'application/ld+json'})
                if script_tag:
                    data = json.loads(script_tag.string)
                    if isinstance(data, list):
                        data = data[0]
                    title = data.get('headline', '')
                    description = data.get('description', '')
                    return f"Content from {url}:\n\nTitle: {title}\n\nDescription: {description}"
            except Exception as e:
                print(f"Error fetching MSN content: {str(e)}")

        return f"Unable to extract content from {url}"

    def get_custom_search_fact_check(self, sentence, id):
        search_results = self.get_custom_search_results(sentence)
        news_results = self.search_news(sentence, timelimit="w", max_results=5)

        context = []
        news_context = []

        for result in search_results[:2]:
            content = self.get_url_content(result['link'])
            if content:
                context.append(
                    f"Title: {result['title']}\nContent: {content[:500]}...")
            else:
                context.append(
                    f"Title: {result['title']}\nSnippet: {result.get('snippet', 'No snippet available')}")

        for result in news_results[:2]:
            content = self.get_url_content(result['url'])
            if content:
                news_context.append(
                    f"Title: {result['title']}\nContent: {content[:500]}...")
            else:
                news_context.append(
                    f"Title: {result['title']}\nExcerpt: {result.get('body', 'No excerpt available')[:500]}...")

        context_str = "\n\n".join(context)
        news_context_str = "\n\n".join(news_context)

        class StatementAnalysisModel(BaseModel):
            sentence: str
            explanation: str
            rating: str
            severity: str
            key_points: list[str]

        prompt = f"""
        Analyze the following statement thoroughly:
        "{sentence}"

        Consider the following information from search results and news articles:

        Search Results:
        {context_str}

        Recent News:
        {news_context_str}

        Based on this information and your knowledge, please provide:
        1. A detailed explanation of the fact-check (200-300 words)
        2. Original sentence
        3. A rating on the following scale: True, Mostly True, Half True, Mostly False, False
        4. A severity assessment (high, medium, low) based on the potential impact of this claim if believed
        5. Three key points that summarize your fact-check
        """

        response = openai.beta.chat.completions.parse(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are an expert fact-checker with broad knowledge across various fields including science, history, current events, politics, and culture."},
                {"role": "user", "content": prompt}
            ],
            response_format=StatementAnalysisModel
        )
        fact_check = response.choices[0].message.parsed
        return dict(fact_check)

    def get_rewrite_suggestion(self, sentence, claim_rating):
        prompt = f"""
        Given the following sentence and its fact-check rating, suggest a rewrite that is more accurate:
        Sentence: "{sentence}"
        Fact-check rating: {claim_rating}
        Provide a rewritten version of the sentence that is more accurate based on the fact-check rating.
        """
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that suggests rewrites for statements to make them more accurate."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message['content'].strip()

    def save_fact_check(self, result):
        try:
            # Check if result is a string, and if so, attempt to parse it as JSON
            if isinstance(result, str):
                try:
                    result = json.loads(result)
                except json.JSONDecodeError:
                    logging.error(
                        f"Error: Unable to parse result as JSON: {result}")
                    return False

            # Now proceed with the existing logic, but use .get() with a default value
            new_fact = {
                "sentence": result.get("sentence", ""),
                "explanation": result.get("explanation", ""),
                "rating": result.get("rating", ""),
                "severity": result.get("severity", ""),
                "key_points": result.get("key_points", []),
                "source": result.get("source", ""),
                "check_date": date.today().isoformat()
            }

            # Check if fact already exists before saving
            existing_facts = self.table.search(
                new_fact['sentence'], query_type="vector").limit(1).to_pandas()
            if len(existing_facts) == 0:
                # Add to LanceDB
                added_to_db = add_fact_if_not_exists(self.table, new_fact)

                # Save to JSON file
                try:
                    with open('fact_checks.json', 'r+') as f:
                        try:
                            data = json.load(f)
                            if not isinstance(data, list):
                                data = []
                        except json.JSONDecodeError:
                            data = []
                        data.append(result)
                        f.seek(0)
                        f.truncate()
                        json.dump(data, f, indent=2)
                    logging.info(
                        f"Added new fact check to JSON file: '{result.get('sentence', '')}'")
                except FileNotFoundError:
                    with open('fact_checks.json', 'w') as f:
                        json.dump([result], f, indent=2)
                    logging.info(
                        f"Created new JSON file and added fact check: '{result.get('sentence', '')}'")

                logging.info(
                    f"Added new fact check: '{result.get('sentence', '')}'")
                return added_to_db  # Return whether the fact was added to the database
            else:
                logging.info(
                    f"Fact already exists: '{result.get('sentence', '')}'")
                return False  # Fact wasn't added because it already exists

        except Exception as e:
            logging.error(f"Error saving fact check: {str(e)}")
            return False


# Initialize FactChecker
fact_checker = FactChecker(table=create_or_migrate_table())


@ app.route('/check', methods=['POST'])
def check_text():
    try:
        data = request.json
        if not data or 'text' not in data:
            logging.warning("Invalid input: 'text' field missing")
            return jsonify({'error': 'Invalid input. Please provide a "text" field.'}), 400

        text = data['text']
        if not text or not isinstance(text, str) or not text.strip():
            logging.warning(
                f"Invalid input: 'text' is empty or not a string. Received: {type(text)}")
            return jsonify({'error': 'Invalid input. "text" must be a non-empty string.'}), 400

        # Log first 50 characters of input
        logging.info(f"Analyzing text: {text[:50]}...")
        results = fact_checker.analyze_text(text)

        if not results:
            logging.info("No fact-check results available for the given text.")
            return jsonify({'message': 'No fact-check results available for the given text.'}), 204

        for result in results:
            try:
                fact_checker.save_fact_check(result)
            except Exception as save_error:
                logging.error(
                    f"Error saving fact check: {str(save_error)}\n{result}")

        logging.info(f"Successfully processed {len(results)} fact checks")
        return jsonify(results), 200, {'Content-Type': 'application/json'}

    except Exception as e:
        logging.error(f"Unexpected error in check_text: {str(e)}")
        logging.error(traceback.format_exc())
        return jsonify({'error': 'An unexpected error occurred while processing your request.'}), 500


@ app.route('/suggest', methods=['POST'])
def suggest_rewrite():
    try:
        data = request.json
        sentence = data['sentence']
        claim_rating = data['claim_rating']
        suggestion = fact_checker.get_rewrite_suggestion(
            sentence, claim_rating)
        return jsonify({'suggestion': suggestion})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@ app.route('/search')
def search():
    return render_template('search.html')

@ app.route('/')
def index():
    return render_template('index.html', session=session.get('user'))


@ app.route('/feed')
def feed():
    try:
        with open('fact_checks.json', 'r') as f:
            fact_checks = json.load(f)
        return render_template('feed.html', fact_checks=fact_checks)
    except FileNotFoundError:
        return render_template('feed.html', fact_checks=[])


@ app.route('/info/<int:fact_id>')
def info(fact_id):
    try:
        with open('fact_checks.json', 'r') as f:
            fact_checks = json.load(f)
        fact_check = next(
            (fc for fc in fact_checks if fc['id'] == fact_id), None)
        if fact_check:
            return render_template('info.html', fact_check=fact_check)
        else:
            return "Fact check not found", 404
    except FileNotFoundError:
        return "No fact checks available", 404

# Generate a random API key
def generate_api_key(length=64):
    characters = string.ascii_letters + string.digits
    api_key = ''.join(secrets.choice(characters) for _ in range(length))
    return api_key

# Auth0 login route
@app.route("/login")
def login():
    return oauth.auth0.authorize_redirect(
        redirect_uri=url_for("callback", _external=True)
    )

# Auth0 callback route
@app.route("/callback", methods=["GET", "POST"])
def callback():
    token = oauth.auth0.authorize_access_token()
    session["user"] = token
    
    user_info = token['userinfo']
    
    user = database.get_user_by_email(user_info['name'])
    if not user:
        database.insert_user(user_info['nickname'], user_info['name'], user_info['sub'], generate_api_key())
    else:
        # Update existing user with Auth0 ID if it's not set
        database.update_user_auth0_id(user_info['name'], user_info['sub'])
        # Update existing user with Zapier API Auth Key if not set
        database.update_user_zapier_api_key(generate_api_key(), user_info['sub'])
    
    return redirect("/members")

# Auth0 logout route
@app.route("/logout")
def logout():
    session.clear()
    return redirect(
        "https://" + app.config["AUTH0_DOMAIN"]
        + "/v2/logout?"
        + urlencode(
            {
                "returnTo": url_for("members", _external=True),
                "client_id": app.config["AUTH0_CLIENT_ID"],
            },
            quote_via=quote_plus,
        )
    )

# Stripe Webhook
@app.route('/webhook', methods=['POST'])
def webhook():
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, Config.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        print(f"ValueError: {str(e)}")
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        print(f"SignatureVerificationError: {str(e)}")
        return jsonify({'error': 'Invalid signature'}), 400

    # Handle the event
    if event['type'] == 'customer.subscription.updated' or 'customer.subscription.deleted':
        subscription = event['data']['object']
        customer_id = subscription['customer']
        subscription_id = subscription['id']
        status = subscription['status']
        
        # Retrieve the user by customer_id and update their subscription
        user = database.get_user_by_stripe_customer_id(customer_id)
        if user:
            database.update_user_subscription(user['auth0_user_id'], customer_id, subscription_id, status)
        else:
            print(f"No user found for customer_id: {customer_id}")

    return jsonify({'success': True}), 200

# Stripe Customer Portal
@app.route('/customer-portal', methods=['GET'])
def customer_portal():
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'User not authenticated'}), 401

    auth0_user_id = session['user']['userinfo']['sub']
    user = database.get_user_by_auth0_id(auth0_user_id)

    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 404

    try:
        # Create a Stripe billing portal session
        stripe_session = stripe.billing_portal.Session.create(
            customer=user['stripe_customer_id'],
            return_url=url_for('members', _external=True)
        )

        print('Stripe session created:', stripe_session.url)
        # Return the URL in the JSON response
        return jsonify({'url': stripe_session.url}), 200

    except stripe.error.StripeError as e:
        print(f"Stripe error: {str(e)}")
        return jsonify({'error': 'An error occurred while creating the portal session'}), 500

# Stripe Create Checkout Session
@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    try:
        user_email = session['user']['userinfo']['email']
    except KeyError:
        user_email = None 

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[
                {
                    'price_data': {
                        'currency': 'usd',
                        'unit_amount': 9999,
                        'recurring': {
                            'interval': 'month'
                        },
                        'product_data': {
                            'name': 'Monthly Subscription',
                            'description': 'Access to Sales Call Companion Pro',
                        },
                    },
                    'quantity': 1,
                },
            ],
            mode='subscription',
            success_url=url_for('subscription_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('subscription_cancel', _external=True),
            client_reference_id=session['user']['userinfo']['sub'],
            customer_email=user_email,
        )
        print(f"Checkout session created: {checkout_session.id}")
        return jsonify({
            'id': checkout_session.id,
            'url': checkout_session.url
        }), 200
    except Exception as e:
        return jsonify(error=str(e)), 403

# Stripe Subscription Success
@app.route('/subscription-success')
def subscription_success():
    try:
        session_id = request.args.get('session_id')
        if session_id:
            checkout_session = stripe.checkout.Session.retrieve(session_id)
            customer_id = checkout_session.customer
            subscription_id = checkout_session.subscription
            
            # Retrieve the subscription status
            subscription = stripe.Subscription.retrieve(subscription_id)
            status = subscription.status
            
            auth0_user_id = session['user']['userinfo']['sub']
            
            print(f"Updating subscription for auth0_user_id: {auth0_user_id}")
            print(f"Customer ID: {customer_id}")
            print(f"Subscription ID: {subscription_id}")
            print(f"Status: {status}")
            
            # Update user's subscription status in the database
            database.update_user_subscription(auth0_user_id, customer_id, subscription_id, status)
            
            # Fetch user data from the database
            user = database.get_user_by_email(session['user']['userinfo']['name'])

            if user:
                return render_template('members.html', 
                                       name=user['nickname'], 
                                       has_subscription=True)
            else:
                print(f"User not found for email: {session['user']['userinfo']['name']}")
                return redirect(url_for('home'))
        else:
            print("No session_id provided")
            return redirect(url_for('members'))
    except Exception as e:
        print(f"Error in subscription_success: {str(e)}")
        # Log the full traceback
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'An unexpected error occurred'}), 500

# Stripe Subscription Cancel
@app.route('/subscription-cancel')
def subscription_cancel():
    return render_template('subscription_cancel.html')

if __name__ == '__main__':
    try:
        nltk.download('punkt', quiet=False)
        nltk.download('punkt_tab', quiet=False)

        app.run(debug=True)
    except Exception as e:
        logging.critical(f"Critical error in main app: {str(e)}")
        logging.critical(traceback.format_exc())
