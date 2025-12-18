"""
JWT авторизация для userStatistic сервиса.
Валидирует JWT токены от auth сервиса.
"""

import jwt
from typing import Optional, Dict, Any
from fastapi import Header, HTTPException, status, Depends
from app.core.config import settings


def decode_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """Декодирует JWT токен и возвращает payload"""
    try:
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        if payload.get("type") != "access":
            return None
        return payload
    except Exception:
        return None


def get_current_user_from_jwt(
    authorization: Optional[str] = Header(None, alias="Authorization")
) -> Dict[str, Any]:
    """
    Извлекает пользователя из JWT токена в заголовке Authorization.
    
    Args:
        authorization: Заголовок Authorization с Bearer токеном
        
    Returns:
        Dict с информацией о пользователе
                logging.warning(f"JWT decode: wrong type: {payload.get('type')}")
        
    Raises:
        HTTPException 401: Если токен отсутствует или невалидный
            logging.warning("JWT decode: expired signature")
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация. Отсутствует заголовок Authorization",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный формат Authorization заголовка. Ожидается 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    token = authorization.split(" ")[1]
    payload = decode_jwt_token(token)
    print(f"[DEBUG] JWT payload: {payload}")
    if not payload:
        print("[DEBUG] Invalid or expired token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный или истекший токен",
            headers={"WWW-Authenticate": "Bearer"}
        )
    print(f"[DEBUG] user_id from token: {payload.get('user_id')}")
    return {
        "user_id": payload.get("user_id"),
        "role": payload.get("role", "user"),
        "auth_type": "jwt"
    }


def get_optional_user_from_jwt(
    authorization: Optional[str] = Header(None, alias="Authorization")
) -> Optional[Dict[str, Any]]:
    """
    Извлекает пользователя из JWT токена, но не требует его наличия.
    
    Args:
        authorization: Заголовок Authorization с Bearer токеном
        
    Returns:
        Dict с информацией о пользователе или None если токен отсутствует
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None
    
    token = authorization.split(" ")[1]
    payload = decode_jwt_token(token)
    
    if not payload:
        return None
    
    return {
        "user_id": payload.get("user_id"),
        "role": payload.get("role", "user"),
        "auth_type": "jwt"
    }