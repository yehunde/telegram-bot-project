import os
import asyncio
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram import Update
from telegram.constants import ParseMode
from typing import Final, List

# --- 1. 配置常量和环境变量 ---
TOKEN: Final[str] = os.environ.get("TOKEN", "YOUR_LOCAL_TEST_TOKEN")

# 从环境变量安全读取 ADMIN_ID 和 TARGET_IDS
try:
    ADMIN_CHAT_ID: Final[int] = int(os.environ.get("ADMIN_ID"))
except (TypeError, ValueError):
    ADMIN_CHAT_ID: Final[int] = -9999999999  # 默认值
    
# 读取 TARGET_IDS 字符串并解析为整数列表
TARGET_IDS_STR: Final[str] = os.environ.get("TARGET_IDS", "")
TARGET_CHAT_IDS: Final[List[int]] = []
if TARGET_IDS_STR:
    # 尝试将每个 ID 转换为整数
    for id_str in TARGET_IDS_STR.split(','):
        try:
            TARGET_CHAT_IDS.append(int(id_str.strip()))
        except ValueError:
            print(f"⚠️ 警告：环境变量 TARGET_IDS 中的无效 ID: {id_str}")


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
    # 逻辑 1: 如果消息来自管理员 (ADMIN_CHAT_ID) -> 转发给所有 TARGETS
    if incoming_chat_id == ADMIN_CHAT_ID:
        
        if not TARGET_CHAT_IDS:
            await update.message.reply_text("❌ 转发失败：TARGET_IDS 变量未设置或为空。")
            return
            
        success_count = 0
        failure_count = 0
        
        # 循环转发给列表中的每一个 ID
        for target_id in TARGET_CHAT_IDS:
            try:
                await context.bot.send_message(
                    chat_id=target_id,
                    text=f"【管理员转发】 {text}"
                )
                success_count += 1
                # 为了防止 Telegram API 速率限制，加入微小延迟
                await asyncio.sleep(0.1) 
            except Exception:
                failure_count += 1
                print(f"❌ 转发到 ID {target_id} 失败。")

        await update.message.reply_text(
            f"✅ 消息已转发完成：成功 {success_count} 个目标，失败 {failure_count} 个目标。"
        )

    # 逻辑 2: 如果消息来自其他用户 -> 转发给 ADMIN
    else:
        # 如果是目标 ID 之一发送的消息，也认为是普通用户消息
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


# --- 3. 主函数 ---

def main():
    if TOKEN == "YOUR_LOCAL_TEST_TOKEN":
        print("❌ 错误：TOKEN 环境变量未设置。")
        return
    
    if ADMIN_CHAT_ID < 0:
        print("⚠️ 警告：ADMIN_ID 未在环境变量中正确设置，接收转发功能将受限。")

    try:
        application = Application.builder().token(TOKEN).build()
    except Exception as e:
        print(f"❌ 错误：创建 Application 失败，Token 可能无效。错误信息: {e}")
        return

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, relay_message))

    print("✅ Bot starting polling...")
    application.run_polling(poll_interval=1.0) 

if __name__ == '__main__':
    main()