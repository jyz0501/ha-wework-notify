"""The WeWork Notify integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .api import WeWorkAppClient, WeWorkBotClient, WeWorkError
from .const import (
    CONF_AGENT_ID,
    CONF_CORP_ID,
    CONF_CORP_SECRET,
    CONF_DEFAULT_TO_PARTY,
    CONF_DEFAULT_TO_TAG,
    CONF_DEFAULT_TO_USER,
    CONF_ENTRY_ID,
    CONF_ENTRY_TITLE,
    CONF_ENTRY_TYPE,
    CONF_IMAGE_BASE64,
    CONF_IMAGE_MD5,
    CONF_IMAGE_MEDIA_ID,
    CONF_MESSAGE,
    CONF_MESSAGE_TYPE,
    CONF_MENTIONED_LIST,
    CONF_MENTIONED_MOBILE_LIST,
    CONF_TO_PARTY,
    CONF_TO_TAG,
    CONF_TO_USER,
    CONF_WEBHOOK_KEY,
    DOMAIN,
    ENTRY_TYPE_APP,
    ENTRY_TYPE_BOT,
    MESSAGE_TYPE_MARKDOWN,
    MESSAGE_TYPE_TEXT,
    MESSAGE_TYPE_IMAGE,
    SERVICE_SEND_MESSAGE,
)

_LOGGER = logging.getLogger(__name__)

RUNTIME_CLIENT = "client"

SEND_MESSAGE_SCHEMA = vol.Schema(
    {
        vol.Exclusive(CONF_ENTRY_ID, "entry_ref"): cv.string,
        vol.Exclusive(CONF_ENTRY_TITLE, "entry_ref"): cv.string,
        vol.Optional(CONF_MESSAGE_TYPE, default=MESSAGE_TYPE_TEXT): vol.In(
            {MESSAGE_TYPE_TEXT, MESSAGE_TYPE_MARKDOWN, MESSAGE_TYPE_IMAGE}
        ),
        vol.Optional(CONF_MESSAGE): cv.string,
        vol.Optional(CONF_TO_USER): cv.string,
        vol.Optional(CONF_TO_PARTY): cv.string,
        vol.Optional(CONF_TO_TAG): cv.string,
        vol.Optional(CONF_MENTIONED_LIST): cv.string,
        vol.Optional(CONF_MENTIONED_MOBILE_LIST): cv.string,
        vol.Optional(CONF_IMAGE_MEDIA_ID): cv.string,
        vol.Optional(CONF_IMAGE_BASE64): cv.string,
        vol.Optional(CONF_IMAGE_MD5): cv.string,
    }
)


async def async_setup(hass: HomeAssistant, _: dict[str, Any]) -> bool:
    """Set up the WeWork Notify integration."""

    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up WeWork Notify from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    _LOGGER.debug("Setting up WeWork Notify entry %s", entry.title)

    if entry.data[CONF_ENTRY_TYPE] == ENTRY_TYPE_APP:
        defaults = _get_defaults(entry)
        client = WeWorkAppClient(
            hass,
            entry.data[CONF_CORP_ID],
            entry.data[CONF_CORP_SECRET],
            entry.data[CONF_AGENT_ID],
            defaults,
        )
    else:
        client = WeWorkBotClient(hass, entry.data[CONF_WEBHOOK_KEY])

    hass.data[DOMAIN][entry.entry_id] = {RUNTIME_CLIENT: client}

    if not hass.services.has_service(DOMAIN, SERVICE_SEND_MESSAGE):

        async def async_handle_send_message(call: ServiceCall) -> None:
            await _async_send_message(hass, call)

        hass.services.async_register(
            DOMAIN,
            SERVICE_SEND_MESSAGE,
            async_handle_send_message,
            schema=SEND_MESSAGE_SCHEMA,
        )

    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a WeWork Notify config entry."""

    data = hass.data.get(DOMAIN, {})
    runtime = data.pop(entry.entry_id, None)
    if runtime and RUNTIME_CLIENT in runtime:
        await runtime[RUNTIME_CLIENT].async_close()

    if not data and hass.services.has_service(DOMAIN, SERVICE_SEND_MESSAGE):
        hass.services.async_remove(DOMAIN, SERVICE_SEND_MESSAGE)

    return True


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def _async_send_message(hass: HomeAssistant, call: ServiceCall) -> None:
    entry = _resolve_entry(hass, call.data)
    runtime = hass.data[DOMAIN].get(entry.entry_id)
    if not runtime:
        raise HomeAssistantError("Entry runtime not initialized")

    client = runtime[RUNTIME_CLIENT]
    payload = dict(call.data)

    defaults = _get_defaults(entry)
    for target_key in (CONF_TO_USER, CONF_TO_PARTY, CONF_TO_TAG):
        if payload.get(target_key) in (None, "") and defaults.get(target_key):
            payload[target_key] = defaults[target_key]

    try:
        await client.async_send_message(payload)
    except WeWorkError as err:
        raise HomeAssistantError(str(err)) from err


def _resolve_entry(hass: HomeAssistant, data: dict[str, Any]) -> ConfigEntry:
    entry_id = data.get(CONF_ENTRY_ID)
    entry_title = data.get(CONF_ENTRY_TITLE)

    if entry_id:
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is None:
            raise HomeAssistantError(f"No entry found with entry_id {entry_id}")
        return entry

    if entry_title:
        matches = [
            entry
            for entry in hass.config_entries.async_entries(DOMAIN)
            if entry.title.lower() == entry_title.lower()
        ]
        if not matches:
            raise HomeAssistantError(f"No entry found with title {entry_title}")
        if len(matches) > 1:
            raise HomeAssistantError(
                "Multiple entries match the given title; please use entry_id instead"
            )
        return matches[0]

    raise HomeAssistantError("Either entry_id or entry_title must be provided")


def _get_defaults(entry: ConfigEntry) -> dict[str, str | None]:
    defaults = {
        CONF_TO_USER: entry.options.get(CONF_TO_USER, entry.data.get(CONF_DEFAULT_TO_USER)),
        CONF_TO_PARTY: entry.options.get(CONF_TO_PARTY, entry.data.get(CONF_DEFAULT_TO_PARTY)),
        CONF_TO_TAG: entry.options.get(CONF_TO_TAG, entry.data.get(CONF_DEFAULT_TO_TAG)),
    }
    return defaults
