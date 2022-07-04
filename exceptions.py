class ServerError(Exception):
    """Ошибка доступа к APi Яндекса."""

    pass


class MessageError(Exception):
    """Ошибка отправки сообщения."""

    pass
