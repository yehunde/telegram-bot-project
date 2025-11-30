# 使用官方 Python 3.11 极简版作为基础镜像
FROM python:3.11-slim

# 设置容器内的工作目录
WORKDIR /app

# 复制依赖文件并安装依赖 (利用 Docker 缓存)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码到容器中
COPY . .

# 运行机器人主程序
# CMD 将使用 Railway 环境变量 'TOKEN'
CMD ["python", "bot.py"]