"""
Quick script to rename the ai_qualification_reason column to ai_reasoning
"""
import asyncio
from sqlalchemy import text
from app.db.base import AsyncSessionLocal


async def fix_column():
    """Rename the column in the leads table."""
    async with AsyncSessionLocal() as db:
        try:
            # First, let's see what columns exist
            print("Checking current columns...")
            result = await db.execute(text("DESCRIBE leads"))
            columns = result.fetchall()

            print("\nCurrent columns in 'leads' table:")
            has_ai_reasoning = False
            has_ai_qualification_reason = False

            for col in columns:
                col_name = col[0]
                print(f"  - {col_name}")
                if col_name == 'ai_reasoning':
                    has_ai_reasoning = True
                elif col_name == 'ai_qualification_reason':
                    has_ai_qualification_reason = True

            print(f"\nHas 'ai_reasoning': {has_ai_reasoning}")
            print(f"Has 'ai_qualification_reason': {has_ai_qualification_reason}")

            if has_ai_qualification_reason and not has_ai_reasoning:
                # Need to rename
                print("\nRenaming column ai_qualification_reason -> ai_reasoning...")
                await db.execute(text(
                    "ALTER TABLE leads CHANGE COLUMN ai_qualification_reason ai_reasoning TEXT"
                ))
                await db.commit()
                print("✅ Column renamed successfully!")

            elif has_ai_qualification_reason and has_ai_reasoning:
                # Need to drop duplicate
                print("\nDropping duplicate column ai_qualification_reason...")
                await db.execute(text(
                    "ALTER TABLE leads DROP COLUMN ai_qualification_reason"
                ))
                await db.commit()
                print("✅ Duplicate column dropped!")

            elif has_ai_reasoning and not has_ai_qualification_reason:
                print("\n✅ Already using correct column name 'ai_reasoning' - no changes needed!")

            else:
                print("\n⚠️  Neither column found - check your table structure!")

        except Exception as e:
            print(f"\n❌ Error: {e}")
            await db.rollback()


if __name__ == "__main__":
    asyncio.run(fix_column())
