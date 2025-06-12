# =================================================================
# Stage 1: Node.js Builder - 安装 Node.js 依赖
# =================================================================
FROM node:18-slim AS node-builder

# 设置工作目录并拷贝 package.json
WORKDIR /app/nodejs_runtime
COPY package*.json ./

# 设置国内镜像源并安装依赖
RUN npm config set registry https://registry.npmmirror.com && \
    npm ci --loglevel verbose

# =================================================================
# Stage 2: Python Builder - 安装 Python 依赖
# =================================================================
FROM python:3.10-slim AS python-deps

# 安装 Python 依赖
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# =================================================================
# Stage 3: Final Image - 构建最终运行镜像
# =================================================================
FROM python:3.10-slim AS final

WORKDIR /app

# 设置环境变量，让系统和 execjs 能找到 Node.js 相关的模块和可执行文件
# 确保 Node.js 的可执行文件路径在 PATH 的最前面
ENV PATH="/usr/local/bin:/app/nodejs_runtime/node_modules/.bin:${PATH}"
ENV NODE_PATH="/app/nodejs_runtime/node_modules"

# ---- 依赖拷贝 ----
# 从 python-deps 阶段精确拷贝 Python 库和可执行文件（如 uvicorn）
COPY --from=python-deps /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=python-deps /usr/local/bin/ /usr/local/bin/

# 从 node-builder 阶段精确拷贝需要的文件
# 1. 只拷贝 node 的可执行文件，而不是整个 /usr/local
COPY --from=node-builder /usr/local/bin/node /usr/local/bin/
# 2. 拷贝安装好的 node 模块
COPY --from=node-builder /app/nodejs_runtime/node_modules /app/nodejs_runtime/node_modules

# ---- 源码拷贝 ----
# 拷贝项目代码到工作目录
COPY . .

# 暴露端口并启动应用
EXPOSE 8000
CMD ["uvicorn", "main_api:app", "--host", "0.0.0.0", "--port", "8000"]