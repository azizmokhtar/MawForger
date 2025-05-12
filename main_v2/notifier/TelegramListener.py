from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import logging
logging.getLogger("httpx").setLevel(logging.WARNING)
class TelegramBotListener:
    def __init__(self, token, symbol_manager):
        self.token = token
        self.symbol_manager = symbol_manager
        self.started = False

    async def start(self):
        if self.started:
            return
        self.started = True

        application = ApplicationBuilder().token(self.token).build()
        application.add_handler(CommandHandler("add", self.add_symbol))
        application.add_handler(CommandHandler("remove", self.remove_symbol))
        application.add_handler(CommandHandler("list", self.list_symbols))
        #application.add_handler(CommandHandler("killswitch", self.kill_switch)) TODO in the future

        print("Telegram bot is running...")

        await application.initialize()
        await application.start()
        await application.updater.start_polling()


    async def add_symbol(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("Usage: /add SYMBOL")
            return

        symbol = context.args[0]
        success = await self.symbol_manager.add_symbol(symbol)
        if success:
            await update.message.reply_text(f"✅ Added symbol: {symbol.upper()}")
        else:
            await update.message.reply_text(f"⚠️ Symbol already exists: {symbol.upper()}")

    async def remove_symbol(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("Usage: /remove SYMBOL")
            return

        symbol = context.args[0]
        success = await self.symbol_manager.remove_symbol(symbol)
        if success:
            await update.message.reply_text(f"🗑️ Removed symbol: {symbol.upper()}")
        else:
            await update.message.reply_text(f"⚠️ Symbol not found: {symbol.upper()}")

    async def list_symbols(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        symbols = await self.symbol_manager.get_active_symbols()
        if symbols:
            await update.message.reply_text("📈 Active Symbols:\n" + "\n".join(symbols))
        else:
            await update.message.reply_text("❌ No active symbols.")


    