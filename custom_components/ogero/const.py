"""Constants for ogero."""

import json
from importlib.resources import as_file, files
from logging import Logger, getLogger
from typing import TypedDict


class Manifest(TypedDict):
    domain: str
    name: str
    codeowners: list[str]
    config_flow: bool
    documentation: str
    iot_class: str
    issue_tracker: str
    requirements: list[str]
    version: str


LOGGER: Logger = getLogger(__package__)

with as_file(files(__package__).joinpath("manifest.json")) as file:
    manifest: Manifest = json.loads(file.read_text(encoding="UTF-8"))

NAME = manifest.get("name")
DOMAIN = manifest.get("domain")
VERSION = manifest.get("version")
ATTRIBUTION = "Data retrieved from https://ogero.gov.lb/"
