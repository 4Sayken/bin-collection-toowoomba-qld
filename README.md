<p align="center">
  <img src="images/banner.png" alt="Bin Collection Toowoomba QLD" width="520">
</p>

<h1 align="center">Bin Collection Toowoomba QLD</h1>

<p align="center">
  <a href="https://my.home-assistant.io/redirect/hacs_repository/?owner=4Sayken&repository=bin-collection-toowoomba-qld&category=integration"><img src="https://img.shields.io/badge/Marketplace-Custom-41BDF5" alt="Marketplace: Custom"></a>
  <a href="https://github.com/4Sayken/bin-collection-toowoomba-qld/releases"><img src="https://img.shields.io/github/v/release/4Sayken/bin-collection-toowoomba-qld" alt="Release"></a>
  <a href="https://github.com/4Sayken/bin-collection-toowoomba-qld/actions/workflows/validate.yml"><img src="https://img.shields.io/github/actions/workflow/status/4Sayken/bin-collection-toowoomba-qld/validate.yml?branch=main&label=validation" alt="Validation"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/4Sayken/bin-collection-toowoomba-qld" alt="License"></a>
  <br>
  <a href="https://github.com/4Sayken/bin-collection-toowoomba-qld/commits/main"><img src="https://img.shields.io/github/commit-activity/m/4Sayken/bin-collection-toowoomba-qld" alt="Commit activity"></a>
  <img src="https://img.shields.io/badge/Home%20Assistant-2025.3%2B-41BDF5" alt="Home Assistant 2025.3+">
</p>

<p align="center"><em>Know which bins go out, and when, for any property in the Toowoomba Region, right inside Home Assistant.</em></p>

---

<p align="center">
  <img src="images/demo.png" alt="The integration's sensors in Home Assistant" width="600">
</p>

## ✨ What it does

Toowoomba Regional Council's
[Find your bin day](https://www.tr.qld.gov.au/Waste-and-water/Waste-and-recycling/Your-waste-bins-%e2%80%93-general-recycling-and-green-waste#section-2)
tool tells you this week's collection. This integration does the same lookup for
you every few hours and turns it into sensors you can put on a dashboard or use in
automations:

- 📅 **When** the next collection is, and how many days away.
- 🗑️ **Which bins** go out: general waste plus recycling or green waste.
- ♻️ **The next recycling date** and 🌿 **the next green waste date**.
- 🌙 **A "Bins out" switch** that's on the evening before and on collection day, for reminders.

## 🚀 Get Started

> **HACS or Marketplace?** They're the same thing. Since **Home Assistant 2026.11**,
> HACS (the Home Assistant Community Store) is built into Home Assistant as the
> **Marketplace**, under **Settings → Marketplace**. On older versions (2025.3 to
> 2026.10) you install HACS separately. Follow the steps for your version below.

**Add it to Home Assistant through the Marketplace or, before 2026.11, HACS:**

[![Open your Home Assistant instance and open this repository in the Marketplace.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=4Sayken&repository=bin-collection-toowoomba-qld&category=integration)

The button above opens this repository in your Home Assistant. To do it by hand:

**Home Assistant 2026.11 or newer (Marketplace)**

1. Open **Settings → Marketplace** and accept its first-run warning if asked.
2. Connect your GitHub account when prompted; the Marketplace needs it for custom repositories.
3. Open the menu (⋮) → **Custom repositories**, add
   `https://github.com/4Sayken/bin-collection-toowoomba-qld` with the type **Integration**.
4. Search for **Bin Collection Toowoomba QLD**, select **Install**, then restart Home Assistant.

**Home Assistant 2025.3 to 2026.10 (HACS)**

1. In **HACS**, open the menu (⋮) → **Custom repositories**.
2. Add `https://github.com/4Sayken/bin-collection-toowoomba-qld` with the type **Integration**.
3. Search for **Bin Collection Toowoomba QLD**, select **Download**, then restart Home Assistant.

**Manual install (no Marketplace or HACS):** copy
`custom_components/bin_collection_toowoomba_qld` into your Home Assistant
`config/custom_components` folder and restart.

### Add your property

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=bin_collection_toowoomba_qld)

1. Go to **Settings → Devices & services → Add integration** and pick
   **Bin Collection Toowoomba QLD**.
2. Type the start of your street address, for example `12 Example`.
3. Pick your property from the council's list.

You can add several properties; each becomes its own device.

## 🗑️ Entities

| Entity | Type | What it shows |
| --- | --- | --- |
| Next collection | Sensor (date) | The next collection day |
| Bins | Sensor | Which bins go out, e.g. `General waste & Recycling` |
| Days until collection | Sensor | Days until the next collection (0 on the day) |
| Next recycling | Sensor (date) | The next day recycling (yellow lid) is collected |
| Next green waste | Sensor (date) | The next day green waste (green lid) is collected; unknown until the integration has seen green waste for your property |
| Recycling week | Binary sensor | On when recycling goes out at the next collection |
| Green waste week | Binary sensor | On when green waste goes out at the next collection |
| Bins out | Binary sensor | On from the day before collection until the end of collection day |

The **Next collection** sensor also has attributes for each bin, the council's
own wording, and the bin image the council shows.

## 🧮 How the next collection is worked out

The council's tool shows *this week's* collection, even after that day has
passed. Once it has, this integration rolls the date forward a week and swaps
recycling and green waste, since they alternate fortnightly. While a date is
rolled forward like this, the `estimated` attribute is `true`; it returns to
`false` as soon as the council publishes the new week.

Green waste is an optional council service. The integration remembers once it
has seen green waste for your property, so if you set it up during a recycling
week, green waste dates are only predicted after the council shows one.

## 🔄 How often it checks

The integration looks up your property every **6 hours** and again just after
**midnight**, so date-based sensors roll over on time. Each check starts fresh
from what the council's website shows, so any change the council makes (a
holiday shift, a new week) is picked up at the next check.

## 🤖 Example automation

A reminder at 6 pm on bin night:

```yaml
automation:
  - alias: Bin night reminder
    triggers:
      - trigger: time
        at: "18:00:00"
    conditions:
      - condition: state
        entity_id: binary_sensor.12_example_street_toowoomba_qld_4350_bins_out
        state: "on"
      - condition: numeric_state
        entity_id: sensor.12_example_street_toowoomba_qld_4350_days_until_collection
        above: 0
    actions:
      - action: notify.notify
        data:
          title: Bin night
          message: >
            Put out: {{ states('sensor.12_example_street_toowoomba_qld_4350_bins') }}
```

Your entity IDs will match your own address.

## ⬆️ Upgrading from "Toowoomba Bin Schedule"

Version 1.1.0 renamed the integration (its internal ID changed from
`toowoomba_bin_schedule` to `bin_collection_toowoomba_qld`), so it installs as a
new integration. Remove the old **Toowoomba Bin Schedule** entry, then install
this version and add your property again.

## ⚠️ Disclaimer

This project isn't affiliated with or endorsed by Toowoomba Regional Council. It
relies on the council's public website, which may change without notice.
