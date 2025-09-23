"""Config flow for the WeWork Notify integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME

from .const import (
    CONF_AGENT_ID,
    CONF_CORP_ID,
    CONF_CORP_SECRET,
    CONF_DEFAULT_TO_PARTY,
    CONF_DEFAULT_TO_TAG,
    CONF_DEFAULT_TO_USER,
    CONF_ENTRY_TYPE,
    CONF_TO_PARTY,
    CONF_TO_TAG,
    CONF_TO_USER,
    CONF_WEBHOOK_KEY,
    DOMAIN,
    ENTRY_TYPE_APP,
    ENTRY_TYPE_BOT,
)


class WeWorkNotifyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for WeWork Notify."""

    VERSION = 1

    def __init__(self) -> None:
        self._name: str | None = None
        self._entry_type: str | None = None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> config_entries.FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            self._name = user_input[CONF_NAME]
            self._entry_type = user_input[CONF_ENTRY_TYPE]
            if self._entry_type == ENTRY_TYPE_APP:
                return await self.async_step_app()
            return await self.async_step_bot()

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME): str,
                vol.Required(CONF_ENTRY_TYPE): vol.In(
                    {
                        ENTRY_TYPE_APP: "WeCom Custom Application",
                        ENTRY_TYPE_BOT: "WeCom Group Robot",
                    }
                ),
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_app(self, user_input: dict[str, Any] | None = None) -> config_entries.FlowResult:
        errors: dict[str, str] = {}

        defaults = {
            CONF_CORP_ID: "",
            CONF_CORP_SECRET: "",
            CONF_AGENT_ID: 1000000,
            CONF_DEFAULT_TO_USER: "",
            CONF_DEFAULT_TO_PARTY: "",
            CONF_DEFAULT_TO_TAG: "",
        }

        if user_input is not None:
            corp_id = user_input[CONF_CORP_ID].strip()
            corp_secret = user_input[CONF_CORP_SECRET].strip()
            agent_id = user_input[CONF_AGENT_ID]

            await self.async_set_unique_id(f"{ENTRY_TYPE_APP}_{corp_id}_{agent_id}")
            self._abort_if_unique_id_configured()

            data: dict[str, Any] = {
                CONF_ENTRY_TYPE: ENTRY_TYPE_APP,
                CONF_CORP_ID: corp_id,
                CONF_CORP_SECRET: corp_secret,
                CONF_AGENT_ID: agent_id,
            }

            for field, value in (
                (CONF_DEFAULT_TO_USER, user_input.get(CONF_DEFAULT_TO_USER, "")),
                (CONF_DEFAULT_TO_PARTY, user_input.get(CONF_DEFAULT_TO_PARTY, "")),
                (CONF_DEFAULT_TO_TAG, user_input.get(CONF_DEFAULT_TO_TAG, "")),
            ):
                if value := value.strip():
                    data[field] = value

            return self.async_create_entry(title=self._name or "WeWork App", data=data)

        schema = vol.Schema(
            {
                vol.Required(CONF_CORP_ID, default=defaults[CONF_CORP_ID]): str,
                vol.Required(CONF_CORP_SECRET, default=defaults[CONF_CORP_SECRET]): str,
                vol.Required(CONF_AGENT_ID, default=defaults[CONF_AGENT_ID]): vol.Coerce(int),
                vol.Optional(CONF_DEFAULT_TO_USER, default=defaults[CONF_DEFAULT_TO_USER]): str,
                vol.Optional(CONF_DEFAULT_TO_PARTY, default=defaults[CONF_DEFAULT_TO_PARTY]): str,
                vol.Optional(CONF_DEFAULT_TO_TAG, default=defaults[CONF_DEFAULT_TO_TAG]): str,
            }
        )

        return self.async_show_form(step_id="app", data_schema=schema, errors=errors)

    async def async_step_bot(self, user_input: dict[str, Any] | None = None) -> config_entries.FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            webhook_key = user_input[CONF_WEBHOOK_KEY].strip()
            await self.async_set_unique_id(f"{ENTRY_TYPE_BOT}_{webhook_key}")
            self._abort_if_unique_id_configured()

            data = {
                CONF_ENTRY_TYPE: ENTRY_TYPE_BOT,
                CONF_WEBHOOK_KEY: webhook_key,
            }

            return self.async_create_entry(title=self._name or "WeWork Robot", data=data)

        schema = vol.Schema({vol.Required(CONF_WEBHOOK_KEY): str})
        return self.async_show_form(step_id="bot", data_schema=schema, errors=errors)

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        return WeWorkNotifyOptionsFlow(config_entry)


class WeWorkNotifyOptionsFlow(config_entries.OptionsFlow):
    """Handle options for WeWork Notify."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> config_entries.FlowResult:
        if self._entry.data.get(CONF_ENTRY_TYPE) != ENTRY_TYPE_APP:
            return self.async_abort(reason="no_app_options")

        current_user = self._entry.options.get(
            CONF_TO_USER, self._entry.data.get(CONF_DEFAULT_TO_USER, "")
        )
        current_party = self._entry.options.get(
            CONF_TO_PARTY, self._entry.data.get(CONF_DEFAULT_TO_PARTY, "")
        )
        current_tag = self._entry.options.get(
            CONF_TO_TAG, self._entry.data.get(CONF_DEFAULT_TO_TAG, "")
        )

        if user_input is not None:
            options = {}
            for field in (CONF_TO_USER, CONF_TO_PARTY, CONF_TO_TAG):
                value = user_input.get(field, "").strip()
                if value:
                    options[field] = value
            return self.async_create_entry(title="", data=options)

        schema = vol.Schema(
            {
                vol.Optional(CONF_TO_USER, default=current_user): str,
                vol.Optional(CONF_TO_PARTY, default=current_party): str,
                vol.Optional(CONF_TO_TAG, default=current_tag): str,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
