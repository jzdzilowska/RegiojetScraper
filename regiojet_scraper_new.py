import requests
import json
from datetime import datetime
import re 
import itertools

# request headers (regiojet)
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

# request parameters (regiojet)
def create_params(departure_date, return_departure_date, from_location_id, to_location_id):
    return {
        'tariffs': 'REGULAR',
        'toLocationType': 'CITY',
        'toLocationId': to_location_id, 
        'fromLocationType': 'CITY',
        'fromLocationId': from_location_id,  
        'departureDate': departure_date,
        'returnDepartureDate': return_departure_date,
    }

# params = create_params(date, date, id, id)
def make_request(headers):
    params = create_params('2024-10-09', '2024-10-11', '10202052', '10202003')
    response = requests.get('https://brn-ybus-pubapi.sa.cz/restapi/routes/search/simple', params=params, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data
    else:
        print(f"Failed to retrieve data: {response.status_code}")  # debugging only
        return None

def convert_travel_time(travel_time_str):
    clean_time_str = re.sub(r'[^\d:]', '', travel_time_str) # original: 04:45xa0h
    hours, minutes = map(int, clean_time_str.split(':'))
    total_hours = hours + (minutes / 60.0)
    return total_hours

def make_graph():
    stations = []
    # iterate through all; find connections - cities as nodes, connections as edges
    locs = open('locations.json')
    data = json.load(locs)
    for country in data:
        for city in country['cities']:
            for station in city['stations']:
                stations.append({
                    'station_id': station['id'],
                    'station_name': station['name'],
                    'city_name': city['name']
                })

    # generate all possible pairs
    connections = list(itertools.combinations(stations, 2))
    for connection in connections: 
        station1 = connection[0]
        station2 = connection[1]
    return connections

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

def main():
    connections = make_graph()
    for connection in connections: 
        id1 = connection[0]['station_id']
        id2 = connection[1]['station_id']
    data = make_request(headers) 
    if data:  
        # convert - tryp reqs
        custom_format = convert_to_custom_format(data)
        print(json.dumps(custom_format, indent=4, default=str))
    else: 
        print("No data available to process.")

if __name__ == "__main__":
    main()