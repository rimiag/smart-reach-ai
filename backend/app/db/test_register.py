"""
Test Registration Script

Debug script to test registration without FastAPI.
"""
import asyncio
from app.db.base import AsyncSessionLocal
from app.models.user import User
from app.core.security import get_password_hash
from sqlalchemy import select


async def test_registration():
    """Test user registration."""
    email = "rizwancl@gmail.com"
    password = "123456789"
    name = "rizwan"

    print("Starting registration test...")

    try:
        async with AsyncSessionLocal() as db:
            # Check if user exists
            print("Checking if user exists...")
            result = await db.execute(select(User).where(User.email == email))
            existing_user = result.scalar_one_or_none()

            if existing_user:
                print(f"✅ User already exists: {existing_user}")
            else:
                # Create new user
                print("Creating new user...")
                new_user = User(
                    email=email,
                    password_hash=get_password_hash(password),
                    name=name,
                )

                db.add(new_user)
                await db.commit()
                await db.refresh(new_user)

                print(f"✅ User created successfully: {new_user}")
                print(f"   ID: {new_user.id}")
                print(f"   Email: {new_user.email}")
                print(f"   Name: {new_user.name}")
                print(f"   Role: {new_user.role}")
                print(f"   Active: {new_user.is_active}")

    except Exception as e:
        print(f"❌ Error during registration: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_registration())
