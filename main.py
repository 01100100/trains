import csv
import json
import requests

# Read train station data from CSV
stations = {}
with open("data/trainline.csv", newline="") as csvfile:
    reader = csv.DictReader(csvfile, delimiter=";")
    for row in reader:
        if row["name"] not in stations:
            stations[row["name"]] = []
        stations[row["name"]].append(row["id"])

# Read train journey data from JSON
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
features = []
for train in journey:
    print(
        f"🚂 Processing train from {train['start_station']} to {train['end_station']}"
    )
    dep_ids = stations.get(train["start_station"], [])
    arr_ids = stations.get(train["end_station"], [])
    feature = None
    if len(dep_ids) == 0:
        print(f"❌ No station found for {train['start_station']}")
        continue
    if len(arr_ids) == 0:
        print(f"❌ No station found for {train['end_station']}")
        continue
    for dep_id in dep_ids:
        for arr_id in arr_ids:
            print(
                f"🔄 Trying route from {train['start_station']} to {train['end_station']} with id {dep_id} to {arr_id}"
            )
            try:
                feature = get_geojson_feature(dep_id, arr_id)
                if feature:
                    feature["properties"] = train
                    features.append(feature)
                    print(
                        f"✅ Found valid route from {train['start_station']} to {train['end_station']}"
                    )
                    break  # Exit the loop if a valid feature is found
            except requests.RequestException as e:
                print(
                    f"⚠️ Request failed for {train['start_station']} to {train['end_station']} with id {dep_id} to {arr_id}: {e}"
                )
        if feature:
            break  # Exit the outer loop if a valid feature is found
    if not feature:
        print(
            f"❌ No valid route found from {train['start_station']} to {train['end_station']}"
        )

geojson_feature_collection = {"type": "FeatureCollection", "features": features}

# Output the GeoJSON FeatureCollection
with open("output/train_journeys.geojson", "w") as geojsonfile:
    json.dump(geojson_feature_collection, geojsonfile, indent=2)
