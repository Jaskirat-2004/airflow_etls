""" EULER SHRINKAGE EMAIL SCRIPT """

# JS ================================= IMPORTS ================================= JS

import requests
import json
from datetime import datetime, timezone

# JS ================================= CHART PARAMS ================================= JS

CHART_ID = 1792
TIME_RANGE = "Current month"

chart_api_params = {
    "format":"csv"
}

# JS ================================= API ENDPOINTS ================================= JS

BASE_URL = "https://data-intelligence-superset.kochartech.com"

CHART_META_QUERY_ENDPOINT = BASE_URL + f"/api/v1/chart/{CHART_ID}"
CHART_DATA_ENDPOINT = BASE_URL + f"/api/v1/chart/data"

LOGIN_CREDENCIALS = {
    "username":"jaskirat_singh",
    "password":"kipl@1234"
    }

# JS ================================= SESSION COOKIE ================================= JS

session = requests.Session()
session.get(f"{BASE_URL}/login/", timeout=20)
login_response = session.post(f"{BASE_URL}/login/", data=LOGIN_CREDENCIALS, timeout=20)

if "/login" in login_response.url:
    raise RuntimeError(f"LOGIN FAILED , {login_response.url}")

# JS ================================= FETCH QUERY ================================= JS

chart_query_response = session.get(CHART_META_QUERY_ENDPOINT, timeout=20)
query_context = json.loads(chart_query_response.json()["result"]["query_context"])

if not chart_query_response.ok:
    raise RuntimeError(f"NOT AUTHORISED, {chart_query_response.status_code}")
if chart_query_response.text == "" or chart_query_response is None:
    raise RuntimeError("NO DATA RETURNED")

# JS ================================= FILTER QUERY ================================= JS

for q in query_context["queries"]:
    q["time_range"] = TIME_RANGE
    q["filters"] = [{'col': 'report_date', 'op': 'TEMPORAL_RANGE', 'val': TIME_RANGE}]

# JS ================================= FETCH DATA ================================= JS

res = session.post(CHART_DATA_ENDPOINT, json=query_context, timeout=180)
data = res.json()["result"][0]["data"]

# JS ================================= RETURN DATA ================================= JS

def as_date(epoch_ms):
    """report_date is epoch MILLISECONDS. UTC is not optional: local-zone
    conversion in IST pulls midnight UTC back into the previous day."""
    return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")

rows = [
    {
        "Date":        as_date(d["report_date"]),
        "Location":    d["location"],
        "Roster":      round(d["Roster"], 1),
        "Present":     round(d["Present"], 1),
        "Absent":      round(d["Absent"], 1),
        "Shrinkage %": round(d["Shrinkage %"] * 100, 1),   # the api returns a RATIO
    }
    for d in data
]

# JS ================================= RETURN DATA ================================= JS

print(json.dumps(rows, indent=2))