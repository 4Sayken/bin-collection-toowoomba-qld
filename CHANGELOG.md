# Changelog

All notable changes to Bin Collection Toowoomba QLD are listed here.

## [1.3.0] - 2026-11-26

### Changed

- The council's site is now checked **once a month**, early on the 1st, instead
  of every 6 hours. Each property checks at its own minute between 4 and 5 am.
- The council's reading is saved, so restarting Home Assistant no longer triggers
  a check. Date-based sensors still roll over just after midnight, using the saved
  reading without contacting the council.
- If a monthly check fails, the sensors keep using the saved reading (instead of
  becoming unavailable) and the check is retried daily until one succeeds that month.

### Added

- **Check for changes** button: checks the council's site straight away and shows
  a Home Assistant notification if the next collection differs from what was
  expected.
- **Last checked** and **Last changed** diagnostic sensors.
- Automated tests and linting run on GitHub for every pull request.
- A property's saved reading is deleted when the property is removed.

## [1.2.0] - 2026-11-20

### Changed

- **Bins** renamed to **Bins to put out**.
- **Bins out** renamed to **Bin night**, and it's now on only the day before
  collection (previously it stayed on through collection day too).

## [1.1.0] - 2026-11-20

### Changed

- Renamed from "Toowoomba Bin Schedule" to **Bin Collection Toowoomba QLD**. The
  internal ID changed to `bin_collection_toowoomba_qld` and the repository moved
  to `4Sayken/bin-collection-toowoomba-qld`, so existing setups need to be added
  again.

### Added

- **Next recycling** and **Next green waste** date sensors.

## [1.0.0] - 2026-11-20

### Added

- First release: set up a property by searching for its address, with sensors
  for the next collection, which bins go out, days until collection, and
  recycling week, green waste week and bins out binary sensors.

[1.3.0]: https://github.com/4Sayken/bin-collection-toowoomba-qld/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/4Sayken/bin-collection-toowoomba-qld/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/4Sayken/bin-collection-toowoomba-qld/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/4Sayken/bin-collection-toowoomba-qld/releases/tag/v1.0.0
