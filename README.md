# EcoMarket AI Customer Service

AI-powered system for handling customer service queries using Google Gemini. Automatically answers order status and return policy questions.

---

## Project Structure

```
ai-workshop-ecomarket/
├── data/
│   ├── orders.json              # Test order data
│   └── return_policies.json     # Product return policies
├── docs/
│   ├── PHASE1.md               # Model selection justification
│   └── PHASE2.md               # Analysis of strengths, limitations, ethics
├── prompts/
│   ├── order_query_prompt.txt  # Prompt for order status queries
│   └── return_query_prompt.txt # Prompt for return policy queries
├── scripts/
│   ├── order_query.py          # Order status lookup script
│   └── return_query.py         # Return policy lookup script
├── .env                        # Your API key (never commit this!)
├── .env.example                # Template for .env file
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Setup

### Step 1: Create a Virtual Environment

Using a virtual environment keeps your project dependencies isolated from your system Python.

**On macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**On Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

When activated, you'll see `(venv)` at the start of your terminal prompt.

### Step 2: Install Dependencies

With your virtual environment activated:

```bash
pip install -r requirements.txt
```

This installs:
- `google-generativeai>=0.3.0` - Google Gemini API client
- `python-dotenv>=1.0.0` - Loads environment variables from .env file

### Step 3: Get Your Google Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the generated key (starts with `AIza...`)

**Note:** The API is completely free. No credit card required.

### Step 4: Configure Your API Key

You need to create a `.env` file with your API key. There are two ways to do this:

**Option A: Copy from the example file (recommended)**
```bash
cp .env.example .env
```

Then open `.env` in your text editor and replace the placeholder:
```
GOOGLE_API_KEY=your-actual-api-key-here
```
---

## Usage

Make sure your virtual environment is activated before running the scripts:
```bash
# If you see (venv) in your prompt, you're good to go
# If not, activate it:
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate     # Windows
```

### Check Order Status

```bash
cd scripts
python order_query.py
```

**Example interaction:**
```
🌿 ECOMARKET - ORDER STATUS QUERY 🌿
Enter order number (e.g., 12345): 12345

🔍 Searching for your order...

AI RESPONSE:
Hi there! I've located your order #12345. It's currently in transit 
and should arrive by April 20, 2024. You can track it here: 
https://track.ecomarket.com/12345

Your order includes:
- Reusable Water Bottle (Stainless Steel, 750ml)
```

### Check Return Policy

```bash
cd scripts
python return_query.py
```

**Example interaction:**
```
🌿 ECOMARKET - RETURN POLICY QUERY 🌿
Enter product name: Water Bottle

🔍 Checking return policy...

AI RESPONSE:
Good news - the Stainless Steel Water Bottle can be returned!

Return period: 30 days from purchase
Condition: Must be unused and in original packaging

