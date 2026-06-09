# Status: real

from app.repositories.identity.capabilities import UserCapabilityRepository
from app.repositories.identity.profiles import UserProfileRepository
from app.repositories.identity.users import UserRepository

__all__ = ["UserRepository", "UserProfileRepository", "UserCapabilityRepository"]
