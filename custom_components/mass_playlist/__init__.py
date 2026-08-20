"""The Music Assistant Playlist Bridge integration.

Singleton integration with no entities/devices of its own - the only thing
a config entry does is register the `mass_playlist.*` services (see
services.py), which talk directly to the Music Assistant server's WebSocket
API to create and fill a real, saved playlist. See CLAUDE.md for the full
background on why this bridge exists.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .services import async_setup_services, async_unload_services


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    await async_setup_services(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    async_unload_services(hass)
    return True
