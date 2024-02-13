import asyncio

from project.bot import bot, dp, update_fees
from project.database.database import create_tables


async def main() -> None:
    await create_tables()
    await update_fees()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
