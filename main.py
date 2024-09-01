import csv
import json
import requests

# Read train station data from CSV and create a lookup table
stations = {}
with open("data/trainline.csv", newline="") as csvfile:
    reader = csv.DictReader(csvfile, delimiter=";")
    for row in reader:
        if row["name"] not in stations:
            stations[row["name"]] = []
        stations[row["name"]].append(
            {
                "id": row["id"],
                "lat": row["latitude"],
                "lon": row["longitude"],
                "country": row["country"],
                "uic8_sncf": row["uic8_sncf"],
                "sncf_id": row["sncf_id"],
                "obb_id": row["obb_id"],
                "trenitalia_id": row["trenitalia_id"],
                "trenord_id": row["trenord_id"],
                "db_id": row["db_id"],
            }
        )

with open("data/journey.json") as jsonfile:
    journey = json.load(jsonfile)


# Function to get GeoJSON feature from API and create a valid geojson LineString feature
def get_geojson_feature(dep_id, arr_id):
    url = f"https://trainmap.ntag.fr/api/route/?simplify=1&dep={dep_id}&arr={arr_id}"
    response = requests.get(url)
    if response.status_code == 500:
        print(f"🚨 500 error for URL: {response.url}")
        return None
    response.raise_for_status()
    feature = response.json()
    if feature["geometry"]["type"] == "Polygon":
        feature["geometry"]["type"] = "LineString"
        feature["geometry"]["coordinates"] = feature["geometry"]["coordinates"][0]
    return feature


# Create GeoJSON FeatureCollection
train_journeys_features = []
train_station_features = []
for trip in journey:
    print(
        f"🚂 Processing train from {trip['start_station']} to {trip['end_station']}"
    )
    possible_departure_stations = stations.get(trip["start_station"], [])
    possible_arrival_stations = stations.get(trip["end_station"], [])
    feature = None
    if len(possible_departure_stations) == 0:
        print(f"❌ No station found for {trip['start_station']}")
        continue
    if len(possible_arrival_stations) == 0:
        print(f"❌ No station found for {trip['end_station']}")
        continue
    for dep in possible_departure_stations:
        for arr in possible_arrival_stations:
            print(
                f"🔄 Trying route from {trip['start_station']} to {trip['end_station']} with id {dep["id"]} to {arr["id"]}"
            )
            try:
                feature = get_geojson_feature(dep["id"], arr["id"])
                if feature:
                    feature["properties"] = trip
                    feature["properties"]["dep_country"] =  dep["country"]
                    feature["properties"]["arr_country"] =  arr["country"]
                    train_journeys_features.append(feature)
                    print(
                        f"✅ Found valid route from {trip['start_station']} to {trip['end_station']}"
                    )
                    train_station_features.append(
                        {
                            "type": "Feature",
                            "geometry": {
                                "type": "Point",
                                "coordinates": [float(dep["lon"]), float(dep["lat"])],
                            },
                            "properties": {
                                "name": trip["start_station"],
                                "country": dep["country"],
                            },
                        }
                    )
                    break  # Exit the loop if a valid feature is found
            except requests.RequestException as e:
                print(
                    f"⚠️ Request failed for {trip['start_station']} to {trip['end_station']} with id {dep["id"]} to {arr["id"]}: {e}"
                )
        if feature:
            break  # Exit the outer loop if a valid feature is found
    if not feature:
        print(
            f"❌ No valid route found from {trip['start_station']} to {trip['end_station']}"
        )

# Output the GeoJSON FeatureCollection
with open("site/src/output/train_journeys.json", "w") as geojsonfile:
    json.dump(
        {"type": "FeatureCollection", "features": train_journeys_features},
        geojsonfile,
        indent=2,
    )

# Output the GeoJSON FeatureCollection
with open("site/src/output/train_stations.geojson", "w") as geojsonfile:
    json.dump(
        {"type": "FeatureCollection", "features": train_station_features},
        geojsonfile,
        indent=2,
    )
