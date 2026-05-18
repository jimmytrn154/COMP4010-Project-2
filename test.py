import ee
import geemap

PROJECT_ID = "comp4010-earth-engine"

try:
    ee.Initialize(project=PROJECT_ID)
except Exception:
    ee.Authenticate()
    ee.Initialize(project=PROJECT_ID)

dataset = ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY").filter(
    ee.Filter.date("2018-05-01", "2018-05-03")
)

precipitation = dataset.select("precipitation")

precipitation_vis = {
    "min": 1,
    "max": 17,
    "palette": ["001137", "0aab1e", "e7eb05", "ff4a2d", "e90000"],
}

print("Earth Engine initialized successfully.")
print("Number of images:", dataset.size().getInfo())

m = geemap.Map()
m.set_center(17.93, 7.71, 2)
m.add_layer(precipitation, precipitation_vis, "Precipitation")

m.to_html(filename="precipitation_map.html")

print("Map saved as precipitation_map.html")