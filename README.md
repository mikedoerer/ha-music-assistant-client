# Music Assistant Playlist Bridge

> ⚠️ **Not started yet.** See [CLAUDE.md](CLAUDE.md) for the full technical spec, research
> findings, and target-environment details — this is the entry point for implementation.

HACS integration for Home Assistant: registers HA services that create and fill a real, saved
playlist in [Music Assistant](https://music-assistant.io/) by talking directly to its WebSocket
API — a gap HA's own built-in `music_assistant` integration doesn't cover.

Built to power a new voice command ("erstelle eine playlist rock der 90er") on an existing
Assist automation, alongside the sibling project
[ha-clock-device](https://github.com/mikedoerer/ha-clock-device).
