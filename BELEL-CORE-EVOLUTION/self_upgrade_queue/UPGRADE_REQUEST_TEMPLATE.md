# SELF-UPGRADE REQUEST (TEMPLATE)

Copy this into a JSON file named:

`upgrade_request__YYYYMMDDThhmmssZ__slug.json`

## Required Fields

- note
- requested_by
- scope: bounded | expansive
- change_type: bugfix | feature | research | governance | security | performance | docs
- targets: list of repo paths intended to be touched
- created_utc: ISO8601 UTC

## Constraints (Recommended)

Specify what must never be modified, and what must always be verified.

## Example Filename

`upgrade_request__20260130T000000Z__research_deduper.json`
