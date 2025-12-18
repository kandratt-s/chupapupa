import re
from email_validator import validate_email, EmailNotValidError


def validate_mail(email: str) -> bool:
    try:
        validate_email(email)
        return True
    except EmailNotValidError:
        return False


def validate_password(password: str) -> bool:
    if len(password) < 8:
        return False
    if not re.search(r"[A-Za-z]", password):
        return False
    if not re.search(r"\d", password):
        return False
    if not re.search(r"[!@#$%^&*]", password):
        return False
    return True
