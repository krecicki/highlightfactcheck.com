# Core imports
import secrets
import string
import stripe
from authlib.integrations.flask_client import OAuth
from urllib.parse import quote_plus, urlencode
from os import environ as env
from flask import Flask, render_template, request, jsonify, redirect, render_template, session, url_for, Response, abort
from flask_cors import CORS
import traceback
from tools.fact_checker import FactChecker
from db.facts_db import FactsDB
from config.config import Config
from tools.logger import logger
from db.user_db import UserDB
from tools.meme2txt_processor import Meme2TxtProcessor
import nltk
import requests
# used only allowing routes to be access by active subscription users
from functools import wraps
from slugify import slugify

# Rate limiting imports
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Initilize user_db
user_db = UserDB()

# Core flask app
app = Flask(__name__, static_folder='static', static_url_path='/static')
CORS(app)
app.config.from_object(Config)  # get config information
# Initilize Stripe with your SK
stripe.api_key = app.config["STRIPE_SECRET_KEY"]


# Initiate Auth0
oauth = OAuth(app)
app.secret_key = app.config["APP_SECRET_KEY"]

# Initiate Auth0
oauth.register(
    "auth0",
    client_id=app.config["AUTH0_CLIENT_ID"],
    client_secret=app.config["AUTH0_CLIENT_SECRET"],
    client_kwargs={"scope": "openid profile email"},
    server_metadata_url=f'https://{app.config["AUTH0_DOMAIN"]}/.well-known/openid-configuration'
)

# Initialize FactChecker
facts_db = FactsDB(db_uri="./localdb")
fact_checker = FactChecker(db=facts_db)

# Initialize the limiter for free users, does not apply to paid users
limiter = Limiter(
    key_func=get_remote_address,
    app=app
)

# Decorator to check if the user has an active subscription to access certain routes


