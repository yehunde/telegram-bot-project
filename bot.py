import os
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram import Update
from telegram.constants import ParseMode
from typing import Final

# --- 1. 配置常量和环境变量 ---
TOKEN: Final[str] = os.environ.get("TOKEN", "YOUR_LOCAL_TEST_TOKEN")

# 从环境变量安全读取 ADMIN_ID 和 TARGET_ID
# 确保在 Railway/本地 设置 ADMIN_ID 和 TARGET_ID
try:
    ADMIN_CHAT_ID: Final[int] = int(os.environ.get("ADMIN_ID"))
except (TypeError, ValueError):
    # 如果未设置或设置错误，使用一个不可能的 ID
    ADMIN_CHAT_ID: Final[int] = -9999999999
    
try:
    TARGET_CHAT_ID: Final[int] = int(os.environ.get("TARGET_ID"))
except (TypeError, ValueError):
    # 如果未设置或设置错误，使用一个不可能的 ID
    TARGET_CHAT_ID: Final[int] = -9999999999


# --- 2. 处理器函数 ---

async def start_command(update: Update, context):
    """处理 /start 命令，并打印用户的 Chat ID"""
    chat_id = update.effective_chat.id
    username = update.effective_user.username if update.effective_user.username else "N/A"
    
    # 打印到控制台/Railway日志，用于捕获 ID
    print(f"--- 捕获 ID ---")
    print(f"User: @{username}")
    print(f"Chat ID: {chat_id}")
    print(f"-----------------")
    
    message = (
        f"你好！机器人已启动。\n"
        f"你的 Chat ID 是: `{chat_id}`\n"
        f"请将此 ID 告知管理员进行配置。"
    )
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN_V2)


async def relay_message(update: Update, context):
    """根据发送者，将消息转发给管理员或目标用户"""
    
    incoming_chat_id = update.effective_chat.id
    text = update.message.text
    
    if not text:
        return # 忽略非文本消息

    # ----------------------------------------------------
    # 逻辑 1: 如果消息来自管理员 (ADMIN_CHAT_ID) -> 转发给 TARGET
    if incoming_chat_id == ADMIN_CHAT_ID:
        
        if TARGET_CHAT_ID == ADMIN_CHAT_ID or TARGET_CHAT_ID < 0:
            await update.message.reply_text("❌ 转发失败：目标 ID 无效或未设置。")
            return
            
        # 转发给目标用户
        try:
            await context.bot.send_message(
                chat_id=TARGET_CHAT_ID,
                text=f"【管理员转发】 {text}"
            )
            await update.message.reply_text("✅ 消息已转发给目标用户。")
        except Exception as e:
            # 如果目标用户屏蔽了机器人，可能会触发这个错误
            await update.message.reply_text(f"❌ 转发失败，请检查 TARGET_ID 或目标用户是否已启动机器人。错误: {e}")

    # 逻辑 2: 如果消息来自其他用户 -> 转发给 ADMIN
    else:
        if ADMIN_CHAT_ID < 0:
            await update.message.reply_text("❌ 抱歉，管理员 ID 未设置或设置错误，消息无法转发。")
            return

        # 转发给管理员
        try:
            # 标记消息来源
            forward_text = f"【新用户消息】来自 ID: `{incoming_chat_id}`:\n\n{text}"
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=forward_text,
                parse_mode=ParseMode.MARKDOWN_V2
            )
            # 给发送者一个确认回复
            await update.message.reply_text("您的消息已转发给管理员，请耐心等待回复。")
        except Exception as e:
            await update.message.reply_text(f"❌ 抱歉，管理员 ID 无效或转发失败。错误: {e}")
    # ----------------------------------------------------


# --- 3. 主函数 ---

def main():
    if TOKEN == "YOUR_LOCAL_TEST_TOKEN":
        print("❌ 错误：TOKEN 环境变量未设置。")
        return
    
    if ADMIN_CHAT_ID < 0 or TARGET_CHAT_ID < 0:
        print("⚠️ 警告：ADMIN_ID 或 TARGET_ID 未在环境变量中正确设置，转发功能将受限。")

    try:
        application = Application.builder().token(TOKEN).build()
    except Exception as e:
        print(f"❌ 错误：创建 Application 失败，Token 可能无效。错误信息: {e}")
        return

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, relay_message))

    print("✅ Bot starting polling...")
    application.run_polling(poll_interval=1.0) # 设置轮询间隔

if __name__ == '__main__':
    main()