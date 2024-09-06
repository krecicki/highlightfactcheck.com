# Core imports
from flask import Flask, render_template, request, jsonify, redirect, render_template, session, url_for
from flask_cors import CORS
import traceback
from fact_checker import FactChecker
from db.facts_db import FactsDB
from config.config import Config
from tools.logger import logger
from db.user_db import UserDB as user_db
import nltk

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


@app.route('/check', methods=['POST'])
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


@app.route('/search')
def search():
    return render_template('search.html')


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

# Auth0 callback route
@app.route("/callback", methods=["GET", "POST"])
def callback():
    token = oauth.auth0.authorize_access_token()
    session["user"] = token
    print(f"Token: {token}")

    user_info = token['userinfo']
    print(f"User Info: {user_info}")
    try:
        user = user_db.get_user_by_email(user_info['name'])
        print(f"User: {user}")
        if not user:
            user_db.insert_user(
                user_info['nickname'], user_info['name'], user_info['sub'], generate_api_key())
        else:
            # Update existing user with Auth0 ID if it's not set
            user_db.update_user_auth0_id(user_info['name'], user_info['sub'])
            # Update existing user with Zapier API Auth Key if not set
            user_db.update_user_zapier_api_key(
                generate_api_key(), user_info['sub'])
    except Exception as e:
        print(f"Error logging in or signing up: {str(e)}")

    return redirect("/search")

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
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'User not authenticated'}), 401

    auth0_user_id = session['user']['userinfo']['sub']
    user = user_db.get_user_by_auth0_id(auth0_user_id)

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
            user = user_db.get_user_by_email(
                session['user']['userinfo']['name'])

            if user:
                return render_template('members.html',
                                       name=user['nickname'],
                                       has_subscription=True)
            else:
                print(
                    f"User not found for email: {session['user']['userinfo']['name']}")
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
        logger.critical(f"Critical error in main app: {str(e)}")
        logger.critical(traceback.format_exc())
