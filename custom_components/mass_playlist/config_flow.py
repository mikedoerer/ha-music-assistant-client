"""Config flow for the Music Assistant Playlist Bridge integration.

Singleton entry with no fields - its only purpose is to register/unregister
the `mass_playlist.*` services on setup/unload (see __init__.py). Mirrors the
top-level flow of ha-clock-device's AlarmClockConfigFlow, minus the
subentries (this integration has no per-device concept).
"""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import DOMAIN


class MassPlaylistConfigFlow(ConfigFlow, domain=DOMAIN):
    """Singleton config flow - just registers the bridge services."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        if user_input is not None:
            return self.async_create_entry(title="Music Assistant Playlist Bridge", data={})
        return self.async_show_form(step_id="user")
