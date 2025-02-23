from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import os
import requests
import logging
from dotenv import load_dotenv

load_dotenv()

# Retrieve API credentials from .env
AMADEUS_API_KEY = os.getenv('AMADEUS_API_KEY')
AMADEUS_API_SECRET = os.getenv('AMADEUS_API_SECRET')
TOKEN_URL = "https://test.api.amadeus.com/v1/security/oauth2/token"
FLIGHT_SEARCH_URL = "https://test.api.amadeus.com/v2/shopping/flight-offers"
HOTEL_SEARCH_URL = "https://test.api.amadeus.com/v1/reference-data/locations/hotels/by-city"

app = FastAPI()

app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

def get_access_token():
	"""Retrieve OAuth access token from Amadeus API."""
	try:
		response = requests.post(
			TOKEN_URL,
			headers={"Content-Type": "application/x-www-form-urlencoded"},
			data={
		    		"grant_type": "client_credentials",
		    		"client_id": AMADEUS_API_KEY,
		    		"client_secret": AMADEUS_API_SECRET
			}
		)
		response.raise_for_status()
		return response.json().get("access_token")
	except requests.RequestException as e:
		logging.error(f"Error fetching access token: {e}")
		raise HTTPException(status_code=500, detail="Failed to retrieve access token")
	

@app.get("/search")
def search_travel(
	origin: str = Query(..., min_length=3, max_length=3, description="3-letter IATA airport code in CAPS"),
	destination: str = Query(..., min_length=3, max_length=3, description="3-letter IATA airport code in CAPS"),
	travel_date: str = Query(..., regex=r"\d{4}-\d{2}-\d{2}", description="Travel date in YYYY-MM-DD format")
):
	"""Fetch flight details using Amadeus"""
	if not AMADEUS_API_KEY or not AMADEUS_API_SECRET:
		raise HTTPException(status_code=500, detail="Amadeus API credentials are missing. Please set them as environment variables.")

	access_token = get_access_token()
	headers = {"Authorization": f"Bearer {access_token}"}

	try:
		"""Fetch flight details"""
		flight_params = {
			"originLocationCode":origin, 
			"destinationLocationCode": destination, 
			"departureDate": travel_date, 
			"adults": 1
		}

		flight_response = requests.get(FLIGHT_SEARCH_URL, headers=headers, params=flight_params)
		flight_response.raise_for_status()
		flights = flight_response.json()
	except requests.RequestException as e:
		logging.error(f"Error fetching flight details: {e}")
		raise HTTPException(status_code=500, detail="Failed to fetch flight data")

	try:
		"""Fetch hotel details"""
		hotel_params = {
			"cityCode": destination
		}
 
		hotel_response = requests.get(HOTEL_SEARCH_URL, headers=headers, params=hotel_params)
		hotel_response.raise_for_status()
		hotels = hotel_response.json()
	except requests.RequestException as e:
		logging.error(f"Error fetching hotel data: {e}")
		raise HTTPException(status_code=500, detail="Failed to fetch hotel data")
	
	return {"flights": flights, "hotels": hotels}

@app.get("/health")
def health_check():
	return {"status": "ok"}

@app.get("/integration.json")
def get_integration_json():
    """Serve the integration.json file for Telex integration."""
    integration_data = {
        "data": {
            "date": {
                "created_at": "2025-02-22",
                "updated_at": "2025-02-22"
            },
            "descriptions": {
                "app_description": "This integration fetches flight and hotel information for a given destination and posts updates in a Telex channel.",
                "app_logo": "https://iili.io/GWj9u1.jpg",
                "app_name": "Travel Buddy",
                "app_url": "https://hng12-stage3-travelbuddy.onrender.com",
                "background_color": "#3498db"
            },
            "integration_category": "CRM & Customer Support",
            "integration_type": "interval",
            "is_active": True,
            "output": [
                {"label": "output_channel_1", "value": True},
                {"label": "output_channel_2", "value": False}
            ],
            "key_features": [
                "Fetches real-time flight offers.",
                "Retrieves available hotel deals.",
                "Automatically posts updates to a Telex channel.",
                "Runs on a set interval."
            ],
            "permissions": {
                "monitoring_user": {
                    "always_online": True,
                    "display_name": "Travel Monitor Bot"
                }
            },
            "settings": [
                {
                    "label": "interval",
                    "type": "text",
                    "required": True,
                    "default": "0 * * * *"  # Runs every hour
                },
                {
                    "label": "Origin Airport (IATA Code)",
                    "type": "text",
                    "required": True,
                    "default": "JFK"
                },
                {
                    "label": "Destination Airport (IATA Code)",
                    "type": "text",
                    "required": True,
                    "default": "LHR"
                },
                {
                    "label": "Travel Date (YYYY-MM-DD)",
                    "type": "text",
                    "required": True,
                    "default": "2025-03-01"
                },
                {
                    "label": "Enable Notifications",
                    "type": "checkbox",
                    "required": True,
                    "default": "Yes"
                },
            "tick_url" == "https://hng12-stage3-travelbuddy.onrender.com/trigger",
            "target_url" == "https://hng12-stage3-travelbuddy.onrender.com/search"
	    ]
	}
    }
    return JSONResponse(content=integration_data)

@app.post("/trigger")
async def trigger_integration(request: Request):
    """Telex calls this endpoint at set intervals, sending user settings."""
    try:
        payload = await request.json()
        settings = payload.get("settings", {})

        # Extract user-configured values
        origin = settings.get("Origin Airport (IATA Code)", "JFK")
        destination = settings.get("Destination Airport (IATA Code)", "LHR")
        travel_date = settings.get("Travel Date (YYYY-MM-DD)", "2025-03-01")

        # Log received data
        logging.info(f"Triggered with: {origin} → {destination} on {travel_date}")

        # Call the search endpoint with user settings
        search_url = f"{request.base_url}search"
        search_params = {
            "origin": origin,
            "destination": destination,
            "travel_date": travel_date
        }
        search_response = requests.get(search_url, params=search_params)
        search_response.raise_for_status()

        # Return the search results to Telex
        return search_response.json()

    except Exception as e:
        logging.error(f"Error processing Telex trigger: {e}")
        raise HTTPException(status_code=500, detail="Failed to process Telex request")
