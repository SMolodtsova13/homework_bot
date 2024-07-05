class UnexpectedStatusCodeException(Exception):
    """Исключение, возникающее при получении неожиданного HTTP-статуса."""
    def __init__(self, status_code):
        self.status_code = status_code
        super().__init__(f'Получен неожиданный статус ответа: {status_code}')
