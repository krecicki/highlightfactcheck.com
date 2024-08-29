from flask import Flask, render_template, request, redirect, url_for, jsonify, json
from flask_cors import CORS
import requests
import nltk
from nltk.tokenize import sent_tokenize
import openai
import os
from dotenv import load_dotenv
from googleapiclient.discovery import build
from duckduckgo_search import DDGS

app = Flask(__name__)
CORS(app)

# Use environment variables for API keys
load_dotenv()
google_api_key = os.environ.get('GOOGLE_API_KEY')
openai_api_key = os.environ.get('OPENAI_API_KEY')
google_cse_id = os.environ.get('GOOGLE_CSE_ID')

class FactChecker:
    def __init__(self, google_api_key, openai_api_key, google_cse_id):
        self.google_api_key = google_api_key
        self.google_base_url = 'https://factchecktools.googleapis.com/v1alpha1/claims:search'
        self.openai_api_key = openai_api_key
        self.google_cse_id = google_cse_id
        openai.api_key = self.openai_api_key
        nltk.download('punkt', quiet=True)
        self.custom_search_service = build("customsearch", "v1", developerKey=self.google_api_key)
        self.ddgs = DDGS()

    def get_fact_checks(self, text):
        params = {
            'key': self.google_api_key,
            'query': text
        }
        response = requests.get(self.google_base_url, params=params)
        #print(f"API Response for '{text}': {response.text}")  # Debug print
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

    def analyze_text(self, text):
        sentences = sent_tokenize(text)
        print(f"Sentences: {sentences}")
        results = []
        for i, sentence in enumerate(sentences, 1):
            fact_checks = self.get_fact_checks(sentence)
            print(f"Fact Checks: {fact_checks}")
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
        return results

    def find_relevant_claim(self, sentence, claims):
        for claim in claims:
            if self.is_claim_relevant(sentence, claim['text']):
                return claim
        return None

    def is_claim_relevant(self, sentence, claim_text):
        prompt = f"""
        Determine if the following claim is relevant to the given sentence.
        Sentence: "{sentence}"
        Claim: "{claim_text}"
        Is this claim directly relevant to the sentence? Respond with only 'Yes' or 'No'.
        """
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that determines if claims are relevant to given sentences."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message['content'].strip().lower() == 'yes'

    def get_custom_search_results(self, query):
        try:
            res = self.custom_search_service.cse().list(q=query, cx=self.google_cse_id, num=10).execute()
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

    def get_custom_search_fact_check(self, sentence, id):
        search_results = self.get_custom_search_results(sentence)
        news_results = self.search_news(sentence, timelimit="w", max_results=5)
        #print(search_results)
        if search_results or news_results:
            context = "\n".join([f"Title: {result['title']}\nSnippet: {result['snippet']}" for result in search_results[:5]])
            news_context = "\n".join([f"Title: {result['title']}\nExcerpt: {result['body'][:100]}..." for result in news_results])
            print(context)
            print(news_context)
            prompt = f"""
            The following information is provided from search results and news articles:
            Statement: "{sentence}"

            Search Results:
            {context}

            Recent News:
            {news_context}

            Respond with a JSON object containing:
            1. A brief explanation of what the search results and news articles say about the statement
            2. A rating (True, Mostly True, Half True, Mostly False, False)
            3. A severity (high, medium, low) based on how inaccurate the statement is
            """
        else:
            return self.get_gpt_fact_check(sentence, id)

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that fact-checks statements using provided search results and news articles."},
                {"role": "user", "content": prompt}
            ]
        )
        fact_check = response.choices[0].message['content']
        try:
            fact_check_json = json.loads(fact_check)
            return {
                'id': id,
                'sentence': sentence,
                'claim_text': fact_check_json.get('explanation', ''),
                'claim_rating': fact_check_json.get('rating', 'Unknown'),
                'severity': fact_check_json.get('severity', 'unknown')
            }
        except json.JSONDecodeError:
            return {
                'id': id,
                'sentence': sentence,
                'claim_text': 'Error in fact-checking',
                'claim_rating': 'Unknown',
                'severity': 'unknown'
            }

    def get_gpt_fact_check(self, sentence, id):
        prompt = f"""
        Fact-check the following statement and provide a rating:
        "{sentence}"
        Respond with a JSON object containing:
        1. A brief explanation of the fact-check
        2. A rating (True, Mostly True, Half True, Mostly False, False)
        3. A severity (high, medium, low) based on how inaccurate the statement is
        """
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that fact-checks statements."},
                {"role": "user", "content": prompt}
            ]
        )
        fact_check = response.choices[0].message['content']
        try:
            fact_check_json = json.loads(fact_check)
            return {
                'id': id,
                'sentence': sentence,
                'claim_text': fact_check_json.get('explanation', ''),
                'claim_rating': fact_check_json.get('rating', 'Unknown'),
                'severity': fact_check_json.get('severity', 'unknown')
            }
        except json.JSONDecodeError:
            return {
                'id': id,
                'sentence': sentence,
                'claim_text': 'Error in fact-checking',
                'claim_rating': 'Unknown',
                'severity': 'unknown'
            }

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

fact_checker = FactChecker(google_api_key, openai_api_key, google_cse_id)

@app.route('/check', methods=['POST'])
def check_text():
    try:
        data = request.json
        text = data['text']
        results = fact_checker.analyze_text(text)
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/suggest', methods=['POST'])
def suggest_rewrite():
    try:
        data = request.json
        sentence = data['sentence']
        claim_rating = data['claim_rating']
        suggestion = fact_checker.get_rewrite_suggestion(sentence, claim_rating)
        return jsonify({'suggestion': suggestion})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