def require_active_subscription(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # We have to check that at least one of the following is present:
        # 1. user in the session (ie. user logged-in and is using the app through the website
        # 2. x-api-key in the request headers (ie. user is using the app through the API or Chrome)
        # If netiher is present, we return an error

        # If we don't have any user in the session and no x-api-key in the request headers, we return an error
        if 'user' not in session and 'x-api-key' not in request.headers:
            return jsonify({'error': 'Authentication required'}), 401

        # Session takes precedence over x-api-key, so let's check that one first
        if 'user' in session:
            logger.debug(f"Checking session")
            auth0_user_id = session['user']['userinfo']['sub']
            user = user_db.get_user_by_auth0_id(auth0_user_id)

            if not user or user.get('subscription_status') != 'active':
                return jsonify({'error': 'Active subscription required'}), 403
        elif 'x-api-key' in request.headers:
            api_key = request.headers.get('x-api-key')
            logger.debug(f"Checking API key")
            user = user_db.get_user_by_api_key(api_key)

            if not user or user.get('subscription_status') != 'active':
                return jsonify({'error': 'Active subscription required'}), 403

        return f(*args, **kwargs)
    return decorated_function

# Route for paid users to check text


@app.route('/check', methods=['POST'])
@require_active_subscription
@limiter.limit("5 per minute;150 day")
def check_text():
    try:
        data = request.json
        if not data or 'text' not in data:
            logger.warning("Invalid input: 'text' field missing")
            return jsonify({'error': 'Invalid input. Please provide a "text" field.'}), 400

        text = data['text']
        if not text or not isinstance(text, str) or not text.strip():
            logger.warning(
                f"Invalid input: 'text' is empty or not a string. Received: {type(text)}")
            return jsonify({'error': 'Invalid input. "text" must be a non-empty string.'}), 400

        # Log first 50 characters of input
        logger.info(f"Analyzing text: {text[:50]}...")
        results = fact_checker.analyze_text(text)

        if not results:
            logger.info("No fact-check results available for the given text.")
            return jsonify({'message': 'No fact-check results available for the given text.'}), 204

        for result in results:
            try:
                fact_checker.save_fact_check(result)
            except Exception as save_error:
                logger.error(
                    f"Error saving fact check: {str(save_error)}\n{result}")

        logger.info(f"Successfully processed {len(results)} fact checks")
        return jsonify(results), 200, {'Content-Type': 'application/json'}

    except Exception as e:
        logger.error(f"Unexpected error in check_text: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': 'An unexpected error occurred while processing your request.'}), 500

# Route for free users to check text has a limit of 3 per day and 1 per hour

@app.route('/check-free', methods=['POST'])
@limiter.limit("5 per minute;15 per day")
def check_text_free():
    try:
        data = request.json
        if not data or 'text' not in data:
            logger.warning("Invalid input: 'text' field missing")
            return jsonify({'error': 'Invalid input. Please provide a "text" field.'}), 400

        text = data['text']
        if not text or not isinstance(text, str) or not text.strip():
            logger.warning(
                f"Invalid input: 'text' is empty or not a string. Received: {type(text)}")
            return jsonify({'error': 'Invalid input. "text" must be a non-empty string.'}), 400

        # Log first 50 characters of input
        logger.info(f"Analyzing text: {text[:50]}...")
        results = fact_checker.analyze_text(text)

        if not results:
            logger.info("No fact-check results available for the given text.")
            return jsonify({'message': 'No fact-check results available for the given text.'}), 204

        for result in results:
            try:
                fact_checker.save_fact_check(result)
            except Exception as save_error:
                logger.error(
                    f"Error saving fact check: {str(save_error)}\n{result}")

        logger.info(f"Successfully processed {len(results)} fact checks")
        return jsonify(results), 200, {'Content-Type': 'application/json'}

    except Exception as e:
        logger.error(f"Unexpected error in check_text: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': 'An unexpected error occurred while processing your request.'}), 500

# Used for rate limiting for free users in the route /check-free


@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify(error="Rate limit exceeded. You can make 3 requests per day, with a maximum of 1 per hour. Please try again later."), 429


@app.route('/')
def index():
    return render_template('index.html', session=session.get('user'))

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

# Successful logged in users can visit the members page with the call page


@app.route('/members')
def members():
    try:
        auth0_user_id = session['user']['userinfo']['sub']
        user = user_db.get_user_by_auth0_id(auth0_user_id)
    except KeyError:
        return redirect("login")
    except Exception as e:
        # Log the exception (optional)
        print(f"Error retrieving user: {e}")
        return redirect("login")

    has_subscription = user and user.get('subscription_status') == 'active'
    api_key = user.get('api_key') if user else None

    return render_template('members.html', has_subscription=has_subscription, api_key=api_key)


# Auth0 Callback after successful login, signup or failure


@app.route("/callback", methods=["GET", "POST"])
def callback():
    token = oauth.auth0.authorize_access_token()
    session["user"] = token

    user_info = token['userinfo']

    user = user_db.get_user_by_email(user_info['name'])
    if not user:
        user_db.insert_user(
            user_info['nickname'], user_info['name'], user_info['sub'], generate_api_key())
    else:
        # Update existing user with Auth0 ID if it's not set
        user_db.update_user_auth0_id(user_info['name'], user_info['sub'])
        # Update existing user with Zapier API Auth Key if not set
        user_db.update_user_zapier_api_key(
            generate_api_key(), user_info['sub'])

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
        user = user_db.get_user_by_stripe_customer_id(customer_id)
        if user:
            user_db.update_user_subscription(
                user['auth0_user_id'], customer_id, subscription_id, status)
        else:
            print(f"No user found for customer_id: {customer_id}")

    return jsonify({'success': True}), 200

# Stripe Customer Portal

@app.route('/customer-portal', methods=['GET'])
def customer_portal():
    print("Customer portal route accessed")
    if 'user' not in session:
        print("User not in session")
        return jsonify({'success': False, 'error': 'User not authenticated'}), 401
    
    auth0_user_id = session['user']['userinfo']['sub']
    print(f"Auth0 user ID: {auth0_user_id}")
    
    user = user_db.get_user_by_auth0_id(auth0_user_id)
    if not user:
        print("User not found in database")
        return jsonify({'success': False, 'error': 'User not found'}), 404
    
    print(f"User found: {user}")
    
    try:
        stripe_session = stripe.billing_portal.Session.create(
            customer=user['stripe_customer_id'],
            return_url=url_for('members', _external=True)
        )
        print(f'Stripe session created: {stripe_session.url}')
        print(f'Redirecting to: {stripe_session.url}')
        return redirect(stripe_session.url)
    except stripe.error.StripeError as e:
        print(f"Stripe error: {str(e)}")
        return jsonify({'success': False, 'error': 'An error occurred while creating the portal session'}), 500

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
                        'unit_amount': 1999,
                        'recurring': {
                            'interval': 'month'
                        },
                        'product_data': {
                            'name': 'Monthly Subscription',
                            'description': 'Access to FactCheckPro Plan (w/ API Key Included)',
                        },
                    },
                    'quantity': 1,
                },
            ],
            mode='subscription',
            success_url=url_for(
                'subscription_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
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
            user_db.update_user_subscription(
                auth0_user_id, customer_id, subscription_id, status)

            # Fetch user data from the database
            user = user_db.get_user_by_auth0_id(auth0_user_id)

            if user:
                return render_template('members.html',
                                       has_subscription=True)
            else:
                print(
                    f"User not found for: {session['user']['userinfo']['sub']}")
                return redirect(url_for('login'))
        else:
            print("No session_id provided")
            return redirect(url_for('login'))
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

# Used for client-side CORS proxy route for fetching metadata from other domains using Open Graph Protocol
@app.route('/proxy', methods=['GET'])
def proxy():
    url = request.args.get('url')
    if not url:
        return 'No URL provided', 400

    try:
        response = requests.get(url)
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for (name, value) in response.raw.headers.items()
                   if name.lower() not in excluded_headers]
        print("meow: ", response.content, headers)
        return Response(response.content, response.status_code, headers)
    except requests.RequestException as e:
        return str(e), 500

