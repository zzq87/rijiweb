#!/usr/bin/env bash
# 时光日记 - 树莓派部署脚本
# 在树莓派上运行: bash setup.sh

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

APP_DIR="/home/pi/rijiweb"
APP_USER="pi"
APP_GROUP="pi"

log_info "============================================="
log_info "  时光日记 - 树莓派部署脚本"
log_info "============================================="

# 1. 检查系统依赖
log_info "检查系统依赖..."
sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-pip python3-venv nginx

# 2. 创建日志目录
log_info "创建日志目录..."
sudo mkdir -p /var/log/rijiweb
sudo chown ${APP_USER}:${APP_GROUP} /var/log/rijiweb

# 3. 创建数据目录
log_info "创建数据目录..."
mkdir -p "${APP_DIR}/data" "${APP_DIR}/backups"
chmod 700 "${APP_DIR}/data" "${APP_DIR}/backups"

# 4. 安装 Python 依赖
log_info "安装 Python 依赖..."
cd "${APP_DIR}"
pip install --upgrade pip -q
pip install -r requirements.txt -q

# 5. 配置环境变量
log_info "配置环境变量..."
if [ ! -f "${APP_DIR}/.env" ]; then
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    CSRF_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    ENC_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

    cat > "${APP_DIR}/.env" << EOF
DIARY_ENV=production
DIARY_SECRET_KEY=${SECRET_KEY}
DIARY_CSRF_KEY=${CSRF_KEY}
DIARY_ENC_KEY=${ENC_KEY}
DIARY_DB_URI=sqlite:///data/riji.db
DIARY_SECURE_COOKIE=false
EOF
    chmod 600 "${APP_DIR}/.env"
    log_info ".env 文件已生成，密钥已随机生成。"
    log_warn "请妥善保管 .env 文件中的密钥，丢失后无法解密已有日记！"
else
    log_info ".env 文件已存在，跳过生成。"
fi

# 6. 配置 systemd 服务
log_info "配置 systemd 服务..."
sudo cp "${APP_DIR}/deploy/rijiweb.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable rijiweb
sudo systemctl restart rijiweb

# 7. 配置 nginx
log_info "配置 nginx..."
sudo cp "${APP_DIR}/deploy/nginx-riji.conf" /etc/nginx/sites-available/rijiweb
sudo ln -sf /etc/nginx/sites-available/rijiweb /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl restart nginx

log_info "============================================="
log_info "  部署完成!"
log_info "============================================="
log_info "  访问地址: http://<树莓派IP地址>"
log_info "  默认账号: admin"
log_info "  默认密码: admin123"
log_warn "  请立即登录修改默认密码!"
log_info ""
log_info "  查看服务状态: sudo systemctl status rijiweb"
log_info "  查看日志: sudo journalctl -u rijiweb -f"
log_info "  数据库备份: ls -la ${APP_DIR}/backups/"
