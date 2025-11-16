import random
import uuid


class IdentityHelper:

    def __init__(self):
        pass

    def uuid(self) -> str:
        """Generate a unique identifier."""
        return str(uuid.uuid4())

    def id(self, min: int = 8, max: int = 12) -> str:
        """Generate a random identifier of variable length."""
        length = random.randint(min, max)
        characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
        return ''.join(random.choices(characters, k=length))
