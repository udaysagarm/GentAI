import os
import requests
from langchain.tools import tool
from dotenv import load_dotenv

load_dotenv()

@tool
def get_current_weather(city: str) -> str:
    """
    Fetches the current weather for a specific city using OpenWeatherMap.
    
    Args:
        city: The name of the city (e.g., "New York", "London").
    """
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key or "YOUR_API_KEY" in api_key:
        return "Error: OPENWEATHER_API_KEY not found or invalid in .env file."

    base_url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city,
        "appid": api_key,
        "units": "imperial" # Default to Fahrenheit
    }

    try:
        response = requests.get(base_url, params=params)
        data = response.json()

        if response.status_code == 200:
            temp = data["main"]["temp"]
            desc = data["weather"][0]["description"]
            humidity = data["main"]["humidity"]
            wind_speed = data["wind"]["speed"]
            
            return (f"The current weather in {city} is {desc} with a temperature of {temp:.1f}°F. "
                    f"Humidity is {humidity}% and wind speed is {wind_speed} mph.")
        elif response.status_code == 404:
            return "City not found. Please check the spelling."
        else:
            return f"Error fetching weather: {data.get('message', 'Unknown error')}"

    except Exception as e:
        return f"Error connecting to weather service: {e}"
