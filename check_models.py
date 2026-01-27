import os
import google.generativeai as genai
from dotenv import load_dotenv

def list_available_models():
    # 1. Load env vars
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print("Error: GEMINI_API_KEY not found in .env file.")
        return

    # 2. Configure GenAI
    genai.configure(api_key=api_key)

    print(f"Checking models for API key: {api_key[:5]}...{api_key[-4:]}")
    print("-" * 50)

    try:
        # 3. List models
        print("Available Models:")
        found_flash = False
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"- {m.name}")
                if "flash" in m.name:
                    found_flash = True
        
        print("-" * 50)
        if found_flash:
            print("SUCCESS: Found 'flash' models in your list.")
        else:
            print("WARNING: No 'flash' models found. You may need to use 'gemini-pro' or check your API key permissions/location.")
            
    except Exception as e:
        print(f"Error listing models: {e}")

if __name__ == "__main__":
    list_available_models()
