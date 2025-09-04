frappe.ui.form.on('Route Plan', {
  refresh(frm) {
    // Avoid duplicate buttons on hot reload
    if (!frm._route_actions_added) {
      const group = __('Actions');
      frm.add_custom_button(__('Fetch from RTM (auto-order)'), () => fetchFromRTM(frm), group);
      frm.add_custom_button(__('Clear Details'), () => clearDetails(frm), group);
      frm._route_actions_added = true;
    }
  }
});

// ---- helpers --------------------------------------------------------------
const CHILD_TABLE_FIELD = 'details'; // change if your child table fieldname differs

function getSubCities(frm) {
  // Supports: child table rows (field `sub_city`), MultiSelect, or CSV string
  const v = frm.doc.sub_cities;
  if (!v) return [];

  if (Array.isArray(v)) {
    // Child table rows
    return v
      .map(r => r.sub_city || r.sub_city_name || r.value || r.name)
      .filter(Boolean);
  }

  if (typeof v === 'string') {
    return v.split(',').map(s => s.trim()).filter(Boolean);
  }

  return [];
}

function clearDetails(frm) {
  const count = (frm.doc[CHILD_TABLE_FIELD] || []).length;
  if (!count) {
    frm.clear_table(CHILD_TABLE_FIELD);
    frm.refresh_field(CHILD_TABLE_FIELD);
    return;
  }

  frappe.confirm(
    __('Clear the current {0} route stop(s)?', [count]),
    () => {
      frm.clear_table(CHILD_TABLE_FIELD);
      frm.refresh_field(CHILD_TABLE_FIELD);
      frappe.show_alert({ message: __('Cleared existing route stops'), indicator: 'green' });
    }
  );
}

function fetchFromRTM(frm) {
  const args = {
    sub_cities: getSubCities(frm),
    date: frm.doc.date || null,
    marketer: frm.doc.marketer || null,
    // Optional starting depot coords if you have them on the doctype
    depot_lat: frm.doc.depot_latitude || frm.doc.depot_lat || frm.doc.latitude || null,
    depot_lng: frm.doc.depot_longitude || frm.doc.depot_lng || frm.doc.longitude || null,
  };

  frappe.call({
    method: 'coffee_roaster.roaster.api.build_route_from_rtm',
    args,
    freeze: true,
    freeze_message: __('Building route…'),
    callback(r) {
      if (!r || !r.message) {
        frappe.msgprint(__('No response from server.'));
        return;
      }

      const weekday = r.message.weekday;
      const stops = r.message.stops || [];

      if (!stops.length) {
        frappe.msgprint(__('No matching RTM Assignments found for the given filters.'));
        return;
      }

      frm.clear_table(CHILD_TABLE_FIELD);

      stops.forEach(row => {
        const d = frm.add_child(CHILD_TABLE_FIELD);
        // Map server fields → child table fields
        d.order_priority = row.seq;             // Int (1..N)
        d.rtm_assignment = row.rtm_assignment;  // Link to RTM Assignment
        d.customer       = row.customer;        // Link to Customer
        d.customer_name  = row.customer_name;   // Data
        d.sub_city       = row.sub_city;        // Link / Select
        d.latitude       = row.latitude;        // Float
        d.longitude      = row.longitude;       // Float
        d.rtm_channel    = row.rtm_channel;     // Select
        d.outlet_type    = row.outlet_type;     // Select
        d.marketer       = row.marketer;        // Link to User (optional)
        d.priority       = row.priority;        // Int (optional)
      });

      frm.refresh_field(CHILD_TABLE_FIELD);

      if (weekday && frm.get_field('weekday')) {
        frm.set_value('weekday', weekday);
      }

      frappe.show_alert({
        message: __('Added {0} stops (auto-ordered)', [stops.length]),
        indicator: 'green'
      });
    },
    error(err) {
      // Unified error notice
      const msg = (err && err.message) || err || __('Unknown error');
      frappe.msgprint({
        title: __('Failed to build route'),
        message: msg,
        indicator: 'red'
      });
    }
  });
}
