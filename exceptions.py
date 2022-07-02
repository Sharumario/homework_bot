class MessageError(Exception):
    """"Неудачная отправка сообщения."""

    pass

class EndPointError(Exception):
    """"Ошибка доступа к APi Яндекса."""

    pass