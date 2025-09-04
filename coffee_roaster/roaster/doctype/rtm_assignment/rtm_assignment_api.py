import frappe, requests

@frappe.whitelist()
def reverse_geocode(lat: float, lng: float):
    r = requests.get(
        "https://nominatim.openstreetmap.org/reverse",
        params={"format":"jsonv2","lat":lat,"lon":lng,"zoom":14,"addressdetails":1},
        headers={"User-Agent":"CoffeeRoaster-ERP/1.0 (admin@example.com)"},
        timeout=10,
    )
    r.raise_for_status()
    data = r.json() or {}
    a = data.get("address", {}) if isinstance(data, dict) else {}
    sub = (a.get("city_district") or a.get("suburb") or a.get("neighbourhood")
           or a.get("borough") or a.get("city") or a.get("town") or a.get("village"))
    return {"display_name": data.get("display_name"), "sub_city": sub}