Here's how to return it:
1. Email support@ecomarket.com with your order number
2. We'll send a prepaid shipping label (1-2 business days)
3. Pack the product securely in original packaging
4. Ship it using the label we provide
5. Refund processed within 5-7 days after we receive it
```

---

## How It Works

### Order Query Flow

1. Script reads the prompt template from `prompts/order_query_prompt.txt`
2. Loads order database from `data/orders.json`
3. Injects the data into the prompt (replaces `{orders_database}` and `{order_number}`)
4. Sends complete prompt to Gemini API
5. Returns natural language response

### Return Query Flow

1. Script reads the prompt template from `prompts/return_query_prompt.txt`
2. Loads return policies from `data/return_policies.json`
3. Injects the data into the prompt (replaces `{return_policies_database}` and `{product_name}`)
4. Sends complete prompt to Gemini API
5. Returns natural language response

### Why Separate Prompt Files?

Prompts are stored as separate `.txt` files (not hardcoded in Python) because:
- You can update prompts without touching code
- Version control shows exactly what changed in the prompt
- Easy to A/B test different approaches
- Non-technical team members can improve the prompts

---

## Test Data

### Orders (data/orders.json)

10 sample orders with different statuses:

| Order # | Status | Description |
|---------|--------|-------------|
| 12345 | In transit | Standard order tracking |
| 12346 | Delayed | Tests empathy and apology |
| 12347 | Delivered | Confirmation message |
| 12348 | Cancelled | Refund information |
| 12349 | Processing | Early order stage |
| 12350 | In transit | Alternative scenario |

### Products (data/return_policies.json)

14 products with different return policies:

**Returnable (30 days):**
- Stainless Steel Water Bottle
- Reusable Shopping Bags  
- Solar Phone Charger
- Bamboo Cutlery Set
- Glass Food Containers

**Non-returnable:**
- Bamboo Toothbrush Set (personal hygiene)
- Organic Snack Box (perishable food)
- Reusable Menstrual Cup (intimate product)

---

## Customizing

### Editing Prompts

You can modify the AI's behavior by editing the prompt files:

```bash
nano prompts/order_query_prompt.txt
nano prompts/return_query_prompt.txt
```

Changes take effect immediately - just run the script again. No code changes or restarts needed.

**Prompt placeholders:**
- `{orders_database}` → Gets replaced with JSON order data
- `{order_number}` → Gets replaced with user's input
- `{return_policies_database}` → Gets replaced with JSON policy data
- `{product_name}` → Gets replaced with user's input

### Adding Test Data

Edit the JSON files to add more test cases:
- `data/orders.json` - Add more orders with different statuses
- `data/return_policies.json` - Add more products and policies

---

## Model Configuration

Both scripts automatically detect the best available Gemini model:
- `gemini-2.5-flash` (newest, preferred)
- `gemini-1.5-flash` (fallback)
- `gemini-pro` (older fallback)

**Settings:**
- **Temperature:** 0.7
  - Balances consistency with natural variety
  - High enough to sound human, low enough to stay factual
- **Max Tokens:** 500-600
  - Enough for detailed customer service responses
  - Not so high that responses become verbose

---

## API Rate Limits (Free Tier)

Google Gemini's free tier is generous:
- 60 requests per minute
- 1,500 requests per day  
- 1 million requests per month

This is plenty for testing, academic projects, and small-scale deployments.

---

## Troubleshooting

### Error: "GOOGLE_API_KEY not found in .env file"

**Causes:**
- `.env` file doesn't exist
- `.env` file is empty or incorrectly formatted
- You forgot to add your API key

**Solutions:**
1. Check that `.env` exists: `ls -a` (you should see `.env`)
2. Check the file content: `cat .env`
3. It should look like: `GOOGLE_API_KEY=AIzaSyC_your_actual_key_here`
4. No spaces around the `=` sign
5. Make sure you copied your actual key from Google AI Studio

### Error: "Could not find a compatible Gemini model"

**Solutions:**
1. Verify your API key is correct
2. Check your internet connection
3. Try regenerating your API key at [Google AI Studio](https://makersuite.google.com/app/apikey)

### Virtual Environment Issues

**To deactivate:**
```bash
deactivate
```

**To completely reset:**
```bash
deactivate  # if currently active
rm -rf venv
python3 -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### Module Import Errors

Make sure your virtual environment is activated:
```bash
# You should see (venv) in your prompt
# If not:
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows
```

Then reinstall dependencies:
```bash
pip install -r requirements.txt
```

---

## Documentation

### Phase 1: Model Selection (docs/PHASE1.md)
Why Google Gemini Pro was chosen:
- Cost comparison (free vs $30-450/month for alternatives)
- Quality assessment for customer service use cases
- Setup simplicity and speed
- Scalability considerations

### Phase 2: Critical Analysis (docs/PHASE2.md)
Honest evaluation of the system:
- **What works:** 24/7 availability, consistency, zero marginal cost
- **What doesn't:** Complex emotional situations, long conversations
- **Ethical risks:** Hallucinations, bias, privacy, job displacement, transparency
- Concrete mitigation strategies for each risk

---

## Project Context

This project demonstrates:

1. **Model Selection Methodology**
   - Systematic comparison of available models
   - Cost-benefit analysis
   - Quality vs price tradeoffs

2. **Prompt Engineering**
   - External prompt files (not hardcoded)
   - Handling edge cases (delays, cancellations, not found)
   - Tone control (empathetic vs professional)

3. **Responsible AI**
   - Identifying potential harms
   - Designing concrete mitigations
   - Monitoring strategies

**Goal:** Automate 80% of repetitive queries while escalating complex cases to humans.

---

## When You're Done

Deactivate the virtual environment:
```bash
deactivate
```

Next time you work on the project:
```bash
cd ai-workshop-ecomarket
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate     # Windows
```