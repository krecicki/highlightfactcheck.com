import openai
from datetime import date
from tools.logger import logger
from dotenv import load_dotenv
import os
from googleapiclient.discovery import build
from duckduckgo_search import DDGS
import requests
# Fact-checking imports
from nltk.tokenize import sent_tokenize
import openai
from googleapiclient.discovery import build
from duckduckgo_search import DDGS
from datetime import datetime
import httpx
import time
import random
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from pydantic import BaseModel
from pandas import DataFrame, notnull
import numpy as np
import traceback
import json
from config.api_config import APIConfig
from db.facts_db import FactsDB
from googlesearch import search

load_dotenv()


class FactChecker:
    def __init__(self, db: FactsDB, logger=logger):
        self.db = db
        self.logger = logger
        self.table = db.table
        self.google_base_url = 'https://factchecktools.googleapis.com/v1alpha1/claims:search'
        self.google_api_key = os.environ.get('GOOGLE_API_KEY')
        openai.api_key = os.environ.get('OPENAI_API_KEY')
        self.custom_search_service = build(
            "customsearch", "v1", developerKey=self.google_api_key)
        self.ddgs = DDGS()

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
                    'severity': self.get_severity(rating),
                    'source': relevant_claim.get('source', '')
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
                    # similarity = 1 / (1 + fact['_distance']) # trying to fix saving to LanceDB/Json
                    # trying to fix saving to LanceDB/Json
                    similarity = 1 / (1 + fact.get('_distance', 0))
                    if similarity >= APIConfig.SIMILARITY_THRESHOLD:
                        result = {
                            'id': int(i),
                            'sentence': str(fact['sentence']),
                            'explanation': str(fact['explanation']),
                            'rating': str(fact['rating']),
                            'severity': str(fact['severity']),
                            'key_points': fact['key_points'].tolist() if isinstance(fact['key_points'], np.ndarray) else fact['key_points'],
                            'source': fact['source'].tolist() if isinstance(fact['source'], np.ndarray) else fact['source'],
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
                    'severity': 'unknown',
                    'source': 'Unknown'
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

    def googlepython_search(self, query, num_results=10, advanced=True):
        """
        Perform a Google search and return the results. Without using Custom Search JSON API.

        :param query: The search query string
        :param num_results: The number of results to return (default: 10)
        :param advanced: Whether to use advanced search (default: True)
        :return: A list of search results
        """
        results = []
        search_generator = search(
            query, num_results=num_results, advanced=advanced)
        print(f"Search Results: {search_generator}")
        for result in search_generator:
            results.append(result)
        print(f"Search Results: {list(results)}")
        return list(results)  # Convert generator to list

    def get_url_content(self, url, max_retries=0):
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
        # search_results = self.get_custom_search_results(sentence)
        gpy_results = self.googlepython_search(sentence)
        news_results = self.search_news(
            sentence, timelimit="w", max_results=10)

        # context = []
        news_context = []
        gpy_context = []
        successful_urls = []

        ''' Process search_results
        for result in search_results[:2]:
            content = self.get_url_content(result['url'])
            if content:
                context.append(
                    f"Title: {result['title']}\nContent: {content[:500]}...")
            else:
                context.append(
                    f"Title: {result['title']}\nSnippet: {result.get('snippet', 'No snippet available')}")'''

        # Process gpy_results
        if isinstance(gpy_results, list):
            for result in gpy_results[:2]:
                try:
                    content = self.get_url_content(result.url)
                    if content:
                        gpy_context.append(
                            f"Title: {result.title}\nContent: {content[:500]}...")
                        print(f"Added URL to successful_urls: {result.url}")
                        successful_urls.append(result.url)
                    else:
                        gpy_context.append(
                            f"Title: {result.title}\nDescription: {result.description}")
                        print(f"Added URL to successful_urls: {result.url}")
                        successful_urls.append(result.url)
                except AttributeError as e:
                    self.logger.error(
                        f"Error processing GPY search result: {str(e)}")
                    continue
        else:
            self.logger.warning(
                "gpy_results is not a list. Skipping GPY results processing.")

        # Process news_results
        for result in news_results[:2]:
            content = self.get_url_content(result['url'])
            if content:
                news_context.append(
                    f"Title: {result['title']}\nContent: {content[:500]}...")
                successful_urls.append(result['url'])
            else:
                news_context.append(
                    f"Title: {result['title']}\nExcerpt: {result.get('body', 'No excerpt available')[:500]}...")
                successful_urls.append(result['url'])
                
        # context_str = "\n\n".join(context + gpy_context)
        context_str = "\n\n".join(gpy_context)
        news_context_str = "\n\n".join(news_context)

        class StatementAnalysisModel(BaseModel):
            sentence: str
            explanation: str
            rating: str
            severity: str
            key_points: list[str]
            source: list[str]

        prompt = f"""
        Analyze the following statement thoroughly:
        "{sentence}"

        Consider the following information from search results and news articles:

        Search Results:
        {context_str}

        Recent News:
        {news_context_str}

        URLs Used for Fact-Check:
        {successful_urls}

        Based on this information and your knowledge, please provide:
        1. A detailed explanation of the fact-check (200-300 words)
        2. Original sentence
        3. A rating on the following scale: True, Mostly True, Half True, Mostly False, False
        4. A severity assessment (high, medium, low) based on the potential impact of this claim if believed
        5. Three key points that summarize your fact-check
        """

        response = openai.beta.chat.completions.parse(
            model=APIConfig.OPENAI_MODEL,
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
            new_fact = {
                "sentence": result.get("sentence", ""),
                "explanation": result.get("explanation", ""),
                "rating": result.get("rating", ""),
                "severity": result.get("severity", ""),
                "key_points": result.get("key_points", []),
                "source": result.get("source", []),
                "check_date": date.today().isoformat()
            }

            added_to_db = self.db.add_fact_if_not_exists(new_fact)
            logger.info(f"Added to DB: {added_to_db}")

            if added_to_db:
                # Save to JSON file
                try:
                    with open('fact_checks.json', 'r+') as f:
                        try:
                            data = json.load(f)
                            if not isinstance(data, list):
                                data = []
                        except json.JSONDecodeError:
                            data = []
                        data.append(new_fact)
                        f.seek(0)
                        f.truncate()
                        json.dump(data, f, indent=2)
                    logger.info(
                        f"Added new fact check to JSON file: '{new_fact['sentence']}'")
                except FileNotFoundError:
                    with open('fact_checks.json', 'w') as f:
                        json.dump([new_fact], f, indent=2)
                    logger.info(
                        f"Created new JSON file and added fact check: '{new_fact['sentence']}'")

            return added_to_db
        except Exception as e:
            logger.error(f"Error saving fact check: {str(e)}")
            raise  # Re-raise the exception after logging
