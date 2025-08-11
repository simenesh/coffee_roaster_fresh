import frappe

def autoname(doc, method=None):
    if not doc.route_order:
        doc.route_order = 0
        # --- Excel-style print layout (HTML injected in "message") ---

from frappe.utils.jinja import render_template

PRINT_TPL = """
<style>
  .mrp-wrap { font-family: Arial, sans-serif; }
  .mrp-title { font-weight: 700; font-size: 20px; text-align:center; border-bottom:1px solid #000; padding:6px 0; }
  .mrp-subtitle { text-align:center; font-weight:600; padding:4px 0 10px; }
  .mrp-table { width:100%; border-collapse:collapse; font-size:12px; }
  .mrp-table th, .mrp-table td { border:1px solid #000; padding:4px 6px; vertical-align:middle; }
  .mrp-th-center, .mrp-td-center { text-align:center; }
  .mrp-total-row { font-weight:700; }
  .mrp-subcity-cell { font-weight:700; font-size:16px; text-align:center; }
  .mrp-outlet-head th { text-align:center; }
</style>

<div class="mrp-wrap">
  <div class="mrp-title">MASTER ROUTE PLAN BY SUB CITY</div>
  <div class="mrp-subtitle">Distrributor - {{ distributor or "-" }}</div>

  <table class="mrp-table">
    <thead>
      <tr>
        <th rowspan="2" class="mrp-th-center" style="width:170px;">SubCity</th>
        <th rowspan="2" class="mrp-th-center" style="width:50px;">Rout</th>
        <th rowspan="2" class="mrp-th-center" style="width:90px;">Day</th>
        <th rowspan="2" class="" style="width:auto;">Area</th>
        <th colspan="4" class="mrp-th-center" style="width:260px;">Outlet</th>
        <th rowspan="2" class="mrp-th-center" style="width:70px;">Total</th>
      </tr>
      <tr class="mrp-outlet-head">
        <th class="mrp-th-center" style="width:65px;">RT</th>
        <th class="mrp-th-center" style="width:65px;">WS</th>
        <th class="mrp-th-center" style="width:65px;">MM</th>
        <th class="mrp-th-center" style="width:65px;">SM</th>
      </tr>
    </thead>
    <tbody>
      {% for subcity, group in rows|groupby('sub_city') %}
        {% set cnt = group|length %}
        {% set rt_sum = 0 %}{% set ws_sum = 0 %}{% set mm_sum = 0 %}{% set sm_sum = 0 %}
        {% for r in group %}
          {% set _ = namespace() %}
          {% set rt_sum = rt_sum + (r.rt or 0) %}
          {% set ws_sum = ws_sum + (r.ws or 0) %}
          {% set mm_sum = mm_sum + (r.mm or 0) %}
          {% set sm_sum = sm_sum + (r.sm or 0) %}

          <tr>
            {% if loop.first %}
              <td class="mrp-subcity-cell" rowspan="{{ cnt }}">{{ subcity }}</td>
            {% endif %}
            <td class="mrp-td-center">{{ r.route_no }}</td>
            <td class="">{{ r.day }}</td>
            <td class="">{{ r.area }}</td>
            <td class="mrp-td-center">{{ r.rt or "" }}</td>
            <td class="mrp-td-center">{{ r.ws or "" }}</td>
            <td class="mrp-td-center">{{ r.mm or "" }}</td>
            <td class="mrp-td-center">{{ r.sm or "" }}</td>
            <td class="mrp-td-center">{{ (r.rt or 0)+(r.ws or 0)+(r.mm or 0)+(r.sm or 0) }}</td>
          </tr>
        {% endfor %}
        <tr class="mrp-total-row">
          <td colspan="4" class="mrp-td-center">TOTAL</td>
          <td class="mrp-td-center">{{ rt_sum }}</td>
          <td class="mrp-td-center">{{ ws_sum }}</td>
          <td class="mrp-td-center">{{ mm_sum }}</td>
          <td class="mrp-td-center">{{ sm_sum }}</td>
          <td class="mrp-td-center">{{ rt_sum + ws_sum + mm_sum + sm_sum }}</td>
        </tr>
      {% endfor %}
    </tbody>
  </table>
</div>
"""

# Build the rows list from your data (rename keys if different)
# Expecting each row dict to have: sub_city, route_no, day, area, rt, ws, mm, sm
# If your report's `data` already matches, you can pass it directly.
message_html = render_template(
    PRINT_TPL,
    {
        "distributor": filters.get("distributor"),
        "rows": data  # your report rows
    }
)

# Return BOTH: normal columns/data (for on‑screen grid) + printable message
return columns, data, message_html

