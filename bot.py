import os
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# 从环境变量中读取 Bot Token。这是部署到 Railway/Docker 的标准和安全做法。
# 如果环境变量 TOKEN 不存在，则使用一个本地占位符（防止泄漏真实 Token）
TOKEN = os.environ.get("TOKEN", "YOUR_LOCAL_TEST_TOKEN") 

async def start(update, context):
    """处理 /start 命令"""
    await update.message.reply_text('你好！机器人已启动。')

async def echo(update, context):
    """处理文本消息，进行复读"""
    # 获取用户发送的文本
    text = update.message.text
    # 回复用户发送的文本
    await update.message.reply_text(f"你发送了: {text}")

def main():
    if TOKEN == "YOUR_LOCAL_TEST_TOKEN":
        print("❌ 错误：TOKEN 环境变量未设置。请在部署前设置 $env:TOKEN 或 Railway 变量。")
        return

    try:
        # 创建 Application
        application = Application.builder().token(TOKEN).build()
    except Exception as e:
        print(f"❌ 错误：创建 Application 失败，可能是 Token 无效。错误信息: {e}")
        return

    # 注册 handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    print("✅ Bot starting polling... (请勿关闭此窗口)")
    # 启动机器人 (使用长轮询)
    application.run_polling()

if __name__ == '__main__':
    main()