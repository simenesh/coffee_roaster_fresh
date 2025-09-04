frappe.ui.form.on('RTM Assignment', {
refresh(frm) {
// Toggle weekly day field visibility
frm.toggle_display('visit_day', frm.doc.visit_frequency === 'Weekly');
},
visit_frequency(frm) {
frm.toggle_display('visit_day', frm.doc.visit_frequency === 'Weekly');
},
customer: async function(frm) {
if (!frm.doc.customer) return;
// Customer Name
if (!frm.doc.customer_name) {
frappe.db.get_value('Customer', frm.doc.customer, 'customer_name').then(r => {
if (r && r.message && r.message.customer_name) {
frm.set_value('customer_name', r.message.customer_name);
}
});
}
// Default Address
frappe.call({
method: 'frappe.contacts.doctype.address.address.get_default_address',
args: { doctype: 'Customer', name: frm.doc.customer },
callback: function(r) {
if (r && r.message) {
frm.set_value('default_address', r.message);
frappe.call({
method: 'frappe.contacts.doctype.address.address.get_address_display',
args: { address_dict: r.message },
callback: function(d) {
if (d && d.message) {
frm.set_value('address_display', d.message);
}
}
});
}
}
});
// Primary Contact (best-effort)
frappe.db.get_list('Dynamic Link', {
fields: ['parent'],
filters: {
parenttype: 'Contact',
link_doctype: 'Customer',
link_name: frm.doc.customer
}, limit: 1
}).then(rows => {
if (rows && rows.length) {
frm.set_value('contact', rows[0].parent);
frappe.db.get_value('Contact', rows[0].parent, ['phone','email_id']).then(c => {
if (c && c.message) {
if (!frm.doc.phone && c.message.phone) frm.set_value('phone', c.message.phone);
if (!frm.doc.email && c.message.email_id) frm.set_value('email', c.message.email_id);
}
});
}
});
}
});
frappe.ui.form.on('RTM Assignment', {
  refresh(frm) {
    ensure_leaflet().then(() => render_map(frm));
    add_actions(frm);
  },
  latitude: (frm) => update_marker_from_fields(frm),
  longitude: (frm) => update_marker_from_fields(frm),
});

function add_actions(frm) {
  if (!frm.custom_buttons_added) {
    frm.add_custom_button(__('Use my location'), () => use_my_location(frm), 'Geo');
    frm.add_custom_button(__('Fill from Customer'), () => fill_from_customer(frm), 'Geo');
    frm.custom_buttons_added = true;
  }
}

async function ensure_leaflet() {
  // Load Leaflet CSS/JS once per page
  if (!window._leaflet_loading && typeof L === 'undefined') {
    window._leaflet_loading = true;
    await loadCSS('https://unpkg.com/leaflet@1.9.4/dist/leaflet.css');
    await loadJS('https://unpkg.com/leaflet@1.9.4/dist/leaflet.js');
  }
}

function render_map(frm) {
  const html_field = frm.fields_dict['map_html'];
  if (!html_field) return;

  // Create container once
  if (!html_field.$wrapper.find('#rtm-map').length) {
    html_field.$wrapper.html('<div id="rtm-map" style="height:320px;border-radius:12px;"></div>');
  }

  // Init map once per form
  if (!frm._map) {
    const start = get_start_coords(frm);
    frm._map = L.map('rtm-map').setView(start, 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19, attribution: '&copy; OpenStreetMap'
    }).addTo(frm._map);

    frm._marker = L.marker(start, { draggable: true }).addTo(frm._map);
    frm._marker.on('dragend', () => {
      const { lat, lng } = frm._marker.getLatLng();
      set_latlng(frm, lat, lng);
      reverse_geocode(frm, lat, lng);
    });
  } else {
    // If map exists, just move to current coords
    const { lat, lng } = get_start_coords(frm);
    frm._map.setView([lat, lng], 13);
    frm._marker.setLatLng([lat, lng]);
  }
}

function get_start_coords(frm) {
  // Default to Addis Ababa if blank
  const lat = parseFloat(frm.doc.latitude) || 8.9806;
  const lng = parseFloat(frm.doc.longitude) || 38.7578;
  return [lat, lng];
}

function set_latlng(frm, lat, lng) {
  frm.set_value('latitude', lat.toFixed(6));
  frm.set_value('longitude', lng.toFixed(6));
}

function update_marker_from_fields(frm) {
  if (frm._marker && frm.doc.latitude && frm.doc.longitude) {
    const lat = parseFloat(frm.doc.latitude), lng = parseFloat(frm.doc.longitude);
    if (!isNaN(lat) && !isNaN(lng)) frm._marker.setLatLng([lat, lng]);
  }
}

function reverse_geocode(frm, lat, lng) {
  frappe.call({
    method: 'coffee_roaster.coffee_roaster.roaster.doctype.rtm_assignment.rtm_assignment_api.reverse_geocode',
    args: { lat, lng },
    callback: (r) => {
      if (!r || !r.message) return;
      const { sub_city, display_name } = r.message;
      if (sub_city && !frm.doc.sub_city) frm.set_value('sub_city', sub_city);
      // optionally show display_name somewhere or as a msgprint:
      // frappe.show_alert({ message: display_name, indicator: 'blue' });
    }
  });
}

function use_my_location(frm) {
  if (!navigator.geolocation) {
    frappe.msgprint(__('Geolocation not supported by browser.'));
    return;
  }
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      const lat = pos.coords.latitude, lng = pos.coords.longitude;
      set_latlng(frm, lat, lng);
      if (frm._map && frm._marker) {
        frm._map.setView([lat, lng], 15);
        frm._marker.setLatLng([lat, lng]);
      }
      reverse_geocode(frm, lat, lng);
    },
    (err) => {
      frappe.msgprint(__('Unable to get location: ') + err.message);
    },
    { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
  );
}

function fill_from_customer(frm) {
  if (!frm.doc.customer) {
    frappe.msgprint(__('Select a Customer first.'));
    return;
  }
  // Pull sub_city / lat / lng custom fields from Customer if you keep them there
  frappe.db.get_value('Customer', frm.doc.customer, ['sub_city', 'latitude', 'longitude'])
    .then(r => {
      if (r && r.message) {
        const { sub_city, latitude, longitude } = r.message;
        if (sub_city && !frm.doc.sub_city) frm.set_value('sub_city', sub_city);
        if (latitude && !frm.doc.latitude) frm.set_value('latitude', latitude);
        if (longitude && !frm.doc.longitude) frm.set_value('longitude', longitude);
        render_map(frm);
      }
    });
}

/* --------- tiny utilities --------- */
function loadJS(src) {
  return new Promise((resolve, reject) => {
    const s = document.createElement('script');
    s.src = src; s.onload = resolve; s.onerror = reject;
    document.head.appendChild(s);
  });
}
function loadCSS(href) {
  return new Promise((resolve, reject) => {
    const l = document.createElement('link');
    l.rel = 'stylesheet'; l.href = href;
    l.onload = resolve; l.onerror = reject;
    document.head.appendChild(l);
  });
}

