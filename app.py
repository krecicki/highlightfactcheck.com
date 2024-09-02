from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import requests
import nltk
from nltk.tokenize import sent_tokenize
import openai
import os
from dotenv import load_dotenv
from googleapiclient.discovery import build
from duckduckgo_search import DDGS
import json
from datetime import datetime
import httpx
import time
import random
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import traceback
import logging
from pydantic import BaseModel
from typing import Optional

# LanceDB is used to checking if a sentence has been fact-checked before running the LLM on it & search results.
import lancedb
from lancedb.pydantic import LanceModel, Vector
from lancedb.embeddings import get_registry
import os
from typing import List, Optional
from datetime import date

app = Flask(__name__)
CORS(app)

# Set up logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Set the LLM model at OpenAI and load the environment variables for API keys
OPENAI_MODEL = "gpt-4o-mini"
load_dotenv()

# Set up LanceDB connection and model for sentence embeddings
db = lancedb.connect(os.path.dirname(os.path.abspath(__file__))+"/db")
model = get_registry().get("sentence-transformers").create(name="BAAI/bge-small-en-v1.5", device="cpu")

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
        if set(old_table.schema.names) != set(FactChecked.model_fields.keys()):
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

def add_fact_if_not_exists(table, fact):
    # Check if a fact with the same sentence already exists
    existing_facts = table.search(fact["sentence"]).limit(1).to_pandas()
    if len(existing_facts) == 0:
        table.add([fact])
        print(f"\nAdded new fact: '{fact['sentence']}'")
    else:
        print(f"\nFact already exists: '{fact['sentence']}'")

# Create or migrate the table
table = create_or_migrate_table()

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
    def __init__(self):
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

    # Analyzes the text and returns a list of fact-checks
    def analyze_text(self, text):
        sentences = sent_tokenize(text)
        self.logger.debug(f"Tokenized {len(sentences)} sentences")
        results = []
        for i, sentence in enumerate(sentences, 1):
            try:
                self.logger.debug(f"Analyzing sentence {i}: {sentence}")
                
                # Check LanceDB for existing fact check
                query_results = table.search(sentence).limit(1).to_pydantic(FactChecked)
                
                if query_results and query_results[0].sentence == sentence:  # Ensure exact match
                    fact = query_results[0]
                    result = {
                        'id': i,
                        'sentence': fact.sentence,
                        'explanation': fact.explanation,
                        'claim_rating': fact.rating,
                        'severity': fact.severity,
                        'key_points': fact.key_points,
                        'source': fact.source,
                        'check_date': fact.check_date.isoformat() if fact.check_date else None
                    }
                    results.append(result)
                    self.logger.debug(f"Retrieved existing fact check for sentence {i}: {sentence}")
                else:
                    # If not in LanceDB or no exact match, proceed with normal fact-checking
                    self.logger.debug(f"No exact match found. Performing new fact check for: {sentence}")
                    fact_checks = self.get_fact_checks(sentence)
                    self.logger.debug(f"Received fact checks for sentence {i}")
                    if 'claims' in fact_checks and fact_checks['claims']:
                        relevant_claim = self.find_relevant_claim(sentence, fact_checks['claims'])
                        if relevant_claim:
                            rating = relevant_claim.get('claimReview', [{}])[0].get('textualRating', 'Unknown')
                            results.append({
                                'id': i,
                                'sentence': sentence,
                                'claim_text': relevant_claim.get('text', ''),
                                'claim_rating': rating,
                                'severity': self.get_severity(rating)
                            })
                        else:
                            results.append(self.get_custom_search_fact_check(sentence, i))
                    else:
                        results.append(self.get_custom_search_fact_check(sentence, i))
            except Exception as e:
                self.logger.error(f"Error analyzing sentence {i}: {str(e)}")
                self.logger.error(traceback.format_exc())
                results.append({
                    'id': i,
                    'sentence': sentence,
                    'claim_text': 'Error in fact-checking',
                    'claim_rating': 'Unknown',
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
                q=query, cx=self.google_cse_id, num=10).execute()
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
        return fact_check.json()

    def get_gpt_fact_check(self, sentence, id):
        class FactCheckModel(BaseModel):
            id: int
            timestamp: Optional[datetime] = datetime.now()
            sentence: str
            claim_text: str
            claim_rating: str
            severity: str

        prompt = f"""
        Fact-check the following statement and provide a rating:
        "{sentence}"
        Respond with a JSON object containing:
        1. Original sentence (sentence field)
        2. A brief explanation of the fact-check (claim_text field)
        3. A rating (True, Mostly True, Half True, Mostly False, False) (claim_rating field)
        4. A severity (high, medium, low) based on how inaccurate the statement is (severity field)
        """
        response = openai.beta.chat.completions.parse(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that fact-checks statements."},
                {"role": "user", "content": prompt}
            ],
            response_format=FactCheckModel
        )
        fact_check = response.choices[0].message.parsed
        return fact_check.json()

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
                    logging.error(f"Error: Unable to parse result as JSON: {result}")
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
            existing_facts = table.search(new_fact['sentence']).limit(1).to_pandas()
            if len(existing_facts) == 0:
                # Add to LanceDB
                added_to_db = add_fact_if_not_exists(table, new_fact)

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
                    logging.info(f"Added new fact check to JSON file: '{result.get('sentence', '')}'")
                except FileNotFoundError:
                    with open('fact_checks.json', 'w') as f:
                        json.dump([result], f, indent=2)
                    logging.info(f"Created new JSON file and added fact check: '{result.get('sentence', '')}'")

                logging.info(f"Added new fact check: '{result.get('sentence', '')}'")
                return added_to_db  # Return whether the fact was added to the database
            else:
                logging.info(f"Fact already exists: '{result.get('sentence', '')}'")
                return False  # Fact wasn't added because it already exists

        except Exception as e:
            logging.error(f"Error saving fact check: {str(e)}")
            return False

# Initialize FactChecker
fact_checker = FactChecker()

@app.route('/check', methods=['POST'])
def check_text():
    try:
        data = request.json
        if not data or 'text' not in data:
            logging.warning("Invalid input: 'text' field missing")
            return jsonify({'error': 'Invalid input. Please provide a "text" field.'}), 400

        text = data['text']
        if not text or not isinstance(text, str) or not text.strip():
            logging.warning(f"Invalid input: 'text' is empty or not a string. Received: {type(text)}")
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
                logging.error(f"Error saving fact check: {str(save_error)}\n{result}")

        logging.info(f"Successfully processed {len(results)} fact checks")
        
        # Ensure results are properly serialized
        serialized_results = json.dumps(results, cls=LanceDBJSONEncoder)
        logging.debug(f"Serialized results: {serialized_results}")  # Log the serialized results
        
        return serialized_results, 200, {'Content-Type': 'application/json'}

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


@ app.route('/')
def index():
    return render_template('index.html')


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


if __name__ == '__main__':
    try:
        nltk.download('punkt', quiet=False)
        nltk.download('punkt_tab', quiet=False)

        app.run(debug=True)
    except Exception as e:
        logging.critical(f"Critical error in main app: {str(e)}")
        logging.critical(traceback.format_exc())