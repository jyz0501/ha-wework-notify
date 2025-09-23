"""API helpers for the WeWork Notify integration."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from aiohttp import ClientError, ClientSession

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    API_BASE_URL,
    CONF_AGENT_ID,
    CONF_CORP_ID,
    CONF_CORP_SECRET,
    CONF_IMAGE_BASE64,
    CONF_IMAGE_MD5,
    CONF_IMAGE_MEDIA_ID,
    CONF_MENTIONED_LIST,
    CONF_MENTIONED_MOBILE_LIST,
    CONF_MESSAGE,
    CONF_MESSAGE_TYPE,
    CONF_TO_PARTY,
    CONF_TO_TAG,
    CONF_TO_USER,
    DEFAULT_TIMEOUT,
    MESSAGE_TYPE_IMAGE,
    MESSAGE_TYPE_MARKDOWN,
    MESSAGE_TYPE_TEXT,
    SUPPORTED_MESSAGE_TYPES,
    TOKEN_RETRYABLE_ERROR_CODES,
)

_LOGGER = logging.getLogger(__name__)


class WeWorkError(HomeAssistantError):
    """Raised when the WeWork API returns an error."""

    def __init__(self, message: str, *, errcode: int | None = None) -> None:
        super().__init__(message)
        self.errcode = errcode


class BaseWeWorkClient:
    """Base class shared by WeWork clients."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self._session: ClientSession | None = None

    @property
    def session(self) -> ClientSession:
        if self._session is None:
            self._session = async_get_clientsession(self._hass, verify_ssl=True)
        return self._session

    async def async_close(self) -> None:
        """No-op for compatibility."""

    async def async_send_message(self, data: dict[str, Any]) -> None:
        raise NotImplementedError


class WeWorkAppClient(BaseWeWorkClient):
    """Client for sending messages via a WeCom custom application."""

    def __init__(
        self,
        hass: HomeAssistant,
        corp_id: str,
        corp_secret: str,
        agent_id: int,
        defaults: dict[str, str | None] | None = None,
    ) -> None:
        super().__init__(hass)
        self._corp_id = corp_id
        self._corp_secret = corp_secret
        self._agent_id = agent_id
        self._token: str | None = None
        self._token_expire_time: float = 0
        self._token_lock = asyncio.Lock()
        self._defaults = defaults or {}

    async def async_send_message(self, data: dict[str, Any]) -> None:
        message_type: str = data.get(CONF_MESSAGE_TYPE, MESSAGE_TYPE_TEXT)
        if message_type not in SUPPORTED_MESSAGE_TYPES:
            raise WeWorkError(f"Unsupported message type: {message_type}")

        payload = await self._build_payload(message_type, data)
        token = await self._ensure_token()
        try:
            await self._do_send(payload, token)
        except WeWorkError as err:
            if err.errcode not in TOKEN_RETRYABLE_ERROR_CODES:
                raise
            _LOGGER.debug("Token invalid, refreshing and retrying: %s", err)
            token = await self._refresh_token(force=True)
            await self._do_send(payload, token)

    async def _do_send(self, payload: dict[str, Any], token: str) -> None:
        url = f"{API_BASE_URL}/message/send"
        try:
            async with self.session.post(
                url,
                params={"access_token": token},
                json=payload,
                timeout=DEFAULT_TIMEOUT,
            ) as resp:
                result = await resp.json()
        except ClientError as err:
            raise WeWorkError(f"Failed to send message: {err}") from err

        errcode = result.get("errcode")
        if errcode:
            errmsg = result.get("errmsg", "unknown error")
            raise WeWorkError(f"Message send failed: {errmsg}", errcode=errcode) from _WeWorkAPIError(errcode, errmsg)

    async def _build_payload(self, message_type: str, data: dict[str, Any]) -> dict[str, Any]:
        message = data.get(CONF_MESSAGE)
        if message_type in {MESSAGE_TYPE_TEXT, MESSAGE_TYPE_MARKDOWN} and not message:
            raise WeWorkError("Message content is required for text or markdown messages")

        to_user = _merge_recipient(data.get(CONF_TO_USER), self._defaults.get(CONF_TO_USER))
        to_party = _merge_recipient(data.get(CONF_TO_PARTY), self._defaults.get(CONF_TO_PARTY))
        to_tag = _merge_recipient(data.get(CONF_TO_TAG), self._defaults.get(CONF_TO_TAG))

        if not any([to_user, to_party, to_tag]):
            raise WeWorkError("At least one recipient must be provided for the application message")

        payload: dict[str, Any] = {
            "agentid": self._agent_id,
            "msgtype": message_type,
            "safe": 0,
        }

        if to_user:
            payload["touser"] = to_user
        if to_party:
            payload["toparty"] = to_party
        if to_tag:
            payload["totag"] = to_tag

        if message_type == MESSAGE_TYPE_TEXT:
            payload[MESSAGE_TYPE_TEXT] = {"content": message}
        elif message_type == MESSAGE_TYPE_MARKDOWN:
            payload[MESSAGE_TYPE_MARKDOWN] = {"content": message}
        elif message_type == MESSAGE_TYPE_IMAGE:
            media_id = data.get(CONF_IMAGE_MEDIA_ID)
            if not media_id:
                raise WeWorkError("image_media_id is required for image messages on applications")
            payload[MESSAGE_TYPE_IMAGE] = {"media_id": media_id}

        return payload

    async def _ensure_token(self) -> str:
        if self._token and time.monotonic() < self._token_expire_time - 30:
            return self._token
        return await self._refresh_token(force=False)

    async def _refresh_token(self, force: bool) -> str:
        async with self._token_lock:
            if self._token and not force and time.monotonic() < self._token_expire_time - 30:
                return self._token

            url = f"{API_BASE_URL}/gettoken"
            try:
                async with self.session.get(
                    url,
                    params={"corpid": self._corp_id, "corpsecret": self._corp_secret},
                    timeout=DEFAULT_TIMEOUT,
                ) as resp:
                    result = await resp.json()
            except ClientError as err:
                raise WeWorkError(f"Failed to refresh token: {err}") from err

            errcode = result.get("errcode")
            if errcode:
                errmsg = result.get("errmsg", "unknown error")
                raise WeWorkError(f"Token refresh failed: {errmsg}", errcode=errcode) from _WeWorkAPIError(errcode, errmsg)

            access_token = result.get("access_token")
            expires_in = result.get("expires_in", 7200)
            if not access_token:
                raise WeWorkError("Missing access_token in token response")

            self._token = access_token
            self._token_expire_time = time.monotonic() + int(expires_in)
            return access_token


