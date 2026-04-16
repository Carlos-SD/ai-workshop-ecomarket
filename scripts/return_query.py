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

# Load return policies database
def load_return_policies():
    """Load return policies from JSON file"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(os.path.dirname(script_dir), 'data', 'return_policies.json')
    
    with open(data_path, 'r', encoding='utf-8') as f:
        return json.load(f)

# Load prompt template from file
def load_prompt_template():
    """Load the prompt template from external file"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    prompt_path = os.path.join(os.path.dirname(script_dir), 'prompts', 'return_query_prompt.txt')
    
    with open(prompt_path, 'r', encoding='utf-8') as f:
        return f.read()

def query_return_policy(product_name):
    """
    Query the return policy for a product using Gemini API
    
    Args:
        product_name: The name of the product to query
    
    Returns:
        AI-generated response about the return policy
    """
    # Load data
    policies = load_return_policies()
    
    # Convert policies to formatted text for the AI
    db_text = json.dumps(policies, indent=2, ensure_ascii=False)
    
    # Load prompt template from file
    prompt_template = load_prompt_template()
    
    # Replace placeholders in the template
    prompt = prompt_template.format(
        return_policies_database=db_text,
        product_name=product_name
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
    print("🌿 ECOMARKET - RETURN POLICY QUERY 🌿")
    print("=" * 60)
    print()
    
    # Request product name from user
    product_name = input("Enter product name (e.g., Water Bottle): ").strip()
    
    if not product_name:
        print("❌ Product name cannot be empty")
        return
    
    print()
    print("🔍 Checking return policy...")
    print()
    
    # Query the return policy
    response = query_return_policy(product_name)
    
    # Display the response
    print("=" * 60)
    print("AI RESPONSE:")
    print("=" * 60)
    print(response)
    print()

if __name__ == "__main__":
    main()