import os
import asyncio
import re
from typing import Final, List, Optional

# 导入 Telegram Bot 库
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram import Update, ParseMode

# 导入 SQLAlchemy 数据库库
from sqlalchemy import create_engine, Column, Integer, select
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import IntegrityError, OperationalError


# --- 1. 配置常量和数据库初始化 ---

TOKEN: Final[str] = os.environ.get("TOKEN", "YOUR_LOCAL_TEST_TOKEN")
DATABASE_URL: Optional[str] = os.environ.get("DATABASE_URL")

# 全局数据库对象
SessionLocal = None
Base = declarative_base()

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

ID_REGEX: Final = r"【新用户消息】来自 ID: `(\d+)`:"


# --- 2. 数据库模型和工具 ---

class BannedUser(Base):
    """被封禁用户模型"""
    __tablename__ = 'banned_users'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True, nullable=False)

    def __repr__(self):
        return f"<BannedUser(user_id={self.user_id})>"


def init_db(db_url: str):
    """初始化数据库引擎和表"""
    global SessionLocal
    try:
        # Railway 使用 postgres:// 协议，但 SQLAlchemy 需要 postgresql:// 
        db_url = db_url.replace("postgres://", "postgresql://", 1)
        
        engine = create_engine(db_url)
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        print("✅ Database initialized and tables created.")
    except Exception as e:
        # 捕获任何连接或创建错误，并继续运行
        print(f"❌ 数据库初始化失败，封禁功能将禁用。错误: {e}")
        SessionLocal = None


def is_user_banned(user_id: int) -> bool:
    """检查用户是否被封禁"""
    if SessionLocal is None:
        return False
        
    session = SessionLocal()
    try:
        stmt = select(BannedUser).where(BannedUser.user_id == user_id)
        result = session.execute(stmt).scalar_one_or_none()
        return result is not None
    except OperationalError as e:
        # 如果数据库在运行时断开，捕获此错误
        print(f"⚠️ 数据库运行时错误，暂时跳过封禁检查: {e}")
        return False
    finally:
        session.close()


# --- 3. 辅助函数：统一处理媒体转发 ---

async def attempt_forward(bot, message, target_id: int, prefix: str, caption_or_text: str, parse_mode: ParseMode = None) -> bool:
    """Helper function to handle all types of message forwarding."""
    
    message_content = f"{caption_or_text if caption_or_text else ''}"
    
    # --- 媒体转发逻辑 (保持不变) ---
    if message.photo:
        await bot.send_photo(chat_id=target_id, photo=message.photo[-1].file_id, caption=f"{prefix} {message_content}", parse_mode=parse_mode)
    elif message.video:
        await bot.send_video(chat_id=target_id, video=message.video.file_id, caption=f"{prefix} {message_content}", parse_mode=parse_mode)
    elif message.document:
        await bot.send_document(chat_id=target_id, document=message.document.file_id, caption=f"{prefix} {message_content}", parse_mode=parse_mode)
    elif message.audio:
        await bot.send_audio(chat_id=target_id, audio=message.audio.file_id, caption=f"{prefix} {message_content}", parse_mode=parse_mode)
    elif message.voice:
        await bot.send_voice(chat_id=target_id, voice=message.voice.file_id)
        await bot.send_message(chat_id=target_id, text=prefix, parse_mode=parse_mode)
    elif message.text:
        await bot.send_message(chat_id=target_id, text=f"{prefix} {message_content}", parse_mode=parse_mode)
    else:
        return False 

    return True


# --- 4. 封禁管理命令 ---

async def ban_user(update: Update, context):
    """管理员命令：/ban <user_id>"""
    if update.effective_chat.id != ADMIN_CHAT_ID:
        return 

    if SessionLocal is None:
        await update.message.reply_text("❌ 封禁功能禁用：数据库未连接或初始化失败。")
        return

    if not context.args:
        await update.message.reply_text("用法: /ban <用户ID>")
        return

    # ... (封禁逻辑保持不变) ...
    try:
        user_id_to_ban = int(context.args[0])
    except ValueError:
        await update.message.reply_text("错误: ID 必须是整数。")
        return

    session = SessionLocal()
    try:
        new_banned_user = BannedUser(user_id=user_id_to_ban)
        session.add(new_banned_user)
        session.commit()
        await update.message.reply_text(f"✅ 用户 ID {user_id_to_ban} 已成功封禁。")
    except IntegrityError:
        session.rollback()
        await update.message.reply_text(f"⚠️ 用户 ID {user_id_to_ban} 已经在封禁列表中。")
    except Exception as e:
        await update.message.reply_text(f"❌ 封禁失败：{e}")
    finally:
        session.close()


