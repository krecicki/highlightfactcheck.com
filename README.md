# Twitter-X-Tweet-Lie-Detector

X-Ray Vision for Tweet Truths. The Elon-gated Fact Stretcher Detector.

<img width="728" alt="Screenshot 2024-08-30 at 8 21 08 AM" src="https://github.com/user-attachments/assets/35cb1e00-3dc8-4482-983b-c6e4feffe43d">

# X-Ray Vision for Tweet Truths: The Elon-gated Fact Stretcher Detector

## 🕵️‍♂️ What's This Meme Machine?

This is your personal BS detector for the wild world of social media! It's like having a lie detector test for every tweet, but way more fun and slightly less awkward.

## 🚀 How to Unleash the Truth

Pre-req: Go to [cloud.google.com](cloud.google.com) and in the console enable the Google Custom Search API and the Google Fact Check Tools API. Then, from the [Credentials page](https://console.cloud.google.com/apis/credentials?), create a new API key that's restricted to the two APIs you enabled.

Add the API keys to the `.env.example` file and rename it to `.env.`. Reference: https://developers.google.com/custom-search/docs/tutorial/creatingcse

1. **Clone this bad boy:**

   ```
   git clone https://github.com/yourusername/X-Ray-Vision-for-Tweet-Truths.git
   ```

2. **Slide into the project directory:**
   ```
   cd X-Ray-Vision-for-Tweet-Truths
   ```
3. **Setup a virtual environment and install the truth serum (dependencies):**
   You can install the `virtualenv` tool from [here](https://virtualenv.pypa.io/en/latest/).

   ```
   virtualenv venv && source venv/bin/activate
   ```

   Install the dependencies:

   ```
   pip install -r requirements.txt
   ```

4. **Fire up the truth machine:**

   ```
   python app.py
   ```

5. **Navigate to `http://localhost:5000` in your favorite browser (even if it's Internet Explorer, we won't judge... much).**

6. **Start typing your "facts" into the text box. Watch as our AI Elon-gates its digital muscles to fact-check your wild claims!**

7. **Click on the highlighted text to see just how far you've stretched the truth. It's like a game, but the points are made up and the facts do matter!**

## 🎭 Pro Tips for Maximum Memery

- The more outrageous the claim, the more fun our fact-checker has. It's like giving coffee to a squirrel!
- Try typing "Elon Musk bought Twitter to tweet from Mars." Our AI might just short-circuit from the memetic overload!
- Remember, with great power comes great responsibility... to create top-tier memes based on cold, hard facts.

## 🦸‍♂️ Contribute to the Meme Dream

Found a bug? Want to add more meme-tastic features? Feel free to open an issue or submit a PR. We promise to review it faster than Elon changes his mind about Twitter features!

## 📜 License

This project is licensed under the LOL-WTF-BBQ License. Just kidding, please read the license.

Now go forth and spread truth faster than misinformation spreads on your uncle's Facebook feed!
