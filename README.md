# Music Assistant Playlist Bridge

HACS integration for Home Assistant: registers an HA service that creates and fills a real, saved
playlist in [Music Assistant](https://music-assistant.io/) by talking directly to its WebSocket
API — a gap HA's own built-in `music_assistant` integration doesn't cover.

Built to power a new voice command ("erstelle eine playlist rock der 90er") on an existing
Assist automation, alongside the sibling project
[ha-clock-device](https://github.com/mikedoerer/ha-clock-device).

## Install

Add this repository to HACS as a custom repository (category: Integration), install "Music
Assistant Playlist Bridge", restart Home Assistant, then add the integration from
Settings → Devices & Services (no configuration fields - it's a singleton that just registers the
service below). Requires the core `music_assistant` integration to already be set up.

## Service: `mass_playlist.create_and_fill`

Creates a playlist and adds tracks to it over a single WebSocket connection.

| Field | Required | Description |
| --- | --- | --- |
| `name` | yes | Name of the playlist to create. |
| `uris` | yes | List of resolved Music Assistant track URIs (e.g. from `music_assistant.search`) - not free-text search terms. |
| `provider_instance_or_domain` | no | Provider to create the playlist on. Omit to use Music Assistant's built-in local playlist provider. |

Returns `{"playlist_id", "name", "provider", "requested"}`. `requested` is the number of URIs
passed in - Music Assistant processes `add_playlist_tracks` as a background task, so there's no
synchronous confirmation of how many tracks actually landed by the time the service returns.

See [CLAUDE.md](CLAUDE.md) for the full technical spec, research findings, and target-environment
details, including the planned Assist blueprint change that will call this service.
