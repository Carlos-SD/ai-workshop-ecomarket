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
├── .env                        # API key configuration
├── .env.example                # API key configuration example  
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Requirements:
- `google-generativeai>=0.3.0`
- `python-dotenv>=1.0.0`

### 2. Get an API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a free API key (no credit card needed)
3. Copy the key

### 3. Configure the API Key

Open `.env` and add your key:

```
GOOGLE_API_KEY=your-actual-api-key-here
```

---

## Usage

### Check Order Status

```bash
cd scripts
python order_query.py
```

Example:
```
Enter order number: 12345

AI Response:
Hi there! I've located your order #12345. It's currently in transit 
and should arrive by April 20, 2024. You can track it here: 
https://track.ecomarket.com/12345
```

### Check Return Policy

```bash
cd scripts
python return_query.py
```

Example:
```
Enter product name: Water Bottle

AI Response:
Good news - the Stainless Steel Water Bottle can be returned within 
30 days if it's unused and in original packaging. Here's how:
1. Email support@ecomarket.com with your order number
2. We'll send a prepaid shipping label (1-2 days)
...
```

---

## How It Works

### Order Query Flow

1. Script reads `prompts/order_query_prompt.txt`
2. Loads order data from `data/orders.json`
3. Replaces prompt placeholders with actual data
4. Sends to Gemini API
5. Returns formatted response

### Return Query Flow

1. Script reads `prompts/return_query_prompt.txt`
2. Loads policies from `data/return_policies.json`
3. Replaces prompt placeholders with actual data
4. Sends to Gemini API
5. Returns formatted response

---

## Test Data

### Orders (data/orders.json)

10 sample orders with different statuses:
- In transit
- Delivered
- Processing
- Delayed
- Cancelled

Test with order numbers: 12345, 12346, 12347, 12348, 12349, 12350

### Products (data/return_policies.json)

14 products with different return policies:
- **Returnable:** Water bottles, reusable bags, solar chargers
- **Non-returnable:** Toothbrushes, food items (hygiene/perishable)

---

## Customizing Prompts

Edit the prompt files directly:
- `prompts/order_query_prompt.txt` - Instructions for order status
- `prompts/return_query_prompt.txt` - Instructions for return policies

Changes take effect immediately (no code changes needed).

---

## Model Configuration

Both scripts auto-detect the best available Gemini model (usually `gemini-2.5-flash` or `gemini-1.5-flash`).

Default settings:
- Temperature: 0.7 (balance between consistency and natural language)
- Max tokens: 500-600 (enough for detailed responses)

---

## Rate Limits (Free Tier)

- 60 requests per minute
- 1,500 requests per day
- 1 million requests per month

This is plenty for testing and small-scale deployment.

---

## Documentation

- **PHASE1.md**: Why Google Gemini Pro was selected (cost, quality, ease of use)
- **PHASE2.md**: What works, what doesn't, and potential ethical issues

---

## Project Context

This was built as a workshop project demonstrating:
1. AI model selection methodology
2. Prompt engineering for customer service
3. Responsible AI deployment practices

The goal: automate 80% of repetitive support queries while escalating complex cases to humans.