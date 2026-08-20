"""Constants for the Music Assistant Playlist Bridge integration."""

from __future__ import annotations

DOMAIN = "mass_playlist"

# The core `music_assistant` integration's config entry - read at call time for
# the server URL + token (see services.py), never stored/cached here.
MUSIC_ASSISTANT_DOMAIN = "music_assistant"

SERVICE_CREATE_AND_FILL = "create_and_fill"

ATTR_NAME = "name"
ATTR_URIS = "uris"
ATTR_PROVIDER_INSTANCE_OR_DOMAIN = "provider_instance_or_domain"
