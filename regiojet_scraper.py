import time
from datetime import datetime
import pandas as pd
import numpy as np
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
import requests
import lxml
from selenium.webdriver.support.ui import WebDriverWait 
from selenium.webdriver.support import expected_conditions as EC

# ! current issues: 
# ! only one-way trips supported - for now, must fetch return ticket info separately (dynamic page structure when selecting return) 
# ! can't access city ids for all cities (locked behind API) - must mock for now; perhaps use selenium to type in city names $ get ids from url? 
# ! must use selenium - requests doesn't fetch appropriate html even after waiting
service = Service(executable_path="/Users/zdzilowska/Desktop/comp/mine/RegiojetScraper/chromedriver")
driver = webdriver.Chrome(service=service)

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
               'destination', 'arrival_date', 'arrival_hour', 'price', 'fare_type', 'available']
    df = pd.DataFrame(columns=columns)
    return df

# Inserts data into the DataFrame.
# @df: DataFrame to insert the ticket into
# @ticket_id: ID of the ticket (regiojet identifier)
# @origin: Origin of the ticket (id of the city)
# @departure_date: Departure date of the ticket (YYYY-MM-DD)
# @departure_hour: Departure hour of the ticket in local time (HH:MM)
# @destination: Destination of the ticket (id of the city)
# @arrival_date: Arrival date of the ticket (YYYY-MM-DD)
# @arrival_hour: Arrival hour of the ticket in local time (HH:MM). If arrival is day after departure, written as 'HH:MM +1'
# @price: Price of the ticket (as a string)
# @fare_type: Type of the ticket (e.g., 'regular', 'student', 'senior', 'youth_13_to_17', 'youth_6_to_12', 'youth_under_5')
# @available: Number of seats available for the ticket
def insert_ticket(df, ticket_id, origin, departure_date, departure_hour, destination, arrival_date, arrival_hour, price, fare_type, available):
    # Create a new ticket entry
    new_ticket = {
        # Generate a simple ticket_id based on the curr number of entries
        'ticket_id': ticket_id,
        'origin': origin,
        'departure_date': departure_date,
        'departure_hour': departure_hour,
        'destination': destination,
        'arrival_date': arrival_date,
        'arrival_hour': arrival_hour,
        'price': price,
        'fare_type': fare_type,
        'available': available,
    }
    print(f"Inserting ticket: {new_ticket}")  # Debug print
    # Append the new ticket to the DataFrame
    df.loc[len(df)] = new_ticket
    return df

# Scrapes the ticket information from the website
def scrape_tickets(df, origin, destination, departure_date, fare_type):
    url = parse_url(origin, destination, departure_date, fare_type)
    driver.get(url)
    soup = BeautifulSoup(driver.page_source, 'lxml')
    
    # find all dates
    date_headers = soup.find_all('p', class_='mt-0.5 lg:mt-1 mb-2 lg:mb-3 sm:text-base font-bold')
    # Loop through each date and scrape associated ticket information
    for date_header in date_headers:
        date = date_header.text.strip()  # Extract the date text
        
        # Convert date to YYYY-MM-DD format
        # Unconverted: ex. "Wednesday, 25. September 2024"
        try:
            date_obj = datetime.strptime(date, "%A, %d. %B %Y")
            formatted_date = date_obj.strftime("%Y-%m-%d")
        except ValueError as e:
            print(f"Date format error: {e}")
            continue

        # Find the next sibling; should be the 'w-full flex flex-col' containing the tickets for the date above
        ticket_container = date_header.find_next('div', class_='w-full flex flex-col')

        if ticket_container:
            tickets = ticket_container.find_all('li')  # Each ticket is in an <li> tag
            # Loop through tickets & extract details
            for ticket in tickets:
                # ! time
                time_info = ticket.find('h2', class_='h3')  # Extract departure and arrival time
                if time_info:
                    departure_hour, arrival_hour = time_info.text.split(' - ')

                # ! price
                price_info = ticket.find('button', class_='inline-flex items-center justify-center px-2.5 rounded-sm font-bold transition focus:outline-none focus-visible:outline-none focus-visible:shadow-border hover:shadow-modal cursor-pointer bg-primary-blue text-white border-none hover:bg-secondary-bluedark focus-visible:bg-secondary-bluedark whitespace-nowrap h-5 whitespace-nowrap')
                if price_info:
                    # extract last element; normally button text = 'from €19.9', after split & [-1] = '€19.9'
                    price = price_info.text.strip().split(' ')[-1] 
                
                # ! seats available 
                # Available seats (free seats)
                seats_info = ticket.find('span', class_='sr-only')
                if seats_info:
                    seats_text = seats_info.text.strip()  # Get the text
                    if "sold out" in seats_text.lower():  # Check if 'sold out' is in the text
                        available_seats = 0  # Set to 0 if sold out
                    else:
                        available_seats = seats_text.split()[-1]  # Extract the number from the text
                else:
                    available_seats = 0

                # ! booking info
                booking_button = ticket.find('button', {'data-id': lambda x: x and 'connection-card' in x})
                if booking_button:
                    # Extract the data-id attribute value
                    data_id = booking_button['data-id']  # 'connection-card-price-7070534785,7330426712'
                    # Split the IDs if there are multiple ones separated by a comma
                    ticket_ids = data_id.split('-')[-1].split(',')
                    # Extract the first ticket ID 
                    # TODO: handle multiple
                    primary_ticket_id = ticket_ids[0]  # '7070534785'
                insert_ticket(df, primary_ticket_id, origin, formatted_date, departure_hour, destination, formatted_date, arrival_hour, price, fare_type, available_seats)  
    driver.quit() 
    return "success"

# Prompt user input from the command line
def main():
    df = create_dataframe()

    # Retrieve desired ticket info
    origin = input("Enter the departure city in English (e.g., 'Cracow'): ")
    destination = input("Enter the arrival city in English (e.g., 'Copenhagen'): ")
    departure_date = input("Enter the departure date (YYYY-MM-DD): ")
    fares = input("Enter the fare types, separated by '-' (TYPE-TYPE-TYPE... e.g. 'regular-regular-senior'): ")

    scrape_tickets(df, origin, destination, departure_date, fares)
    print(df)


if __name__ == "__main__":
    main()
