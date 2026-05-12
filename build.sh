#!/bin/bash
# Render 构建脚本

# 安装后端依赖（确保装到当前虚拟环境）
pip install -r backend/requirements.txt

# 安装前端依赖并构建
cd frontend
npm install
npm run build

# 把前端构建产物复制到后端 static 目录
mkdir -p ../backend/static
cp -r dist/* ../backend/static/

cd ..
