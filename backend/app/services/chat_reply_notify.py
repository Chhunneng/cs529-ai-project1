import uuid

CHAT_REPLY_CHANNEL_PREFIX = "chat:reply:"


def chat_reply_channel(user_message_id: uuid.UUID) -> str:
    return f"{CHAT_REPLY_CHANNEL_PREFIX}{user_message_id}"