# Initialize FactsDB for Blog Routes Below
# Initialize FactsDB
db_uri = "localdb"
facts_db = FactsDB(db_uri)

def generate_slug(sentence):
    return slugify(sentence)

def prepare_fact(fact):
    if 'vector' in fact:
        del fact['vector']
    fact['slug'] = generate_slug(fact['sentence'])
    return fact

@app.route('/blog')
def blog():
    page = int(request.args.get('page', 1))
    per_page = 10
    all_facts = facts_db.get_all_facts()
    start = (page - 1) * per_page
    end = start + per_page
    
    facts_page = [prepare_fact(fact) for fact in all_facts[start:end]]
    
    total_pages = (len(all_facts) - 1) // per_page + 1
    
    return render_template('blog.html', 
                           facts=facts_page, 
                           total_facts=len(all_facts),
                           current_page=page,
                           total_pages=total_pages)

@app.route('/api/facts')
def get_facts():
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    all_facts = facts_db.get_all_facts()
    start = (page - 1) * per_page
    end = start + per_page
    
    facts_page = [prepare_fact(fact) for fact in all_facts[start:end]]
    
    return jsonify({
        'facts': facts_page,
        'has_more': end < len(all_facts)
    })

@app.route('/search')
def search_facts():
    query = request.args.get('query', '')
    limit = int(request.args.get('limit', 10))
    results = facts_db.search_facts(query, limit)
    
    prepared_results = [prepare_fact(fact) for fact in results]
    
    return render_template('blog.html', 
                           facts=prepared_results, 
                           search_query=query, 
                           total_facts=len(results),
                           current_page=1,
                           total_pages=1)

@app.route('/article/<string:slug>')
def article(slug):
    all_facts = facts_db.get_all_facts()
    fact = next((prepare_fact(f) for f in all_facts if generate_slug(f['sentence']) == slug), None)
    if fact is None:
        abort(404)
    return render_template('article.html', fact=fact)

# Used for meme2txt_processor
@app.route('/meme2txt', methods=['POST'])
def meme2txt():
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400
    
    image_file = request.files['image']
    
    if image_file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if image_file:
        try:
            result = Meme2TxtProcessor.extract_text(image_file)
            return jsonify({'result': result})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        
        
        
if __name__ == '__main__':
    try:
        nltk.download('punkt', quiet=False)
        nltk.download('punkt_tab', quiet=False)

        app.run(debug=True)
    except Exception as e:
        logger.critical(f"Critical error in main app: {str(e)}")
        logger.critical(traceback.format_exc())
