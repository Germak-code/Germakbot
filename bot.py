import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ContextTypes
)

# ====== CONFIG ======
BOT_TOKEN = "8964168078:AAF8GMy42OfxOoywATPB63T-tj9dMPSOC_I"
BOT_USERNAME = "Germak_bot" # without @
CHANNEL_USERNAME = "@tradewithgermak"
CHANNEL_ID = -1003235461884 # Get from @userinfobot. Bot must be admin in channel

REFERRAL_REWARD = 1.00
TASK_REWARD = 0.50 # Bonus for joining channel
MIN_WITHDRAWAL = 20.00

# ====== TEMP STORAGE ======
# {user_id: {"balance": 0.0, "referrals": [], "referred_by": None, "claimed_tasks": []}}
users = {}

# ====== LOGGING ======
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def get_user(user_id):
    if user_id not in users:
        users[user_id] = {
            "balance": 0.0,
            "referrals": [],
            "referred_by": None,
            "claimed_tasks": [] # to prevent claiming task twice
        }
    return users[user_id]


def main_keyboard():
    keyboard = [
        [InlineKeyboardButton("💰 Check Balance", callback_data="balance")],
        [InlineKeyboardButton("🔗 My Referral Link", callback_data="referral")],
        [InlineKeyboardButton("✅ Tasks", callback_data="tasks")],
        [InlineKeyboardButton("📖 How to Earn", callback_data="earn")],
        [InlineKeyboardButton("💵 Withdraw", callback_data="withdraw")]
    ]
    return InlineKeyboardMarkup(keyboard)


def tasks_keyboard():
    keyboard = [
        [InlineKeyboardButton(f"Join {CHANNEL_USERNAME}", url=f"https://t.me/{CHANNEL_USERNAME.replace('@','')}")],
        [InlineKeyboardButton(f"Verify & Claim ${TASK_REWARD}", callback_data="task_join")],
        [InlineKeyboardButton("⬅️ Back", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)


# ====== COMMANDS ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    args = context.args
    get_user(user_id)

    new_user = len(users[user_id]["referrals"]) == 0 and users[user_id]["balance"] == 0

    # Handle referral
    if args and args[0].startswith("ref_"):
        referrer_id = int(args[0].split("_")[1])
        if referrer_id != user_id and users[user_id]["referred_by"] is None:
            users[user_id]["referred_by"] = referrer_id
            if referrer_id in users:
                users[referrer_id]["balance"] += REFERRAL_REWARD
                users[referrer_id]["referrals"].append(user_id)
                try:
                    await context.bot.send_message(
                        chat_id=referrer_id,
                        text=f"🎉 New Referral Joined!\n+${REFERRAL_REWARD:.2f} has been added to your balance."
                    )
                except Exception as e:
                    logger.error(f"Could not notify referrer {referrer_id}: {e}")

    # Welcome message
    if new_user:
        welcome_text = f"""
👋 Welcome {user.first_name}!

Earn real money with us:
1. **Refer Friends**: Earn ${REFERRAL_REWARD:.2f} for each friend
2. **Complete Tasks**: Earn ${TASK_REWARD:.2f} bonus for joining our channel

Tap a button below to get started 👇
        """
    else:
        welcome_text = f"Welcome back {user.first_name}! Use the menu below."

    await update.message.reply_text(welcome_text, reply_markup=main_keyboard(), parse_mode="Markdown")


# ====== BUTTON HANDLER ======
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_data = get_user(user_id)

    if query.data == "balance":
        text = f"""
💰 **Your Balance**
Current Balance: ${user_data['balance']:.2f}
Total Referrals: {len(user_data['referrals'])}

Minimum for withdrawal: ${MIN_WITHDRAWAL:.2f}
        """
        await query.edit_message_text(text, reply_markup=main_keyboard(), parse_mode="Markdown")

    elif query.data == "referral":
        referral_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"
        text = f"""
🔗 **Your Referral Link**
`{referral_link}`

Share this with friends. 
You get **${REFERRAL_REWARD:.2f}** when they join with your link.
        """
        await query.edit_message_text(text, reply_markup=main_keyboard(), parse_mode="Markdown")

    elif query.data == "tasks":
        task_status = "✅ Claimed" if "join_channel" in user_data["claimed_tasks"] else "❌ Not Claimed"
        text = f"""
✅ **Earn Extra Bonus**

Task 1: Join Our Channel - ${TASK_REWARD:.2f}
Status: {task_status}

Steps:
1. Click "Join Channel" below
2. Join the channel
3. Come back and click "Verify"
        """
        await query.edit_message_text(text, reply_markup=tasks_keyboard(), parse_mode="Markdown")

    elif query.data == "task_join": # VERIFY TASK
        if "join_channel" in user_data["claimed_tasks"]:
            await query.answer("You already claimed this bonus!", show_alert=True)
            return
        
        try:
            # Check if user is member of channel
            member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
            if member.status in ["member", "administrator", "creator"]:
                user_data["balance"] += TASK_REWARD
                user_data["claimed_tasks"].append("join_channel")
                text = f"🎉 Verified!\n+${TASK_REWARD:.2f} bonus added to your balance.\n\nNew Balance: ${user_data['balance']:.2f}"
                await query.edit_message_text(text, reply_markup=main_keyboard())
                logger.info(f"User {user_id} completed task: join_channel")
            else:
                await query.answer("You haven't joined the channel yet. Join and click verify again.", show_alert=True)
        except Exception as e:
            logger.error(f"Error checking membership for {user_id}: {e}")
            await query.answer("Error: Make sure bot is Admin in the channel with 'Ban Users' permission.", show_alert=True)

    elif query.data == "earn":
        text = f"""
📖 **How to Earn Money**

1. **Referrals**: ${REFERRAL_REWARD:.2f} per successful referral
   Share your referral link. When someone starts the bot with your link, you earn instantly.

2. **Tasks**: ${TASK_REWARD:.2f} bonus
   Join our official channel to get the bonus one time.

3. **Withdraw**: ${MIN_WITHDRAWAL:.2f} minimum
   Once you reach ${MIN_WITHDRAWAL:.2f} you can request a withdrawal.
        """
        await query.edit_message_text(text, reply_markup=main_keyboard(), parse_mode="Markdown")

    elif query.data == "withdraw":
        if user_data["balance"] >= MIN_WITHDRAWAL:
            amount = MIN_WITHDRAWAL
            user_data["balance"] -= amount
            text = f"""
✅ **Withdrawal Request Sent**

Amount: ${amount:.2f}
New Balance: ${user_data['balance']:.2f}

An admin will contact you for payment details.
Note: This is demo. Connect to PayPal/Crypto for real payments.
            """
            logger.info(f"Withdrawal request: User {user_id} - ${amount}")
        else:
            needed = MIN_WITHDRAWAL - user_data["balance"]
            text = f"❌ Insufficient Balance\nCurrent: ${user_data['balance']:.2f}\nNeed: ${needed:.2f} more"
        await query.edit_message_text(text, reply_markup=main_keyboard(), parse_mode="Markdown")

    elif query.data == "back":
        await query.edit_message_text("Main Menu:", reply_markup=main_keyboard())


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Exception while handling an update:", exc_info=context.error)


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_error_handler(error_handler)
    logger.info("Bot is running with polling...")
    app.run_polling()


if __name__ == "__main__":
    main()