async def unban_user(update: Update, context):
    """管理员命令：/unban <user_id>"""
    if update.effective_chat.id != ADMIN_CHAT_ID:
        return 
        
    if SessionLocal is None:
        await update.message.reply_text("❌ 解封功能禁用：数据库未连接或初始化失败。")
        return

    if not context.args:
        await update.message.reply_text("用法: /unban <用户ID>")
        return

    # ... (解禁逻辑保持不变) ...
    try:
        user_id_to_unban = int(context.args[0])
    except ValueError:
        await update.message.reply_text("错误: ID 必须是整数。")
        return

    session = SessionLocal()
    try:
        stmt = select(BannedUser).where(BannedUser.user_id == user_id_to_unban)
        user_to_delete = session.execute(stmt).scalar_one_or_none()
        
        if user_to_delete:
            session.delete(user_to_delete)
            session.commit()
            await update.message.reply_text(f"✅ 用户 ID {user_id_to_unban} 已解除封禁。")
        else:
            await update.message.reply_text(f"⚠️ 用户 ID {user_id_to_unban} 不在封禁列表中。")
    except Exception as e:
        await update.message.reply_text(f"❌ 解除封禁失败：{e}")
    finally:
        session.close()


# --- 5. 核心消息转发处理器 ---

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
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN_V2)


async def relay_message(update: Update, context):
    """根据发送者，将所有类型的消息转发给管理员或目标用户"""
    
    message = update.message
    incoming_chat_id = message.chat_id
    caption_or_text = message.caption if message.caption else message.text
    
    # ----------------------------------------------------
    # Logic 2 Check: 封禁用户检查 (Feature 3)
    # ----------------------------------------------------
    # 仅当数据库Session Local存在时才执行检查
    if SessionLocal is not None and incoming_chat_id != ADMIN_CHAT_ID and is_user_banned(incoming_chat_id):
        await message.reply_text("❌ 您的消息无法发送，您已被管理员禁止使用本服务。")
        return

    # ... (下方逻辑保持不变) ...
    
    # ----------------------------------------------------
    # Logic 1A: ADMIN REPLY TO USER MESSAGE (Feature 4)
    # ----------------------------------------------------
    if incoming_chat_id == ADMIN_CHAT_ID and message.reply_to_message:
        
        replied_content = message.reply_to_message.caption if message.reply_to_message.caption else message.reply_to_message.text
        
        if replied_content:
            match = re.search(ID_REGEX, replied_content)
            
            if match:
                original_sender_id = int(match.group(1))
                forward_prefix = "【管理员回复】" 
                
                try:
                    is_forwarded = await attempt_forward(context.bot, message, original_sender_id, forward_prefix, caption_or_text, parse_mode=None)

                    if is_forwarded:
                        await message.reply_text(f"✅ 回复已成功发送给用户 ID: {original_sender_id}。")
                    else:
                        await message.reply_text("⚠️ 无法识别或转发您的回复消息类型。")
                    
                    return 
                
                except Exception as e:
                    await message.reply_text(f"❌ 转发给用户 ID {original_sender_id} 失败。错误: {e}")
                    print(f"❌ 转发给用户 ID {original_sender_id} 失败。错误: {e}")
                    return

    # ----------------------------------------------------
    # Logic 1B: ADMIN BROADCAST
    # ----------------------------------------------------
    if incoming_chat_id == ADMIN_CHAT_ID:
        
        if not TARGET_CHAT_IDS:
            await message.reply_text("❌ 转发失败：TARGET_IDS 变量未设置或为空。")
            return
            
        success_count = 0
        failure_count = 0
        forward_prefix = "【管理员广播】" 
        
        for target_id in TARGET_CHAT_IDS:
            try:
                is_forwarded = await attempt_forward(context.bot, message, target_id, forward_prefix, caption_or_text, parse_mode=None)
                
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
    # Logic 2: USER TO ADMIN
    # ----------------------------------------------------
    else:
        
        if ADMIN_CHAT_ID < 0:
            await message.reply_text("❌ 抱歉，管理员 ID 未设置或设置错误，消息无法转发。")
            return

        # 转发给 ADMIN
        try:
            forward_text = f"【新用户消息】来自 ID: `{incoming_chat_id}`:\n\n"
            
            is_forwarded = await attempt_forward(context.bot, message, ADMIN_CHAT_ID, forward_text, caption_or_text, parse_mode=ParseMode.MARKDOWN_V2)
            
            if is_forwarded:
                await message.reply_text("您的消息已转发给管理员，请耐心等待回复。")
            else:
                await message.reply_text("⚠️ 无法转发您的消息类型，请发送文本或常用媒体。")
                
        except Exception as e:
            await message.reply_text(f"❌ 抱歉，管理员 ID 无效或转发失败。错误: {e}")
            print(f"转发给管理员失败: {e}")


# --- 6. 主函数 ---

def main():
    if TOKEN == "YOUR_LOCAL_TEST_TOKEN":
        print("❌ 错误：TOKEN 环境变量未设置。")
        return
        
    if DATABASE_URL:
        init_db(DATABASE_URL) # 初始化数据库
    else:
        print("⚠️ 警告：DATABASE_URL 环境变量缺失，封禁功能将禁用。")

    if ADMIN_CHAT_ID < 0:
        print("⚠️ 警告：ADMIN_ID 未在环境变量中正确设置，接收转发功能将受限。")

    try:
        application = Application.builder().token(TOKEN).build()
    except Exception as e:
        print(f"❌ 错误：创建 Application 失败，Token 可能无效。错误信息: {e}")
        return

    # 消息处理器
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("ban", ban_user))
    application.add_handler(CommandHandler("unban", unban_user))
    application.add_handler(MessageHandler(filters.ALL, relay_message))

    print("✅ Bot starting polling...")
    application.run_polling(poll_interval=1.0) 

if __name__ == '__main__':
    main()