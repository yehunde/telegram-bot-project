import os
import asyncio
import re
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

# 正则表达式：用于从管理员回复的消息中提取用户 ID
ID_REGEX: Final = r"【新用户消息】来自 ID: `(\d+)`:"


# --- 2. 辅助函数：统一处理媒体转发 (增强异常处理) ---

async def attempt_forward(bot, message, target_id: int, prefix: str, caption_or_text: str, parse_mode: ParseMode = None) -> (bool, Optional[str]):
    """
    Helper function to handle all types of message forwarding.
    Returns: (is_forwarded: bool, error_message: Optional[str])
    """
    
    # 消息内容（用于 caption 或 text）
    message_content = f"{caption_or_text if caption_or_text else ''}"
    
    try:
        # --- 媒体转发逻辑 ---
        if message.photo:
            # 取最大尺寸图片
            await bot.send_photo(chat_id=target_id, photo=message.photo[-1].file_id, caption=f"{prefix} {message_content}", parse_mode=parse_mode)
        elif message.video:
            await bot.send_video(chat_id=target_id, video=message.video.file_id, caption=f"{prefix} {message_content}", parse_mode=parse_mode)
        elif message.document:
            await bot.send_document(chat_id=target_id, document=message.document.file_id, caption=f"{prefix} {message_content}", parse_mode=parse_mode)
        elif message.audio:
            await bot.send_audio(chat_id=target_id, audio=message.audio.file_id, caption=f"{prefix} {message_content}", parse_mode=parse_mode)
        elif message.voice:
            # 语音消息
            await bot.send_voice(chat_id=target_id, voice=message.voice.file_id)
            await bot.send_message(chat_id=target_id, text=prefix, parse_mode=parse_mode)
        elif message.text:
            await bot.send_message(chat_id=target_id, text=f"{prefix} {message_content}", parse_mode=parse_mode)
        else:
            return False, None # 不支持的消息类型

        return True, None # 转发成功

    except Exception as e:
        # 捕获所有 Telegram API 或其他发送错误
        error_msg = str(e)
        print(f"❌ 转发失败，错误信息: {error_msg}")
        return False, error_msg


# --- 3. 处理器函数 ---

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
    """恢复媒体转发和回复转发逻辑"""
    
    message = update.message
    incoming_chat_id = message.chat_id
    caption_or_text = message.caption if message.caption else message.text
    
    # ----------------------------------------------------
    # Logic 1A: ADMIN REPLY TO USER MESSAGE (Feature 4: 回复转发)
    # ----------------------------------------------------
    if incoming_chat_id == ADMIN_CHAT_ID and message.reply_to_message:
        
        replied_content = message.reply_to_message.caption if message.reply_to_message.caption else message.reply_to_message.text
        
        if replied_content:
            # 使用正则表达式匹配原始发送者的 ID
            match = re.search(ID_REGEX, replied_content)
            
            if match:
                original_sender_id = int(match.group(1))
                forward_prefix = "【管理员回复】" 
                
                # 调用增强的转发函数
                is_forwarded, error_msg = await attempt_forward(context.bot, message, original_sender_id, forward_prefix, caption_or_text)

                if is_forwarded:
                    await message.reply_text(f"✅ 回复已成功发送给用户 ID: {original_sender_id}。")
                else:
                    await message.reply_text(f"❌ 回复转发失败。原因: {error_msg if error_msg else '不支持的消息类型'}")
                
                return

    # ----------------------------------------------------
    # Logic 1B: ADMIN BROADCAST (媒体转发)
    # ----------------------------------------------------
    if incoming_chat_id == ADMIN_CHAT_ID:
        
        if not TARGET_CHAT_IDS:
            await message.reply_text("❌ 转发失败：TARGET_IDS 变量未设置或为空。")
            return
            
        success_count = 0
        failure_count = 0
        forward_prefix = "【管理员广播】" 
        
        # 循环广播给所有 TARGET_IDS
        for target_id in TARGET_CHAT_IDS:
            try:
                # 使用增强的辅助函数转发
                is_forwarded, _ = await attempt_forward(context.bot, message, target_id, forward_prefix, caption_or_text)
                
                if is_forwarded:
                    success_count += 1
                await asyncio.sleep(0.1) 

            except Exception:
                # 这里的异常捕获主要是针对循环本身，而不是 attempt_forward 内部的 API 错误
                failure_count += 1
                print(f"❌ 广播到 ID {target_id} 失败。")

        await message.reply_text(
            f"✅ 消息已转发完成：成功 {success_count} 个目标，失败 {failure_count} 个目标。"
        )

    # ----------------------------------------------------
    # Logic 2: USER TO ADMIN (媒体转发)
    # ----------------------------------------------------
    else:
        
        if ADMIN_CHAT_ID < 0:
            await message.reply_text("❌ 抱歉，管理员 ID 未设置，消息无法转发。")
            return

        # 转发给 ADMIN
        forward_text = f"【新用户消息】来自 ID: `{incoming_chat_id}`:\n\n"
        
        # 调用增强的转发函数
        is_forwarded, error_msg = await attempt_forward(context.bot, message, ADMIN_CHAT_ID, forward_text, caption_or_text, parse_mode=ParseMode.MARKDOWN_V2)
        
        if is_forwarded:
            await message.reply_text("您的消息已转发给管理员，请耐心等待回复。")
        else:
            # 报告详细错误信息给用户（如果存在）
            if error_msg:
                 await message.reply_text(f"❌ 转发失败。原因可能为文件过大或服务器错误。详细错误: {error_msg}")
            else:
                 await message.reply_text("⚠️ 无法转发您的消息类型，请发送文本或常用媒体。")
                

# --- 4. 主函数 ---

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

    # 恢复 filters.ALL 以处理所有消息类型
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, relay_message)) 

    print("✅ Bot starting polling...")
    application.run_polling(poll_interval=1.0) 

if __name__ == '__main__':
    main()