class MessageError(Exception):
    """"Неудачная отправка сообщения."""

    pass

class EndPointError(Exception):
    """"Ошибка доступа к APi Яндекса."""

    pass

class EmptyListError(Exception):
    """"Список пуст."""

    pass

class TokenError(Exception):
    """"Ошибка токена"""

    pass