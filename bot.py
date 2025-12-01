import os
import asyncio
import re # <-- 新增：用于解析回复消息中的用户ID

from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram import Update, InputFile
from telegram.constants import ParseMode
from typing import Final, List

# --- 1. 配置常量和环境变量 ---
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
# 匹配格式：【新用户消息】来自 ID: `(\d+)`:
ID_REGEX: Final = r"【新用户消息】来自 ID: `(\d+)`:"


# --- 2. 辅助函数：统一处理媒体转发 ---

async def attempt_forward(bot, message, target_id: int, prefix: str, caption_or_text: str, parse_mode: ParseMode = None) -> bool:
    """Helper function to handle all types of message forwarding."""
    
    # 消息内容（用于 caption 或 text）
    message_content = f"{caption_or_text if caption_or_text else ''}"
    
    # --- 媒体转发逻辑 ---
    if message.photo:
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
        # 补充发送来源信息（语音不支持 caption）
        await bot.send_message(chat_id=target_id, text=prefix, parse_mode=parse_mode)
    elif message.text:
        await bot.send_message(chat_id=target_id, text=f"{prefix} {message_content}", parse_mode=parse_mode)
    else:
        return False # 不支持的消息类型

    return True # 转发成功


# --- 3. 处理器函数 ---

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
        f"你好！机器人已启动。\\n"
        f"你的 Chat ID 是: `{chat_id}`\\n"
        f"请将此 ID 告知管理员进行配置。"
    )
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN_V2)


async def relay_message(update: Update, context):
    """根据发送者，将所有类型的消息转发给管理员或目标用户"""
    
    message = update.message
    incoming_chat_id = message.chat_id
    caption_or_text = message.caption if message.caption else message.text
    
    # ----------------------------------------------------
    # Logic 1A: ADMIN REPLY TO USER MESSAGE (Feature 4: 回复转发)
    # ----------------------------------------------------
    if incoming_chat_id == ADMIN_CHAT_ID and message.reply_to_message:
        
        # 提取管理员回复的消息内容
        replied_content = message.reply_to_message.caption if message.reply_to_message.caption else message.reply_to_message.text
        
        if replied_content:
            # 使用正则表达式匹配原始发送者的 ID
            match = re.search(ID_REGEX, replied_content)
            
            if match:
                original_sender_id = int(match.group(1))
                forward_prefix = "【管理员回复】" 
                
                try:
                    # 精准转发给原始用户
                    is_forwarded = await attempt_forward(context.bot, message, original_sender_id, forward_prefix, caption_or_text)

                    if is_forwarded:
                        await message.reply_text(f"✅ 回复已成功发送给用户 ID: {original_sender_id}。")
                    else:
                        await message.reply_text("⚠️ 无法识别或转发您的回复消息类型。")
                    
                    return # 成功处理回复，退出函数
                
                except Exception as e:
                    await message.reply_text(f"❌ 转发给用户 ID {original_sender_id} 失败。错误: {e}")
                    print(f"❌ 转发给用户 ID {original_sender_id} 失败。错误: {e}")
                    return

    # ----------------------------------------------------
    # Logic 1B: ADMIN BROADCAST (非回复消息，执行广播)
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
                # 使用辅助函数转发
                is_forwarded = await attempt_forward(context.bot, message, target_id, forward_prefix, caption_or_text)
                
                if is_forwarded:
                    success_count += 1
                await asyncio.sleep(0.1) 

            except Exception:
                failure_count += 1
                print(f"❌ 广播到 ID {target_id} 失败。")

        await message.reply_text(
            f"✅ 消息已转发完成：成功 {success_count} 个目标，失败 {failure_count} 个目标。"
        )

    # ----------------------------------------------------
    # Logic 2: USER TO ADMIN (用户消息转发给管理员)
    # ----------------------------------------------------
    else:
        # ⚠️ 待办：在这里检查用户是否被封禁 (Feature 3)
        
        if ADMIN_CHAT_ID < 0:
            await message.reply_text("❌ 抱歉，管理员 ID 未设置或设置错误，消息无法转发。")
            return

        # 转发给 ADMIN
        try:
            # Prefix for admin message (使用 MarkdownV2 格式化 ID)
            forward_text = f"【新用户消息】来自 ID: `{incoming_chat_id}`:\n\n"
            
            # 使用辅助函数转发给管理员，指定 MarkdownV2 格式
            is_forwarded = await attempt_forward(context.bot, message, ADMIN_CHAT_ID, forward_text, caption_or_text, parse_mode=ParseMode.MARKDOWN_V2)
            
            if is_forwarded:
                await message.reply_text("您的消息已转发给管理员，请耐心等待回复。")
            else:
                await message.reply_text("⚠️ 无法转发您的消息类型，请发送文本或常用媒体。")
                
        except Exception as e:
            await message.reply_text(f"❌ 抱歉，管理员 ID 无效或转发失败。错误: {e}")
            print(f"转发给管理员失败: {e}")


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

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.ALL, relay_message))

    print("✅ Bot starting polling...")
    application.run_polling(poll_interval=1.0) 

if __name__ == '__main__':
    main()