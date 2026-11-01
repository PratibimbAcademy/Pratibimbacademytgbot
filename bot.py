import logging
from datetime import datetime
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ----------------- CONFIGURATION -----------------
TOKEN = "9240859217:AAGBz1BrgeYA-Ksdv8Lb0HKpZOJetIqNxgk"  # यहाँ अपना Bot Token डालें
ADMIN_ID = 8259043568  # यहाँ अपनी Telegram Numeric User ID डालें
# --------------------------------------------------

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


# --- 1. Admin Commands & Post Scheduling ---


async def send_scheduled_media(context: ContextTypes.DEFAULT_TYPE):
    """Schedule किया गया मैसेज/मीडिया ग्रुप में भेजेगा"""
    job = context.job
    chat_id = job.data["chat_id"]
    message = job.data["message"]

    # Original message copy करके ग्रुप में भेजता है (Text, Photo, Video, File, Audio सब)
    await context.bot.copy_message(
        chat_id=chat_id,
        from_chat_id=ADMIN_ID,
        message_id=message.message_id,
    )


async def schedule_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """कमांड: /schedule YYYY-MM-DD HH:MM (Reply करके चलाना है)"""
    if update.effective_user.id != ADMIN_ID:
        return

    if not update.message.reply_to_message:
        await update.message.reply_text(
            "⚠️ कृपया उस मैसेज/मीडिया का Reply करें जिसे आप Schedule करना चाहते हैं!"
        )
        return

    try:
        # टाइम फॉर्मेट पढ़ें (जैसे: 2026-11-02 10:30)
        time_str = " ".join(context.args)
        scheduled_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
        now = datetime.now()

        delay = (scheduled_time - now).total_seconds()
        if delay <= 0:
            await update.message.reply_text(
                "⚠️ टाइम भविष्य (Future) का होना चाहिए!"
            )
            return

        # Target Group ID (यदि कोई ग्रुप ID न दी हो तो उसी चैट का ID लेगा)
        target_chat_id = update.effective_chat.id

        context.job_queue.run_once(
            send_scheduled_media,
            when=delay,
            data={
                "chat_id": target_chat_id,
                "message": update.message.reply_to_message,
            },
        )

        await update.message.reply_text(
            f"✅ पोस्ट सफलतापूर्वक Schedule हो गई है!\n⏰ टाइम: {time_str}"
        )

    except ValueError:
        await update.message.reply_text(
            "⚠️ गलत फॉर्मेट! सही तरीका:\n`/schedule YYYY-MM-DD HH:MM` (जैसे: /schedule 2026-11-02 18:30)",
            parse_mode="Markdown",
        )


# --- 2. Contact & Forward System (Live Support) ---


async def handle_user_dm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """यूज़र बोट में मैसेज भेजेगा तो वह एडमिन के पास जाएगा"""
    if update.effective_chat.type != "private":
        return

    user = update.effective_user
    if user.id == ADMIN_ID:
        return  # एडमिन खुद को मैसेज फॉरवर्ड नहीं करेगा

    header = f"📩 **नया मैसेज आया है!**\n👤 नाम: {user.full_name}\n🆔 ID: `{user.id}`\n\n💬 **मैसेज:**"

    await context.bot.send_message(
        chat_id=ADMIN_ID, text=header, parse_mode="Markdown"
    )
    # यूज़र का मैसेज (Text/Photo/Video/Document) Admin को कॉपी करके भेजता है
    copied_msg = await update.message.copy(chat_id=ADMIN_ID)

    # Admin को आसानी से Reply करने का निर्देश
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"👉 इस मैसेज का उत्तर देने के लिए ऊपर दिए मैसेज का Reply करें या लिखें:\n`/reply {user.id} आपका मैसेज`",
        parse_mode="Markdown",
    )

    await update.message.reply_text(
        "✅ आपका मैसेज एडमिन को भेज दिया गया है। जल्द ही जवाब मिलेगा!"
    )


async def reply_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """एडमिन द्वारा यूज़र को जवाब देने के लिए"""
    if update.effective_user.id != ADMIN_ID:
        return

    # तरीका 1: यदि Admin ने Telegram के Reply feature का उपयोग किया हो
    if update.message.reply_to_message:
        # बोट की मदद से Direct User को Reply भेजना
        try:
            target_user_id = int(context.args[0]) if context.args else None
            text_to_send = " ".join(
                context.args[1:] if target_user_id else context.args
            )

            if not target_user_id:
                await update.message.reply_text(
                    "⚠️ कृपया यूज़र ID दें: `/reply USER_ID आपका मैसेज`",
                    parse_mode="Markdown",
                )
                return

            await context.bot.send_message(
                chat_id=target_user_id, text=text_to_send
            )
            await update.message.reply_text("✅ जवाब यूज़र को भेज दिया गया!")
        except Exception as e:
            await update.message.reply_text(f"❌ मैसेज भेजने में त्रुटि: {e}")
        return

    # तरीका 2: /reply USER_ID मैसेज
    if len(context.args) < 2:
        await update.message.reply_text(
            "⚠️ सही तरीका: `/reply USER_ID आपका मैसेज`", parse_mode="Markdown"
        )
        return

    user_id = context.args[0]
    reply_text = " ".join(context.args[1:])

    try:
        await context.bot.send_message(
            chat_id=user_id, text=f"💬 **Admin का जवाब:**\n{reply_text}"
        )
        await update.message.reply_text("✅ जवाब सफलतापूर्वक भेज दिया गया!")
    except Exception as e:
        await update.message.reply_text(f"❌ मैसेज नहीं भेजा जा सका: {e}")


# --- 3. Group Moderation (Basic Anti-Spam / Filter) ---


async def moderate_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ग्रुप में स्पैम लिंक ब्लॉक करने के लिए (Management)"""
    if not update.message or not update.message.text:
        return

    msg = update.message.text.lower()
    # उदाहरण: यदि कोई अन्य चैनल या स्पैम लिंक शेयर करता है
    if "t.me/" in msg or "http://" in msg or "https://" in msg:
        user = update.effective_user
        if user.id != ADMIN_ID:
            await update.message.delete()
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"⚠️ @{user.username or user.first_name}, ग्रुप में लिंक भेजना सख्त मना है!",
            )


def main():
    app = Application.builder().token(TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("schedule", schedule_cmd))
    app.add_handler(CommandHandler("reply", reply_cmd))

    # DM Support Handler (Personal Chat)
    app.add_handler(
        MessageHandler(filters.ChatType.PRIVATE & ~filters.COMMAND, handle_user_dm)
    )

    # Group Management Handler
    app.add_handler(
        MessageHandler(
            filters.ChatType.GROUPS & ~filters.COMMAND, moderate_group
        )
    )

    print("🤖 Bot started running...")
    app.run_polling()


if __name__ == "__main__":
    main()
