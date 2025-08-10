import frappe, json, paho.mqtt.client as mqtt
from frappe.utils import now_datetime

MQTT_HOST      = frappe.conf.get("roaster_mqtt_host")  # put this in site_config.json
MQTT_TOPIC_FMT = "roaster/{serial}/telemetry"          # e.g. roaster/PROBAT123/telemetry

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        batch = payload["roast_batch"]
        doc   = frappe.get_doc({
            "doctype": "Roast Machine Telemetry",
            "roast_batch": batch,
            "reading_time": payload.get("timestamp") or now_datetime(),
            "bean_temp": payload["bean_temp"],
            "environment_temp": payload["env_temp"],
            "ror": payload["ror"],
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Telemetry ingest failed")

def start_mqtt_listener():
    client = mqtt.Client()
    client.on_message = on_message
    client.connect(MQTT_HOST, 1883, 60)
    client.subscribe("roaster/+/telemetry")  # wildcard for multiple machines
    client.loop_forever()
