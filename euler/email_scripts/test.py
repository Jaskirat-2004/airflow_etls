""" EMAIL SCRIPT """

import requests
import json

# JS ====================================================================== JS

BASE_URL = "https://data-intelligence-superset.kochartech.com"

CHART_ID = 1792

API_ENDPOINT = f"/api/v1/chart/{CHART_ID}/data/"

LOGIN_CREDENCIALS = {
    "username":"jaskirat_singh",
    "password":"kipl@1234"
    }

chart_api = BASE_URL + API_ENDPOINT
chart_api_params = {
    "format":"json"
}

# JS ====================================================================== JS

# CREATE A SESSION 
session = requests.Session()
session.get(f"{BASE_URL}/login/", timeout=20)

login_response = session.post(f"{BASE_URL}/login/", data=LOGIN_CREDENCIALS, timeout=20)

if "/login" in login_response.url:
    raise RuntimeError(f"LOGIN FAILED , {login_response.url}")

# FETCH DATA
chart_api_response = session.get(chart_api, params=chart_api_params, timeout=20)

if not chart_api_response.ok:
    raise RuntimeError("NOT AUTHORISED")
if chart_api_response.text == "" or chart_api_response is None:
    raise RuntimeError("NO DATA RETURNED")

results = chart_api_response.json().get("result")
rows = []
for block in results:
    rows.extend(block.get("data"))

print(json.dumps(rows))

# JS ====================================================================== JS


