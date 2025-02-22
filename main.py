from fastapi import FastAPI, Query, HTTPException
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
