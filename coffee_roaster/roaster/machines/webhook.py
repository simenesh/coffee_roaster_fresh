import frappe
import json
from coffee_roaster.roaster.machines.service import import_curve_into_log

# Python's built-in logging module
import logging
log = logging.getLogger(__name__)


@frappe.whitelist(allow_guest=True)
def ingest(token: str | None = None, log_name: str | None = None):
    """
    Webhook endpoint to ingest roasting curve data.

    Accepts data via POST request body. Authenticates using a token provided
    in the JSON body, query parameters, or headers. Can automatically create
    a new Coffee Roasting Log if configured to do so.

    Headers:
        X-Roast-Token: Authentication token.
        X-Roast-Filename: The original filename of the curve data.
        X-Roast-Adapter: The specific adapter to use for parsing.

    Args:
        token (str, optional): Authentication token.
        log_name (str, optional): The name of the Coffee Roasting Log to attach the curve to.
    """
    # --- Authentication ---
    token = (token
             or frappe.request.args.get("token")
             or frappe.request.headers.get("X-Roast-Token"))
    token = (token or "").strip()

    # SUGGESTION: Cache the settings to reduce DB calls on frequent requests.
    # The cache will be cleared automatically if Roaster Settings are saved.
    def _get_roaster_settings():
        return frappe.db.get_value("Roaster Settings", "Roaster Settings",
                                   ["machine_webhook_token", "auto_create_roast_log"],
                                   as_dict=True)

    settings = frappe.cache().get_value("roaster_settings", _get_roaster_settings)
    token_cfg = (settings.machine_webhook_token or "").strip()

    if not token_cfg or token != token_cfg:
        frappe.throw("Invalid token", frappe.PermissionError)

    # --- Get Request Data ---
    raw_content = frappe.request.get_data() or b""
    filename = frappe.request.headers.get("X-Roast-Filename") or "roast.json"
    adapter = frappe.request.headers.get("X-Roast-Adapter")

    # SUGGESTION: Add logging for better debugging.
    log.info(f"Webhook invoked. filename='{filename}', adapter='{adapter}', log_name='{log_name}'")

    # --- Determine Roasting Log ---
    if not log_name and int(settings.auto_create_roast_log or 0):
        try:
            crl = frappe.new_doc("Coffee Roasting Log")
            crl.roast_date = frappe.utils.today()
            crl.insert(ignore_permissions=True)
            log_name = crl.name
            log.info(f"Auto-created Coffee Roasting Log: {log_name}")
        except Exception as e:
            log.error(f"Failed to auto-create Coffee Roasting Log: {e}")
            frappe.throw("Configuration error: Failed to auto-create roast log.")

    # SUGGESTION: Use frappe.ValidationError for clearer client-side error signals.
    if not log_name:
        frappe.throw("Header 'X-Roast-Log-Name' is required (or enable 'auto_create_roast_log' in settings)",
                     frappe.ValidationError)

    # --- Process Data ---
    try:
        # Pass data to your service function to handle the core logic
        result = import_curve_into_log(
            "Coffee Roasting Log",
            log_name,
            filename=filename,
            content=raw_content,
            adapter=adapter
        )
        log.info(f"Successfully imported curve into {log_name}")
        # Ensure the result is serializable
        return result or {"status": "success"}

    except Exception as e:
        # Log the full error and the raw content for debugging
        log.error(f"Error importing curve into {log_name}. Error: {e}", exc_info=True)
        try:
            # Try to decode raw content for logging, but don't fail if it's not utf-8
            decoded_content = raw_content.decode('utf-8', errors='ignore')
            log.debug(f"Request content for failed import: {decoded_content}")
        except Exception:
            log.debug("Could not decode raw content for logging.")

        # Re-raise the exception to send a 500 error to the client
        raise
