# Ogero Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/oraad/ha-ogero.svg)](https://github.com/oraad/ha-ogero/releases)

Custom integration for [Ogero](https://ogero.gov.lb/) (Lebanon Telekom). It polls your My Ogero account and exposes usage and billing data as Home Assistant entities.

Powered by [pyogero](https://github.com/oraad/pyogero).

## Installation

### HACS (recommended)

| Parameter | Value |
|-----------|--------|
| Repository | `https://github.com/oraad/ha-ogero` |
| Category | Integration |
| Type | Custom repository |

1. In HACS, open **Integrations → ⋮ → Custom repositories**.
2. Add the repository URL above and select **Integration** as the category.
3. Install **Ogero** and restart Home Assistant.

### Manual

| Parameter | Value |
|-----------|--------|
| Target path | `config/custom_components/ogero` |
| Source | Copy the `custom_components/ogero` folder from this repository |

Restart Home Assistant after copying files.

## Configuration

1. Go to **Settings → Devices & services → Add integration**.
2. Search for **Ogero**.
3. Enter your My Ogero username and password.
4. Select the first phone or DSL line to monitor (you can add more lines afterward).

One integration card is created per Ogero login. Each phone or DSL line appears as its own device.

### Configuration parameters

| Parameter | Where | Description |
|-----------|--------|-------------|
| Username | Config flow | My Ogero login username |
| Password | Config flow | My Ogero login password |
| Account | Device subentry | Phone or DSL line to monitor (per device) |
| Update interval | Integration options | Poll interval (default 1 hour, minimum 15 minutes) |

### Managing lines and credentials

| Action | How |
|--------|-----|
| Add another line | **Configure → Add device** on the integration card |
| Change which line a device uses | Device **Configure** (subentry reconfigure) |
| Change password | **Reauthenticate** on the integration card |
| Change poll interval | **Configure → Ogero options** |

## Removal

1. Open **Settings → Devices & services → Ogero**.
2. Select the integration and choose **Delete** (removes the login and all line devices).
3. To remove a single line only, delete that device from **Settings → Devices & services** (removes the subentry for that account).
4. If installed via HACS, uninstall **Ogero** from HACS and restart Home Assistant.
5. For a manual install, delete `config/custom_components/ogero` and restart.

## Data updates

This integration uses **cloud polling** (`iot_class: cloud_polling`). Ogero does not push updates to Home Assistant; the integration logs into My Ogero on a schedule and refreshes entity states after each successful poll.

- **Default poll interval:** 1 hour (configurable under **Configure → Ogero options**).
- **Allowed range:** 15 minutes minimum, 24 hours maximum.
- **Per line:** Each phone or DSL device has its own coordinator; all sensors on that device update together when its poll completes.
- **Availability:** If a poll fails, entities on that line become unavailable until the next successful update. Use **Reauthenticate** if your My Ogero password changed.
- **Recommendation:** Avoid very short intervals. Data is fetched via the same web portal as the My Ogero app ([pyogero](https://github.com/oraad/pyogero)); frequent polling adds load on Ogero’s servers without giving true real-time usage.

## Supported accounts and lines

This integration connects to the **My Ogero** cloud service, not to a specific modem model.

### Supported

- Any My Ogero account you can sign in to at [ogero.gov.lb](https://ogero.gov.lb/).
- Each phone and/or DSL line linked to that account (one Home Assistant device per line).
- Multiple usernames (separate integration cards, one per login).

### Not supported

- Lines that do not appear in My Ogero after you log in.
- Controlling your line from Home Assistant (reboot modem, change plan, pay bills, etc.) — monitoring only.
- A documented public Ogero API (the integration reads the same data as the web portal).

## Entities

Quick reference for entities on each line device.

### Sensors

| Entity | Description |
|--------|-------------|
| Quota | Monthly quota (GB) |
| Speed | Connection speed label |
| Upload / Download | Usage (GB) |
| Total consumption | Total usage (GB) |
| Extra consumption | Usage above quota (GB) |
| Last update | Last Ogero data refresh |
| Outstanding balance | Total outstanding amount (LBP), with unpaid bill history as attributes |

### Binary sensors

| Entity | ON when |
|--------|---------|
| Unpaid bills | At least one unpaid bill |
| Over quota | Extra consumption is above zero |

## Supported functionality

Detailed reference for each entity on an Ogero line device. There are no buttons, switches, or services — read-only monitoring.

### Sensors

- **Quota**
  - **Description:** Monthly data quota in GB from the Ogero dashboard.
  - **Remarks:** Integer display.

- **Speed**
  - **Description:** Connection speed label as shown on the portal (for example `8 Mbps`).
  - **Remarks:** Diagnostic entity; disabled by default (enable in the entity registry if needed). Text sensor; not a numeric speed test.

- **Upload**
  - **Description:** Upload usage for the current billing period in GB.
  - **Remarks:** One decimal place suggested in the UI.

- **Download**
  - **Description:** Download usage for the current billing period in GB.
  - **Remarks:** One decimal place suggested in the UI.

- **Total consumption**
  - **Description:** Combined upload and download usage in GB.
  - **Remarks:** Useful for dashboards and history graphs.

- **Extra consumption**
  - **Description:** Usage above the monthly quota in GB.
  - **Remarks:** When greater than zero, the **Over quota** binary sensor is on.

- **Last update**
  - **Description:** Timestamp of the last successful data refresh from Ogero.
  - **Remarks:** Diagnostic entity; disabled by default (enable in the entity registry if needed). `device_class: timestamp` (uses the standard HA icon).

- **Outstanding balance**
  - **Description:** Total outstanding bill amount in LBP.
  - **Remarks:** `device_class: monetary`. When unpaid bills exist, the `unpaid_bills` attribute lists period, amount, and status per bill.

### Binary sensors

- **Unpaid bills**
  - **Description:** On when at least one bill is unpaid.
  - **Remarks:** `device_class: problem`. Use for notifications and dashboards.

- **Over quota**
  - **Description:** On when extra consumption is above zero.
  - **Remarks:** `device_class: problem`. Reflects quota exceeded on the portal.

## Known limitations

These are intentional design boundaries, not bug reports (use [GitHub Issues](https://github.com/oraad/ha-ogero/issues) for defects).

- **Read-only** — You cannot pay bills, change packages, or manage lines from Home Assistant.
- **Unofficial data source** — [pyogero](https://github.com/oraad/pyogero) scrapes the My Ogero website. If Ogero changes their portal, the integration may need an update.
- **Polling latency** — Entity states reflect the last successful poll, not live bandwidth.
- **Currency and units** — Balance is in LBP as returned by Ogero; usage is in GB.
- **Shared session** — All lines under one username share one API client on the parent config entry.
- **Home Assistant version** — Developed and tested against Home Assistant **2026.3.x** (see [requirements.txt](requirements.txt)).

## Use cases

Why add Ogero to Home Assistant?

- **Billing alerts** — Notify when **Unpaid bills** turns on or when outstanding balance crosses a threshold you care about.
- **Quota awareness** — Build dashboard cards for consumption versus quota, or alert when **Over quota** is on before extra charges accumulate.
- **Multi-line homes** — One login with separate devices per DSL or phone line, each with its own entities and automations.
- **History and trends** — Record usage sensors with the Recorder to compare months or spot unusual spikes.
- **Wall tablets and voice** — Surface “data used this month” or “any unpaid bills?” on a dashboard or voice assistant.

## Troubleshooting

### Invalid authentication during setup

#### Symptom

The config flow shows **Invalid username or password** (`invalid_auth`).

#### Description

Home Assistant could not log in to My Ogero with the credentials you entered.

#### Resolution

1. Confirm username and password at [ogero.gov.lb](https://ogero.gov.lb/).
2. If you changed your password, open the integration card and use **Reauthenticate**.

### Cannot connect

#### Symptom

The config flow shows **Unable to connect to Ogero** (`cannot_connect`).

#### Description

The integration could not reach the Ogero portal (network or site issue).

#### Resolution

1. Open the My Ogero site in a browser on the same network as Home Assistant.
2. Check firewall or DNS if the site works elsewhere but not on the HA host.
3. Retry setup after Ogero maintenance or outages.

### Entities are unavailable

#### Symptom

Ogero sensors show **unavailable** for one or all lines.

#### Description

The last poll failed (network, parse error, or expired login).

#### Resolution

1. Check **Settings → System → Logs** for `custom_components.ogero` errors.
2. Use **Reauthenticate** on the integration if credentials expired.
3. Avoid very short poll intervals; try the default 1 hour if you suspect rate limiting.

### Account already configured

#### Symptom

Adding a line fails with **This account is already configured for this login**.

#### Description

That phone or DSL line is already set up on this integration card.

#### Resolution

Remove the existing device for that line, or pick a different line in the flow.

### Login already configured

#### Symptom

Setup aborts with **This login is already configured** (`already_configured`).

#### Description

An integration entry already exists for this My Ogero username.

#### Resolution

Use the existing Ogero card, or delete the old entry before adding it again.

### New line added but no entities

#### Symptom

You added a device via **Configure → Add device** but no new sensors appear.

#### Description

Platform setup may not have completed after the subentry was created.

#### Resolution

1. Reload the integration (**Configure → Reload** on the integration card, or restart Home Assistant).
2. If the problem persists, remove the line device and add it again.

### Data feels stale

#### Symptom

Values do not change as often as you expect.

#### Description

Polling only runs on the configured interval (default 1 hour).

#### Resolution

Lower **Update interval** in **Configure → Ogero options** (minimum 15 minutes). Remember that shorter intervals increase load on the Ogero portal.

## Examples

Import automations from the blueprint files in this repository:

1. Copy the `blueprints` folder into your Home Assistant `config` directory (for example `config/blueprints/automation/ogero/`), or clone the repo and point Home Assistant at the blueprint path.
2. Go to **Settings → Automations & scenes → Create automation → Create new automation → Use blueprint**.
3. Select the blueprint and fill in the Ogero entities for your line device.

| Blueprint | Purpose |
|-----------|---------|
| [Notify on unpaid bills](blueprints/automation/ogero/notify_unpaid_bills.yaml) | Notification when **Unpaid bills** turns on |
| [Notify when over quota](blueprints/automation/ogero/notify_over_quota.yaml) | Notification when **Over quota** turns on |
| [Daily usage summary](blueprints/automation/ogero/daily_usage_summary.yaml) | Scheduled notification with consumption and balance |

Each blueprint uses entity selectors filtered to the `ogero` integration so you pick the correct sensors for each line device.

## Development

Use the VS Code dev container, then:

```bash
scripts/setup
scripts/develop
```

Home Assistant runs at http://localhost:8123 with debug logging for this integration.

When adding or renaming entities, update the **Supported functionality** section and any related blueprints in the same change.

## License

MIT — see [LICENSE](LICENSE).
