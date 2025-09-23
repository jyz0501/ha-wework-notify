"""Constants for the WeWork Notify integration."""

from __future__ import annotations

DOMAIN = "wework_notify"

CONF_ENTRY_TYPE = "entry_type"
ENTRY_TYPE_APP = "app"
ENTRY_TYPE_BOT = "bot"

CONF_CORP_ID = "corp_id"
CONF_CORP_SECRET = "corp_secret"
CONF_AGENT_ID = "agent_id"
CONF_WEBHOOK_KEY = "webhook_key"

CONF_DEFAULT_TO_USER = "default_to_user"
CONF_DEFAULT_TO_PARTY = "default_to_party"
CONF_DEFAULT_TO_TAG = "default_to_tag"

CONF_ENTRY_ID = "entry_id"
CONF_ENTRY_TITLE = "entry_title"

CONF_MESSAGE = "message"
CONF_MESSAGE_TYPE = "message_type"
CONF_TITLE = "title"
CONF_TO_USER = "to_user"
CONF_TO_PARTY = "to_party"
CONF_TO_TAG = "to_tag"
CONF_IMAGE_MEDIA_ID = "image_media_id"
CONF_IMAGE_BASE64 = "image_base64"
CONF_IMAGE_MD5 = "image_md5"
CONF_MENTIONED_LIST = "mentioned_list"
CONF_MENTIONED_MOBILE_LIST = "mentioned_mobile_list"

MESSAGE_TYPE_TEXT = "text"
MESSAGE_TYPE_MARKDOWN = "markdown"
MESSAGE_TYPE_IMAGE = "image"
SUPPORTED_MESSAGE_TYPES = {MESSAGE_TYPE_TEXT, MESSAGE_TYPE_MARKDOWN, MESSAGE_TYPE_IMAGE}

SERVICE_SEND_MESSAGE = "send_message"

TOKEN_RETRYABLE_ERROR_CODES = {40014, 42001, 40001}

API_BASE_URL = "https://qyapi.weixin.qq.com/cgi-bin"

DEFAULT_TIMEOUT = 10
