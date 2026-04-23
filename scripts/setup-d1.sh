#!/bin/bash
# D1数据库初始化脚本

echo "🗄️  Cloudflare D1 数据库初始化"
echo "=============================="

# 检查wrangler是否安装
if ! command -v wrangler &> /dev/null; then
    echo "❌ wrangler未安装，请先安装: npm install -g wrangler"
    exit 1
fi

# 检查登录状态
wrangler whoami &> /dev/null
if [ $? -ne 0 ]; then
    echo "🔑 请先登录Cloudflare:"
    wrangler login
fi

# 创建D1数据库
echo ""
echo "📦 创建D1数据库 'trendradar-evolution'..."
wrangler d1 create trendradar-evolution

echo ""
echo "✅ 数据库创建完成！"
echo ""
echo "请将以下信息添加到GitHub Secrets:"
echo "  - D1_DATABASE_ID: <上方输出的database_id>"
echo ""
echo "然后运行初始化:"
echo "  python -c \"from evolution.storage_d1 import init_d1_storage; init_d1_storage()\""
