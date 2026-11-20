# Toowoomba Bin Schedule

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz)

A Home Assistant integration that tells you which bins go out this week for any
property in the Toowoomba Regional Council area (Queensland, Australia).

It uses the same lookup as the council's
[Find your bin day](https://www.tr.qld.gov.au/Waste-and-water/Waste-and-recycling/Your-waste-bins-%e2%80%93-general-recycling-and-green-waste#section-2)
tool, so you don't need to visit the website each week.

## Installation

### HACS (recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=4Sayken&repository=toowoomba-bin-schedule&category=integration)

1. In HACS, open the menu (⋮) → **Custom repositories**.
2. Add `https://github.com/4Sayken/toowoomba-bin-schedule` with the
   type **Integration**.
3. Search for **Toowoomba Bin Schedule**, download it and restart Home Assistant.

### Manual

Copy `custom_components/toowoomba_bin_schedule` into your Home Assistant
`config/custom_components` folder and restart.

## Setup

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=toowoomba_bin_schedule)

1. Go to **Settings → Devices & services → Add integration** and pick
   **Toowoomba Bin Schedule**.
2. Type the start of your street address (for example `3 Parsons`).
3. Pick your property from the council's list.

You can add several properties; each becomes its own device.

## Entities

| Entity | Type | What it shows |
| --- | --- | --- |
| Next collection | Sensor (date) | The next collection day |
| Bins | Sensor | Which bins go out, e.g. `General waste & Recycling` |
| Days until collection | Sensor | Days until the next collection (0 on the day) |
| Recycling week | Binary sensor | On when recycling (yellow lid) goes out |
| Green waste week | Binary sensor | On when green waste (green lid) goes out |
| Bins out | Binary sensor | On from the day before collection until the end of collection day |

The **Next collection** sensor also has attributes for each bin, the council's
own wording, and the bin image the council shows.

## How "next collection" is worked out

The council's tool shows *this week's* collection, even after that day has
passed. Once it has, this integration rolls the date forward a week and swaps
recycling and green waste, since they alternate fortnightly. While a date is
rolled forward like this, the `estimated` attribute is `true`; it returns to
`false` as soon as the council publishes the new week.

Green waste is an optional council service. The integration remembers once it
has seen green waste for your property, so if you set it up during a recycling
week, green waste weeks are only predicted after the council shows one.

## Example automation

```yaml
automation:
  - alias: Bin night reminder
    triggers:
      - trigger: time
        at: "18:00:00"
    conditions:
      - condition: state
        entity_id: binary_sensor.3_parsons_street_rangeville_qld_4350_bins_out
        state: "on"
      - condition: numeric_state
        entity_id: sensor.3_parsons_street_rangeville_qld_4350_days_until_collection
        above: 0
    actions:
      - action: notify.notify
        data:
          title: Bin night
          message: >
            Put out: {{ states('sensor.3_parsons_street_rangeville_qld_4350_bins') }}
```

Your entity IDs will match your own address.

## Disclaimer

This project isn't affiliated with or endorsed by Toowoomba Regional Council. It
relies on the council's public website, which may change without notice.