class WeWorkBotClient(BaseWeWorkClient):
    """Client for sending messages via a WeCom group robot."""

    def __init__(self, hass: HomeAssistant, webhook_key: str) -> None:
        super().__init__(hass)
        self._webhook_key = webhook_key

    async def async_send_message(self, data: dict[str, Any]) -> None:
        message_type: str = data.get(CONF_MESSAGE_TYPE, MESSAGE_TYPE_TEXT)
        if message_type not in SUPPORTED_MESSAGE_TYPES:
            raise WeWorkError(f"Unsupported message type: {message_type}")

        payload = self._build_payload(message_type, data)
        url = f"{API_BASE_URL}/webhook/send"
        try:
            async with self.session.post(
                url,
                params={"key": self._webhook_key},
                json=payload,
                timeout=DEFAULT_TIMEOUT,
            ) as resp:
                result = await resp.json()
        except ClientError as err:
            raise WeWorkError(f"Failed to send message: {err}") from err

        errcode = result.get("errcode")
        if errcode:
            errmsg = result.get("errmsg", "unknown error")
            raise WeWorkError(f"Message send failed: {errmsg}", errcode=errcode) from _WeWorkAPIError(errcode, errmsg)

    def _build_payload(self, message_type: str, data: dict[str, Any]) -> dict[str, Any]:
        message = data.get(CONF_MESSAGE)
        payload: dict[str, Any]
        if message_type == MESSAGE_TYPE_TEXT:
            if not message:
                raise WeWorkError("Message content is required for text messages")
            item: dict[str, Any] = {"content": message}
            mentioned_list = _split_optional(data.get(CONF_MENTIONED_LIST))
            mentioned_mobile_list = _split_optional(data.get(CONF_MENTIONED_MOBILE_LIST))
            if mentioned_list:
                item["mentioned_list"] = mentioned_list
            if mentioned_mobile_list:
                item["mentioned_mobile_list"] = mentioned_mobile_list
            payload = {"msgtype": message_type, message_type: item}
        elif message_type == MESSAGE_TYPE_MARKDOWN:
            if not message:
                raise WeWorkError("Message content is required for markdown messages")
            payload = {"msgtype": message_type, message_type: {"content": message}}
        elif message_type == MESSAGE_TYPE_IMAGE:
            base64_data = data.get(CONF_IMAGE_BASE64)
            md5_hash = data.get(CONF_IMAGE_MD5)
            if not base64_data or not md5_hash:
                raise WeWorkError("image_base64 and image_md5 are required for image messages on robots")
            payload = {
                "msgtype": message_type,
                message_type: {"base64": base64_data, "md5": md5_hash},
            }
        else:
            raise WeWorkError(f"Unsupported message type: {message_type}")
        return payload


class _WeWorkAPIError(Exception):
    def __init__(self, errcode: int, errmsg: str) -> None:
        self.errcode = errcode
        self.errmsg = errmsg
        super().__init__(f"errcode={errcode}, errmsg={errmsg}")


def _merge_recipient(override: str | None, default: str | None) -> str | None:
    override = override.strip() if isinstance(override, str) else None
    default = default.strip() if isinstance(default, str) else None
    if override and default:
        # WeCom expects recipients separated by '|'. Use unique order preserving merge.
        existing = []
        for part in (override.split("|") + default.split("|")):
            part = part.strip()
            if part and part not in existing:
                existing.append(part)
        return "|".join(existing)
    return override or default


def _split_optional(value: str | None) -> list[str] | None:
    if not value:
        return None
    return [item.strip() for item in value.split("|") if item.strip()]
