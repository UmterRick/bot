def set_hook():
    import asyncio
    from main import bot_config, webhook_config
    from aiogram import Bot

    bot = Bot(token=bot_config['TOKEN'])

    async def hook_set():
        WEBHOOK_URL = webhook_config.get("url", "") + bot_config["TOKEN"]
        await bot.set_webhook(WEBHOOK_URL)
        print(await bot.get_webhook_info())

    asyncio.run(hook_set())
    bot.close()

def start():
    from main import start_bot
    start_bot()