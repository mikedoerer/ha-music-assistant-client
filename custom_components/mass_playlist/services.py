"""Services for the Music Assistant Playlist Bridge integration.

`create_and_fill` is the only service: it opens one WebSocket connection to
the Music Assistant server, creates a playlist, adds tracks to it, and
disconnects - a single combined action so the calling automation/blueprint
doesn't have to hand an id across two separate service calls.

`add_playlist_tracks` on the MA server processes the add as a background
task (see the `music-assistant-client` source) - there's no synchronous
confirmation of how many tracks actually landed in the playlist by the time
this service returns, so the response reports `requested` (what was asked
for) only, not a fabricated `added` count.
"""

from __future__ import annotations

import logging

import voluptuous as vol
from music_assistant_client import MusicAssistantClient
from music_assistant_client.exceptions import MusicAssistantClientException
from music_assistant_models.errors import MusicAssistantError

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import aiohttp_client, config_validation as cv

from .const import (
    ATTR_NAME,
    ATTR_PROVIDER_INSTANCE_OR_DOMAIN,
    ATTR_URIS,
    DOMAIN,
    MUSIC_ASSISTANT_DOMAIN,
    SERVICE_CREATE_AND_FILL,
)

_LOGGER = logging.getLogger(__name__)

CREATE_AND_FILL_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_NAME): cv.string,
        vol.Required(ATTR_URIS): vol.All(cv.ensure_list, [cv.string], vol.Length(min=1)),
        vol.Optional(ATTR_PROVIDER_INSTANCE_OR_DOMAIN): cv.string,
    }
)


def _music_assistant_connection(hass: HomeAssistant) -> tuple[str, str]:
    """Return (url, token) from the loaded core `music_assistant` config entry."""
    entries = hass.config_entries.async_entries(MUSIC_ASSISTANT_DOMAIN)
    entry = entries[0] if entries else None
    if entry is None or entry.state is not ConfigEntryState.LOADED:
        raise ServiceValidationError(
            "The Music Assistant integration is not set up - "
            "set it up first before creating a playlist."
        )
    return entry.data["url"], entry.data["token"]


async def _async_handle_create_and_fill(hass: HomeAssistant, call: ServiceCall) -> ServiceResponse:
    url, token = _music_assistant_connection(hass)
    name = call.data[ATTR_NAME]
    uris: list[str] = call.data[ATTR_URIS]
    provider = call.data.get(ATTR_PROVIDER_INSTANCE_OR_DOMAIN)

    session = aiohttp_client.async_get_clientsession(hass)
    client = MusicAssistantClient(url, session, token=token)
    try:
        await client.connect()
        playlist = await client.music.create_playlist(
            name, provider_instance_or_domain=provider
        )
        await client.music.add_playlist_tracks(playlist.item_id, uris)
    except (MusicAssistantClientException, MusicAssistantError) as err:
        raise HomeAssistantError(f"Music Assistant playlist creation failed: {err}") from err
    finally:
        await client.disconnect()

    return {
        "playlist_id": playlist.item_id,
        "name": playlist.name,
        "provider": playlist.provider,
        "requested": len(uris),
    }


async def async_setup_services(hass: HomeAssistant) -> None:
    """Register the mass_playlist.* domain services once for the whole integration."""
    if hass.services.has_service(DOMAIN, SERVICE_CREATE_AND_FILL):
        return

    async def _handle(call: ServiceCall) -> ServiceResponse:
        return await _async_handle_create_and_fill(hass, call)

    hass.services.async_register(
        DOMAIN,
        SERVICE_CREATE_AND_FILL,
        _handle,
        schema=CREATE_AND_FILL_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )


def async_unload_services(hass: HomeAssistant) -> None:
    """Remove the mass_playlist.* domain services."""
    hass.services.async_remove(DOMAIN, SERVICE_CREATE_AND_FILL)
