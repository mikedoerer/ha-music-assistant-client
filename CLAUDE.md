# CLAUDE.md

This file provides guidance to Claude Code when working in this repository.

## What this is

A small HACS custom integration for Home Assistant (`custom_components/mass_playlist/`, domain
still to be finalized — see below). Its **only** job: register HA services that create and fill
a real, saved playlist in Music Assistant, by talking directly to the Music Assistant server's
WebSocket API via the `music-assistant-client` PyPI package.

This exists because HA's own built-in `music_assistant` integration does **not** expose
playlist-creation as an HA service — confirmed live against the target instance
(`ha_list_services(domain="music_assistant")`), the only services it registers are `search`,
`get_library`, `play_media`, `play_announcement`, `transfer_queue`, `get_queue`. Playlist
creation/filling only exists on Music Assistant's own WebSocket command bus
(`music/playlists/create_playlist`, `music/playlists/add_playlist_tracks`), which nothing in HA
core forwards. A plain HA automation/blueprint (YAML + Jinja + service calls) has no way to reach
those commands — HA's automation engine can only call *registered services* plus a few built-ins
(`delay`, `wait_template`, ...). There is no generic "call an arbitrary WebSocket API" action in
HA. Hence: this integration exists purely to register the missing services.

One-person hobby project, sibling to [ha-clock-device](https://github.com/mikedoerer/ha-clock-device)
(same owner/instance, same conventions — read that repo's CLAUDE.md if you want more background
on how this user structures HA custom integrations).

## Why this exists (the actual feature request)

The target HA instance has an existing Assist voice automation, `automation.bad_musik` (alias
"Bad Musik"), built from a **local German fork** of the official Music Assistant
["Local LLM Enhanced Voice Support" blueprint](https://github.com/music-assistant/voice-support/blob/main/llm-enhanced-local-assist-blueprint/mass_llm_enhanced_assist_blueprint_en.yaml).
Today it only *plays* music ("spiel/spiele/höre/misch/mische {query}"). The goal is a new voice
command, "erstelle eine playlist rock der 90er", that generates and **saves** a real named
playlist of **~50 tracks** in Music Assistant's library — not just a transient playback queue.

## Target environment (the live HA instance this plugs into)

- **SSH**: `ssh mike@homeassistant` — passwordless, sudo works. **Session-scoped, not standing
  infrastructure** — reachability was confirmed in the originating session but may not be granted
  in a fresh one. Check (`ssh -o BatchMode=yes -o ConnectTimeout=4 mike@homeassistant "echo OK"`)
  before relying on it; don't assume.
- **ha-mcp**: Home Assistant MCP connector tools, prefixed `mcp__<id>__ha_*` (e.g. `ha_call_service`,
  `ha_get_integration`, `ha_search`, `ha_manage_hacs`, `ha_restart`). Also session-scoped — check
  via `ToolSearch` early rather than assuming it's connected. When available, prefer scoped
  `ha_*` calls or lean `curl`+`jq` over SSH for read-only checks; see the sibling project's memory
  for the established preference order (ha-mcp when connected, else SSH, off-network neither).
- **Music Assistant server**: reachable from the HA host at `http://d5369777-music-assistant:8094`
  (internal hassio hostname/port — confirmed via `curl .../info`: `server_version 2.9.13`,
  `schema_version 31`). This is a *different* server/WS endpoint than HA's own WebSocket API —
  HA's `ws_command` escape hatches (e.g. in `ha_call_service`) do **not** reach it.
- **Auth — read at runtime, never hardcode**: HA's own `music_assistant` config entry (domain
  `music_assistant`, single entry) already holds the URL + a long-lived token for this exact
  connection, under `entry.data["url"]` / `entry.data["token"]`. The new integration must read
  this from the live config entry at call time, e.g.:
  ```python
  entries = hass.config_entries.async_entries("music_assistant")
  if not entries or entries[0].state is not ConfigEntryState.LOADED:
      raise ServiceValidationError("Music Assistant integration is not set up")
  url = entries[0].data["url"]
  token = entries[0].data["token"]
  ```
  **Never write an actual token or the raw `data` dict into this repo, logs, or commit messages.**
  If you need to inspect it live, read it from the running instance, use it in-memory, and discard.
- **The blueprint to extend**: `/config/blueprints/automation/custom/llm_enhanced_de.yaml` on the
  HA host. Confirmed (2026-08-20) its only existing change vs. upstream is German shuffle-word
  detection (`misch`/`mische` alongside `shuffle`) — documented in the blueprint's own top-level
  `description:` block, which follows a "Lokaler Fork ... Einzige Änderung ..." changelog style;
  extend that description when you add the playlist-creation change, don't just silently edit the
  logic.
  **Always edit this DE fork in place. Never point the automation back at the upstream/English
  blueprint** — this was an explicit, repeated instruction from the user in the originating
  session.
- **The automation using it**: `automation.bad_musik`. Blueprint inputs currently: `llm_agent:
  conversation.extended_openai_conversation` (this conversation agent is set up under an Assist
  pipeline called "Claude Assist" — **out of scope, never touch that pipeline's own
  settings/wake word/agent config**, only the blueprint/automation YAML is in scope here),
  `default_player: media_player.bad_box`, `trigger: ["(spiel|spiele|höre|misch|mische) {query}"]`.
- **`music_assistant` config_entry_id** (needed for `music_assistant.search` calls):
  `01KJ0XAESYSBNGX5N40Y8SSM19` at the time this was written — re-verify, don't assume it's stable
  forever (`ha_get_integration(domain="music_assistant")`).

## Music Assistant WS API facts (already verified live against the target server, schema 31)

`pip install music-assistant-client` (PyPI, current version `1.5.1`; import name
`music_assistant_client`; depends on `aiohttp>=3.8.6`, `music_assistant_models`). Source:
[music-assistant/client](https://github.com/music-assistant/client).

Minimal one-shot usage (no need for `start_listening()` — `send_command` handles request/response
directly without subscribing to the event stream; confirmed in the client library's own source
comment):

```python
from music_assistant_client import MusicAssistantClient

client = MusicAssistantClient(url, None, token=token)
await client.connect()
playlist = await client.send_command(
    "music/playlists/create_playlist", name="Rock der 90er", media_types=["track"]
)
# playlist["item_id"] is the db_playlist_id add_playlist_tracks expects
await client.send_command(
    "music/playlists/add_playlist_tracks",
    db_playlist_id=playlist["item_id"],
    uris=[...],
)
await client.disconnect()
```

- `create_playlist(name, media_types=["track"], provider_instance_or_domain=None)`: **omit**
  `provider_instance_or_domain`, which defaults to Music Assistant's **`builtin`** provider —
  playlists live locally in MA's own DB, independent of Spotify/Tidal/etc., no write-scope on any
  streaming account needed. This is what "erstelle eine playlist" should use.
- `add_playlist_tracks(db_playlist_id, uris)`: `uris` are full MA media URIs (e.g.
  `tidal--XJWUNufZ://track/77610757`), not free text. Resolve each LLM-suggested "Artist - Title"
  string via the **already-available** `music_assistant.search` HA service first — no new code
  needed for this half:
  ```yaml
  action: music_assistant.search
  data:
    config_entry_id: "01KJ0XAESYSBNGX5N40Y8SSM19"
    name: "{{ track_name }}"
    artist: "{{ artist_name }}"
    media_type: ["track"]
  return_response: true
  ```
  Verified live response shape: `service_response.tracks` is a list, best match first;
  `service_response.tracks[0].uri` is what you want. Can be an **empty list** when nothing
  matched — the blueprint loop must skip those, not error.

## Planned design

- **Domain**: `mass_playlist` (custom_components/mass_playlist/) — deliberately distinct from
  `music_assistant`, which belongs to the core integration. Open to a better name if one occurs to
  you, but avoid anything that could be mistaken for the core integration itself.
- **Config flow**: singleton, no fields — same `single_instance_allowed`-style pattern as
  ha-clock-device's `config_flow.py`. Its only purpose is registering/unregistering the services
  on entry setup/unload; no device, no entities.
- **Services** (starting recommendation, not fixed — this session's call):
  - `mass_playlist.create_and_fill` — one combined service: `name: str`, `uris: list[str]`,
    optional `provider_instance_or_domain: str | None`. Internally does `create_playlist` +
    `add_playlist_tracks` over a single WS connection (connect once, both commands, disconnect).
    `supports_response: True` (`SupportsResponse.ONLY`), returning something like
    `{"playlist_id": ..., "name": ..., "requested": N, "added": M}` so the blueprint can speak an
    accurate confirmation. A single combined service keeps the blueprint-side YAML simple — one
    action instead of orchestrating a create + fill pair with an id hand-off across two calls.
  - Fail loudly (`ServiceValidationError`/`HomeAssistantError`), not silently, when: the
    `music_assistant` config entry isn't loaded, the WS connect/auth fails, or `uris` is empty —
    matches this project family's existing "no silent failure modes" convention (see
    ha-clock-device's CLAUDE.md and its `feedback_wecker_test_state`-adjacent history for why that
    matters to this user).
- **Blueprint change** (`llm_enhanced_de.yaml` on the HA host, edited via SSH):
  - Add a **second** conversation trigger (its own `id:`) for playlist creation, e.g.
    `(erstelle|leg an) [eine] playlist {query}` — pick wording that won't collide with the
    existing `(spiel|spiele|höre|misch|mische) {query}` trigger. Keep both triggers on the *same*
    automation/blueprint (not a second automation) so `llm_agent`/`default_player` stay shared.
  - Branch the `actions:` on `trigger.id`. Leave the existing play/shuffle path untouched. New
    path:
    1. A new LLM prompt (via the same `conversation.process` + `from_json` pattern already used)
       asking for **exactly ~50** suggestions as JSON, e.g.
       `{"playlist_name": "...", "tracks": ["Artist - Title", ...]}`.
    2. `repeat.for_each` over the suggested tracks, calling `music_assistant.search` per track
       (see above), collecting resolved `uri`s and skipping empty results.
    3. Call `mass_playlist.create_and_fill` with the collected `uris` and a playlist name (LLM
       `playlist_name`, or derived from the query — open decision, see below).
    4. `set_conversation_response` confirming playlist name + track count, German, matching the
       fork's existing response style (see `area_response`/`player_response` inputs for tone).

## Open decisions for the implementing session

- Exact German trigger wording for "create playlist" — needs to be unambiguous against the
  existing play/shuffle trigger.
- What to do when `music_assistant.search` resolves fewer than ~50 of the suggested tracks: accept
  fewer, ask the LLM for a top-up batch, or something else — don't loop indefinitely either way.
- Playlist naming source (LLM `playlist_name` field vs. derived directly from the spoken query).
- Whether `mass_playlist` is the final domain name.

## Testing

No test suite here either (same as ha-clock-device) — `.github/workflows/validate.yml` (hassfest +
HACS validation) already copied into this repo is the only CI. Real verification is on-device:
install via HACS custom repository (or copy to `/config/custom_components/`), restart HA, then
trigger the new voice command on the "Bad Musik" automation's satellite and confirm a real,
named playlist with ~50 tracks appears in Music Assistant's library afterward.

Bump `version` in `manifest.json` when shipping a user-visible change (HACS/hassfest expects it to
move) — same convention as ha-clock-device.
