import json
import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Gemini API
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("❌ ERROR: GOOGLE_API_KEY not found in .env file")
    print("Please add your API key to the .env file")
    exit(1)

genai.configure(api_key=api_key)

# Automatically detect the best available model
def get_available_model():
    """Find the first available text generation model"""
    try:
        models = genai.list_models()
        for model in models:
            if 'generateContent' in model.supported_generation_methods:
                model_name = model.name.replace('models/', '')
                return model_name
    except Exception as e:
        print(f"Error detecting models: {e}")
        # Fallback to common model names
        for fallback in ['gemini-1.5-flash-latest', 'gemini-1.5-pro-latest', 'gemini-pro']:
            try:
                test_model = genai.GenerativeModel(fallback)
                test_model.generate_content("test")
                return fallback
            except:
                continue
    return None

# Get the model
model_name = get_available_model()
if not model_name:
    print("❌ ERROR: Could not find a compatible Gemini model")
    print("Please check your API key at: https://makersuite.google.com/app/apikey")
    exit(1)

print(f"✅ Using model: {model_name}")
model = genai.GenerativeModel(model_name)

# Load orders database
def load_orders():
    """Load orders from JSON file"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(os.path.dirname(script_dir), 'data', 'orders.json')
    
    with open(data_path, 'r', encoding='utf-8') as f:
        return json.load(f)

# Load prompt template from file
def load_prompt_template():
    """Load the prompt template from external file"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    prompt_path = os.path.join(os.path.dirname(script_dir), 'prompts', 'order_query_prompt.txt')
    
    with open(prompt_path, 'r', encoding='utf-8') as f:
        return f.read()

def query_order_status(order_number):
    """
    Query the order status using Gemini API
    
    Args:
        order_number: The order number to query
    
    Returns:
        AI-generated response about the order status
    """
    # Load data
    orders = load_orders()
    
    # Convert orders to formatted text for the AI
    db_text = json.dumps(orders, indent=2, ensure_ascii=False)
    
    # Load prompt template from file
    prompt_template = load_prompt_template()
    
    # Replace placeholders in the template
    prompt = prompt_template.format(
        orders_database=db_text,
        order_number=order_number
    )

    try:
        # Call Gemini API
        response = model.generate_content(prompt)
        
        return response.text
    
    except Exception as e:
        return f"Error processing query: {str(e)}"

def main():
    """Main program function"""
    print("=" * 60)
    print("🌿 ECOMARKET - ORDER STATUS QUERY 🌿")
    print("=" * 60)
    print()
    
    # Request order number from user
    order_number = input("Enter order number (e.g., 12345): ").strip()
    
    if not order_number:
        print("❌ Order number cannot be empty")
        return
    
    print()
    print("🔍 Searching for your order...")
    print()
    
    # Query the order status
    response = query_order_status(order_number)
    
    # Display the response
    print("=" * 60)
    print("AI RESPONSE:")
    print("=" * 60)
    print(response)
    print()

if __name__ == "__main__":
    main()