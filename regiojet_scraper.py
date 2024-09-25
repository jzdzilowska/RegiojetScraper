import time
import datetime
import pandas as pd
import numpy as np
from selenium.webdriver.common.by import By
from selenium import webdriver
from bs4 import BeautifulSoup
import requests
from selenium.webdriver.support.ui import WebDriverWait 
from selenium.webdriver.support import expected_conditions as EC

# ! current issues: 
# ! only one-way trips supported - for now, must fetch return ticket info separately (dynamic page structure when selecting return) 
# ! can't access city ids for all cities (locked behind API) - must mock for now; perhaps use selenium to type in city names $ get ids from url? 

# Dictionary mapping city names to their corresponding IDs; mocked for now (could integrate selenium -  the full list 
# is locked for the API)
cities = {
    'Cracow': '1225791000',
    'Prague': '10202003',
    'Vienna': '10202052',
    'Brno': '10202002',
    'London': '10202049',
}

# Dictionary mapping fare types to their corresponding tariff codes
tariffs = {
    'regular': 'REGULAR',
    'student': 'CZECH_STUDENT_PASS_26',
    'senior': 'ISIC',
    'youth_13_to_17': 'CZECH_STUDENT_PASS_15',
    'youth_6_to_12': 'CHILD_UNDER_12',
    'youth_under_5': 'ATTENDED_CHILD',
}

default_url = ("https://regiojet.com/?departureDate={dep_date}&{tariff}"
    "&fromLocationId={dep_id}&fromLocationType=CITY&toLocationId={arrival_id}&toLocationType=CITY")

# Parses the default url based on user input
def parse_url(origin, destination, departure_date, fares): 
    if origin not in cities or destination not in cities:
        raise ValueError("Invalid origin or destination")
    
    # fares are faretype2-faretype1-faretype1(....)
    fare_list = fares.split('-')
    tariff_params = []
    for fare_type in fare_list:
        if fare_type not in tariffs:
            raise ValueError(f"Invalid fare type: {fare_type}")

        # Add the corresponding tariff code for each fare type
        tariff_code = tariffs[fare_type]
        tariff_params.append(f"tariffs={tariff_code}")

    # Join all the tariffs
    tariffs_str = "&".join(tariff_params)

    formatted_url = default_url.format(
        dep_date=departure_date,
        tariff=tariffs_str,
        dep_id=cities[origin],
        arrival_id=cities[destination],
    )
    print(formatted_url)
    return formatted_url

# Creates an empty DataFrame to hold ticket info
def create_dataframe():
    # Pandas used for simplicity (quick verification of functionality with all data stored locally),
    # too much overhead to integrate cloud.
    columns = ['ticket_id', 'origin', 'departure_date', 'departure_hour',
               'destination', 'arrival_date', 'arrival_hour', 'price', 'currency', 'fare_type']
    df = pd.DataFrame(columns=columns)
    return df

# Inserts data into the DataFrame.
# @df: DataFrame to insert the ticket into
# @origin: Origin of the ticket (id of the city)
# @departure_date: Departure date of the ticket (YYYY-MM-DD)
# @departure_hour: Departure hour of the ticket in local time (HH:MM)
# @destination: Destination of the ticket (id of the city)
# @arrival_date: Arrival date of the ticket (YYYY-MM-DD)
# @arrival_hour: Arrival hour of the ticket in local time (HH:MM)
# @price: Price of the ticket (as a string)
# @currency: Currency of the ticket (e.g., USD)
# @fare_type: Type of the ticket (e.g., 'regular', 'student', 'senior', 'youth_13_to_17', 'youth_6_to_12', 'youth_under_5')
def insert_ticket(df, origin, departure_date, departure_hour, destination, arrival_date, arrival_hour, price, currency, fare_type):
    # Create a new ticket entry
    new_ticket = {
        # Generate a simple ticket_id based on the curr number of entries
        'ticket_id': len(df) + 1,
        'origin': origin,
        'departure_date': departure_date,
        'departure_hour': departure_hour,
        'destination': destination,
        'arrival_date': arrival_date,
        'arrival_hour': arrival_hour,
        'price': price,
        'currency': currency
    }
    # Append the new ticket to the DataFrame
    df = df.append(new_ticket, ignore_index=True)
    return df

# Scrapes the ticket information from the website
def scrape_tickets(df, url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    return df

# Prompt user input from the command line
def main():
    df = create_dataframe()

    # Retrieve desired ticket info
    origin = input("Enter the departure city in English (e.g., 'Cracow'): ")
    destination = input("Enter the arrival city in English (e.g., 'Copenhagen'): ")
    departure_date = input("Enter the departure date (YYYY-MM-DD): ")
    fares = input("Enter the fare types, separated by '-' (TYPE-TYPE-TYPE... e.g. 'regular-regular-senior'): ")

    url = parse_url(origin, destination, departure_date, fares)
    scrape_tickets(df, url)
    print(df)


if __name__ == "__main__":
    main()
