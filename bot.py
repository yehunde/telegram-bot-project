import os
import asyncio
from typing import Final, List
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram import Update
from telegram.constants import ParseMode

# --- 1. 配置常量 ---
TOKEN: Final[str] = os.environ.get("TOKEN", "YOUR_LOCAL_TEST_TOKEN")

try:
    ADMIN_CHAT_ID: Final[int] = int(os.environ.get("ADMIN_ID"))
except (TypeError, ValueError):
    ADMIN_CHAT_ID: Final[int] = -9999999999
    
TARGET_IDS_STR: Final[str] = os.environ.get("TARGET_IDS", "")
TARGET_CHAT_IDS: Final[List[int]] = []
if TARGET_IDS_STR:
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
    
    print(f"--- 捕获 ID ---")
    print(f"User: @{username}")
    print(f"Chat ID: {chat_id}")
    print(f"-----------------")
    
    message = (
        f"你好！机器人已启动。\\n"
        f"你的 Chat ID 是: `{chat_id}`\\n"
        f"请将此 ID 告知管理员进行配置。"
    )
    try:
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN_V2)
    except Exception:
        await update.message.reply_text(f"机器人已启动，你的 Chat ID 是: {chat_id}")


async def relay_message(update: Update, context):
    """精简版：仅转发纯文本消息"""
    
    message = update.message
    incoming_chat_id = message.chat_id
    text_content = message.text
    
    # 仅处理纯文本消息
    if not text_content:
        # 如果不是文本（如图片、视频），直接回复并忽略
        try:
            await message.reply_text("❌ 抱歉，当前仅接受纯文本消息。")
        except Exception:
            pass
        return
    
    # --- 逻辑 1: 管理员发送消息 -> 广播给所有 TARGETS ---
    if incoming_chat_id == ADMIN_CHAT_ID:
        
        if not TARGET_CHAT_IDS:
            await message.reply_text("❌ 转发失败：TARGET_IDS 变量未设置或为空。")
            return
            
        success_count = 0
        failure_count = 0
        forward_prefix = "【管理员消息】" 
        
        for target_id in TARGET_CHAT_IDS:
            try:
                await context.bot.send_message(
                    chat_id=target_id,
                    text=f"{forward_prefix} {text_content}"
                )
                success_count += 1
                await asyncio.sleep(0.1) 
            except Exception:
                failure_count += 1
                print(f"❌ 广播到 ID {target_id} 失败。")

        await message.reply_text(
            f"✅ 消息已转发完成：成功 {success_count} 个目标，失败 {failure_count} 个目标。"
        )

    # --- 逻辑 2: 其他用户发送消息 -> 转发给 ADMIN ---
    else:
        
        if ADMIN_CHAT_ID < 0:
            await message.reply_text("❌ 抱歉，管理员 ID 未设置，消息无法转发。")
            return

        try:
            forward_text = f"【新用户消息】来自 ID: `{incoming_chat_id}`:\n\n"
            
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"{forward_text}{text_content}",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            
            await message.reply_text("您的消息已转发给管理员。")
        except Exception as e:
            await message.reply_text("❌ 转发给管理员失败，请稍后再试。")
            print(f"转发给管理员失败: {e}")


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

    # 过滤器 filters.TEXT 确保只处理文本消息
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, relay_message)) 

    print("✅ Bot starting polling...")
    application.run_polling(poll_interval=1.0) 

if __name__ == '__main__':
    main()