from fastapi import Depends, FastAPI, HTTPException, status
from models import Role, User
from repositories import RoleRepository, UserRepository
from schemas import RoleCreate, RoleResponse, UserCreate, UserResponse, UserUpdate
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db

app = FastAPI(
    title="Auth Service", description="Authentication and authorization service", version="1.0.0"
)


# ==================== Health Check ====================
@app.get("/health", tags=["health"])
async def health(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    """Check service health."""
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection failed"
        ) from err


# ==================== User Endpoints ====================
@app.post(
    "/users", response_model=UserResponse, tags=["users"], status_code=status.HTTP_201_CREATED
)
async def create_user(user_data: UserCreate, db: AsyncSession = Depends(get_db)) -> UserResponse:
    """Create a new user."""
    repo = UserRepository(db, User)

    # Check if user already exists
    existing_user = await repo.get_by_username(user_data.username)
    if existing_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")

    existing_email = await repo.get_by_email(user_data.email)
    if existing_email:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")

    # TODO: Hash password in production
    user = await repo.create(
        username=user_data.username,
        email=user_data.email,
        password_hash=user_data.password,  # Should be hashed
        first_name=user_data.first_name,
        last_name=user_data.last_name,
    )

    await repo.commit()
    return user


@app.get("/users", response_model=list[UserResponse], tags=["users"])
async def get_users(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
) -> list[User]:
    """Get all users with pagination."""
    repo = UserRepository(db, User)
    users: list[User] = await repo.get_all(skip=skip, limit=limit)
    return users


@app.get("/users/{user_id}", response_model=UserResponse, tags=["users"])
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)) -> UserResponse:
    """Get user by ID."""
    repo = UserRepository(db, User)
    user = await repo.get_by_id(user_id)

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return user


@app.put("/users/{user_id}", response_model=UserResponse, tags=["users"])
async def update_user(
    user_id: int, user_data: UserUpdate, db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """Update user."""
    repo = UserRepository(db, User)

    user = await repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Check if email is already taken
    if user_data.email and user_data.email != user.email:
        existing_email = await repo.get_by_email(user_data.email)
        if existing_email:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")

    update_data = user_data.model_dump(exclude_unset=True)
    updated_user = await repo.update(user_id, **update_data)

    await repo.commit()
    return updated_user


@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["users"])
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)) -> None:
    """Delete user."""
    repo = UserRepository(db, User)

    deleted = await repo.delete(user_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    await repo.commit()


@app.get("/users/search/by-username/{username}", response_model=UserResponse, tags=["users"])
async def get_user_by_username(username: str, db: AsyncSession = Depends(get_db)) -> UserResponse:
    """Get user by username."""
    repo = UserRepository(db, User)
    user = await repo.get_by_username(username)

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return user


@app.get("/users/search/by-email/{email}", response_model=UserResponse, tags=["users"])
async def get_user_by_email(email: str, db: AsyncSession = Depends(get_db)) -> UserResponse:
    """Get user by email."""
    repo = UserRepository(db, User)
    user = await repo.get_by_email(email)

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return user


# ==================== Role Endpoints ====================
@app.post(
    "/roles", response_model=RoleResponse, tags=["roles"], status_code=status.HTTP_201_CREATED
)
async def create_role(role_data: RoleCreate, db: AsyncSession = Depends(get_db)) -> RoleResponse:
    """Create a new role."""
    repo = RoleRepository(db, Role)

    # Check if role already exists
    existing_role = await repo.get_by_name(role_data.name)
    if existing_role:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Role already exists")

    role = await repo.create(name=role_data.name, description=role_data.description)

    await repo.commit()
    return role


@app.get("/roles", response_model=list[RoleResponse], tags=["roles"])
async def get_roles(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
) -> list[Role]:
    """Get all roles with pagination."""
    repo = RoleRepository(db, Role)
    roles: list[Role] = await repo.get_all(skip=skip, limit=limit)
    return roles


@app.get("/roles/{role_id}", response_model=RoleResponse, tags=["roles"])
async def get_role(role_id: int, db: AsyncSession = Depends(get_db)) -> RoleResponse:
    """Get role by ID."""
    repo = RoleRepository(db, Role)
    role = await repo.get_by_id(role_id)

    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    return role


@app.put("/roles/{role_id}", response_model=RoleResponse, tags=["roles"])
async def update_role(
    role_id: int, role_data: RoleCreate, db: AsyncSession = Depends(get_db)
) -> RoleResponse:
    """Update role."""
    repo = RoleRepository(db, Role)

    role = await repo.get_by_id(role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    updated_role = await repo.update(
        role_id, name=role_data.name, description=role_data.description
    )

    await repo.commit()
    return updated_role


@app.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["roles"])
async def delete_role(role_id: int, db: AsyncSession = Depends(get_db)) -> None:
    """Delete role."""
    repo = RoleRepository(db, Role)

    deleted = await repo.delete(role_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    await repo.commit()
