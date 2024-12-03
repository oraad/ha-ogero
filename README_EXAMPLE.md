# Ogero

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

![Project Maintenance][maintenance-shield]

_Integration to integrate with [ogero][ogero]._

**This integration will set up the following platforms.**

Platform | Description
-- | --
`binary_sensor` | Show something `True` or `False`.
`sensor` | Show info from ogero API.
`switch` | Switch something `True` or `False`.

## Installation

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
1. If you do not have a `custom_components` directory (folder) there, you need to create it.
1. In the `custom_components` directory (folder) create a new folder called `ogero`.
1. Download _all_ the files from the `custom_components/ogero/` directory (folder) in this repository.
1. Place the files you downloaded in the new directory (folder) you created.
1. Restart Home Assistant
1. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "Ogero"

## Configuration is done in the UI

<!---->


***

[ogero]: https://github.com/oraad/ha-ogero
[commits-shield]: https://img.shields.io/github/commit-activity/y/oraad/ha-ogero.svg?style=for-the-badge
[commits]: https://github.com/oraad/ha-ogero/commits/main
[exampleimg]: example.png
[license-shield]: https://img.shields.io/github/license/oraad/ha-ogero.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-Omar%20Raad-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/oraad/ha-ogero.svg?style=for-the-badge
[releases]: https://github.com/oraad/ha-ogero/releases
