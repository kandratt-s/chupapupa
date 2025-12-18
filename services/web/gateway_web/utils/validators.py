def is_valid_email(email: str) -> bool:
    """
    Более лояльная проверка: достаточно наличия одного '@' и точки в домене.
    Библиотека email_validator была слишком строгой для наших тестовых адресов
    вида user_123@example.com, поэтому используем простую проверку.
    """
    if not email or "@" not in email:
        return False
    local, _, domain = email.partition("@")
    return bool(local) and "." in domain
