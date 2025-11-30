变量:ADMIN_ID=你的ID  TARGET_IDS=填写您所有目标用户和群组的 ID，用逗号 , 分隔。  

ADMIN_ID	<您个人的 Chat ID>	用于接收用户消息。

TARGET_ID	<您朋友的 Chat ID>	用于接收您的转发消息

TOKEN = os.environ.get("TOKEN", "YOUR_LOCAL_TEST_TOKEN")


🚀 使用 GitHub Actions 构建 Docker 镜像
我们将创建工作流（Workflow），它会在您每次推送代码到 main 分支时自动构建并推送 Docker 镜像。

步骤 1: 创建 GitHub Token (Access Token)
GitHub Actions 需要权限才能将镜像推送到您的 GitHub Packages。

登录 GitHub。

点击 头像 → Settings（设置）。

在左侧导航栏底部选择 Developer settings（开发者设置）。

选择 Personal access tokens（个人访问令牌）→ Tokens (classic)。

点击 Generate new token（生成新令牌）。

Note（注释）： 例如 docker_builder_token

Expiration（过期时间）： 建议选择 90 天或自定义。

Select scopes（选择权限）： 必须勾选以下权限：

write:packages (用于推送镜像)

read:packages (用于拉取镜像，可选但推荐)

workflow (用于触发 Actions，如果需要)

点击 Generate token。

复制生成的令牌。这个令牌只会显示一次！

步骤 2: 将 Token 存储为 GitHub Secret
我们需要将复制的令牌存储在 GitHub 仓库的 Secret 中，以便 Actions 工作流可以安全地访问它。

在您的 GitHub 仓库 telegram-bot-project 页面，点击 Settings（设置）。

在左侧导航栏选择 Security → Secrets → Actions。

点击 New repository secret（新建仓库 Secret）。

Name（名称）： CR_PAT (代表 Container Registry Personal Access Token)

Value（值）： 粘贴您在步骤 1 中复制的令牌。




结果：GitHub Actions 正在为您构建镜像
由于您刚刚推送了包含 docker-build.yml 的代码，GitHub Actions 会自动被触发并开始执行构建任务。

1. 检查构建进度 (Action)
请立即在浏览器中：

登录您的 GitHub 仓库：https://github.com/yehunde/telegram-bot-project

点击顶部的 Actions（操作）标签页。

您应该能看到一个名为 Docker Image CI 的工作流正在运行或已完成。

点击进入该任务，您可以查看 Build and push Docker image 步骤是否成功。

2. 检查镜像结果 (Package)
如果 Actions 成功运行，Docker 镜像将被存储在 GitHub Packages 中。

点击您的 GitHub 头像。

选择 Your profile（您的个人资料）。

点击 Packages（软件包）标签页。

您应该能找到一个名为 telegram-bot-project 的 Docker 镜像。

3. Railway 部署更新
重要提醒：

Railway 正在运行最新的转发代码： 您的 Railway 机器人现在正在运行包含多目标转发逻辑的最新版本。

配置 Chat ID： 您的首要任务仍然是配置 ADMIN_ID 和 TARGET_IDS 变量，以使双向转发功能正常工作。
