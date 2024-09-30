import requests
import json
from datetime import datetime
import re 
import itertools

# cURL; headers for regiojet API request
headers = {
    'accept': 'application/1.2.0+json',
    'accept-language': 'en-US,en;q=0.9',
    'cache-control': 'no-cache',
    'origin': 'https://regiojet.com',
    'priority': 'u=1, i',
    'referer': 'https://regiojet.com/?departureDate=2024-09-28&tariffs=REGULAR&fromLocationId=10202052&fromLocationType=CITY&toLocationId=10202003&toLocationType=CITY&returnDepartureDate=2024-10-05',
    'sec-ch-ua': '"Google Chrome";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'cross-site',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
    'x-application-origin': 'WEB',
    'x-currency': 'EUR',
    'x-lang': 'en',
}

# Creates parameters for the Regiojet API request
# @param departure_date: The departure date in the format 'YYYY-MM-DD'; today if not specified
# @param return_departure_date: The return departure date in the format 'YYYY-MM-DD'; none if not specified
# @param from_location_id: Origin location id; regjojet encoding
# @param to_location_id: Destination location id; regiojet encoding
def create_params(from_location_id, to_location_id):
    return {
        'tariffs': 'REGULAR',
        'toLocationType': 'CITY',
        'toLocationId': to_location_id, 
        'fromLocationType': 'CITY',
        'fromLocationId': from_location_id,  
        # 'departureDate': departure_date, # ! omit when requesting all possible connections
        # 'returnDepartureDate': return_departure_date, # ! omit when requesting all possible connections
    }

"""
# Requests specific connection data from Regiojet API
# @param headers: Headers for the API request (global var; retrieved from curltopython)
# @param params: Parameters for the API request (passed in)
def make_request(headers, params):
    response = requests.get('https://brn-ybus-pubapi.sa.cz/restapi/routes/search/simple', params=params, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data
    else:
        print(f"Failed to retrieve data: {response.status_code}")  # debugging only
        return None
"""
# Helper; converts travel time from hh:mm string to hours
def convert_travel_time(travel_time_str):
    clean_time_str = re.sub(r'[^\d:]', '', travel_time_str) # original: 04:45xa0h
    hours, minutes = map(int, clean_time_str.split(':'))
    total_hours = hours + (minutes / 60.0)
    return total_hours

# Converts data from the Regiojet API to fit Tryp
def convert_to_custom_format(data):
    results = []
    for route in data.get('routes', []):
        result = {
            "departure": datetime.strptime((route['departureTime'].split('.')[0]), '%Y-%m-%dT%H:%M:%S'),
            "arrival": datetime.strptime((route['arrivalTime'].split('.')[0]), '%Y-%m-%dT%H:%M:%S'),
            "duration": convert_travel_time(route['travelTime']),  # Convert seconds to hours
            "carrier": "REGIOJET",
            "iata_origin": route['departureStationId'],
            "iata_destination": route['arrivalStationId'],
            # TODO: Ask if correct - include creditPrice?
            "price": int(route['priceFrom']) + int(route['priceTo']),
            "stops": 0,
            "layover_info": None, 
            "flight_numbers": route['id'],
            "flight_carriers": "REGIOJET",
            "vehicle_type": route['vehicleTypes'],
            "flight_number_was_scraped": False
        }
        results.append(result)
    return results

# Graphs all possible connections between stations based on locations retr. from regiojet API 
def make_graph():
    stations = []
    # Iterates through all regardless of direct connection; sets stations as nodes, connections as edges
    with open('locations.json') as locs:
        data = json.load(locs)
        for country in data:
            for city in country['cities']:
                for station in city['stations']:
                    stations.append({
                        'station_id': station['id'],
                        'station_name': station['name'],
                        'city_name': city['name']
                    })
    # Pairs all stations together
    connections = list(itertools.combinations(stations, 2))
    return connections
    
# Checks if a direct connection exists between two stations via Regiojet API request
# @param from_station_id: Origin station id (regiojet encoding)
# @param to_station_id: Destination station id (regiojet encoding)
# @param headers: Headers for the API request (global var; retrieved from curltopython)
def check_direct_connection(from_station_id, to_station_id, headers):
    # ! Dates omitted
    params = create_params(from_station_id, to_station_id)
    response = requests.get('https://brn-ybus-pubapi.sa.cz/restapi/routes/search/simple', params=params, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        return data  # Returns the route data
    else:
        print(f"Failed to retrieve data for stations {from_station_id} -> {to_station_id}: {response.status_code}")
        return None 

# Function to create all station pairs and check connections
def find_direct_connections():
    # Get all station pairs (regardless of direct connection status)
    connections = make_graph()
    
    direct_connections = []
    # Iterate through all pairs and check for direct routes
    for station1, station2 in connections:
        route_data = check_direct_connection(station1['station_id'], station2['station_id'], headers)
        if route_data and route_data.get('routes'):
            # Store direct connection info
            direct_connections.append({
                'from_station': station1,
                'to_station': station2,
                'route_info': route_data  
            })
    
    # Save the results to a file
    with open('direct_connections.json', 'w') as outfile:
        json.dump(direct_connections, outfile, indent=4)


def main():
    find_direct_connections()

if __name__ == "__main__":
    main()