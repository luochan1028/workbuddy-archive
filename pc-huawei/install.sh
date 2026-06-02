#!/bin/bash
# ╔══════════════════════════════════════════════════════════════╗
# ║  x-monitor v2.1 — 全球投资情报系统                             ║
# ║  一键安装脚本（适用于首次部署的 VPS）                            ║
# ╚══════════════════════════════════════════════════════════════╝
#
# 用法:
#   1. 把整个 x-monitor 文件夹上传到 VPS: scp -r x-monitor/ root@YOUR_IP:/opt/
#   2. SSH 到 VPS: ssh root@YOUR_IP
#   3. 运行安装: bash /opt/x-monitor/install.sh
#
#   或者一条命令:
#   scp -r x-monitor/ root@YOUR_IP:/opt/ && ssh root@YOUR_IP "bash /opt/x-monitor/install.sh"
#
set -e

INSTALL_DIR="/opt/x-monitor"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

banner() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════╗"
    echo "║     x-monitor v2.1 — 全球投资情报系统               ║"
    echo "║     Global Investment Intelligence Dashboard      ║"
    echo "╚══════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

info()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; }
step()  { echo -e "\n${BLUE}==>${NC} $1"; }

banner

# ═════════════════════════════════════════════════════════════
#  步骤 0: 环境检查
# ═════════════════════════════════════════════════════════════
step "检查运行环境..."

# Python 版本
if command -v python3 &>/dev/null; then
    PY_VER=$(python3 --version 2>&1 | awk '{print $2}')
    PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
    PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)
    if [ "$PY_MAJOR" -ge 3 ] && [ "$PY_MINOR" -ge 8 ]; then
        info "Python $PY_VER ✓"
    else
        error "需要 Python >= 3.8，当前: $PY_VER"
        exit 1
    fi
else
    error "未找到 Python3，请先安装: apt install python3 python3-venv python3-pip"
    exit 1
fi

# 操作系统
if [ -f /etc/os-release ]; then
    . /etc/os-release
    info "OS: $NAME ✓"
else
    warn "无法检测操作系统"
fi

# 磁盘空间
FREE_GB=$(df -BG "$INSTALL_DIR" 2>/dev/null | tail -1 | awk '{print $4}' | sed 's/G//' || echo "0")
if [ "$FREE_GB" -lt 1 ] 2>/dev/null; then
    warn "磁盘空间不足 1GB (当前: ${FREE_GB}GB)"
fi

# systemd
if command -v systemctl &>/dev/null; then
    info "systemd ✓"
else
    error "需要 systemd 来管理服务"
    exit 1
fi

# ═════════════════════════════════════════════════════════════
#  步骤 1: 停旧服务
# ═════════════════════════════════════════════════════════════
step "停旧服务..."
for svc in x-monitor x-web x-watchdog; do
    if systemctl is-active --quiet "$svc" 2>/dev/null; then
        systemctl stop "$svc" 2>/dev/null || true
        info "已停止 $svc"
    fi
done

# ═════════════════════════════════════════════════════════════
#  步骤 2: 创建 Python 虚拟环境
# ═════════════════════════════════════════════════════════════
step "配置 Python 虚拟环境..."

cd "$INSTALL_DIR"

if [ ! -f "venv/bin/python" ]; then
    python3 -m venv venv
    info "虚拟环境已创建"
else
    info "虚拟环境已存在，跳过创建"
fi

# 安装/升级 pip
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip -q

# 安装依赖
info "安装 Python 依赖..."
"$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt" -q

# 验证关键依赖
MISSING=()
for pkg in flask feedparser requests; do
    if ! "$INSTALL_DIR/venv/bin/python" -c "import $pkg" 2>/dev/null; then
        MISSING+=("$pkg")
    fi
done
if [ ${#MISSING[@]} -gt 0 ]; then
    warn "以下包安装可能失败: ${MISSING[*]}"
    warn "尝试单独安装..."
    for pkg in "${MISSING[@]}"; do
        "$INSTALL_DIR/venv/bin/pip" install "$pkg"
    done
fi

info "依赖安装完成"

# 可选：翻译库
if ! "$INSTALL_DIR/venv/bin/python" -c "import deep_translator" 2>/dev/null; then
    info "安装翻译库 (deep-translator)..."
    "$INSTALL_DIR/venv/bin/pip" install deep-translator -q 2>/dev/null || warn "翻译库安装失败，翻译功能不可用"
fi

# ═════════════════════════════════════════════════════════════
#  步骤 3: 安装 systemd 服务
# ═════════════════════════════════════════════════════════════
step "安装 systemd 服务..."

for svc in x-monitor x-web x-watchdog; do
    if [ -f "$INSTALL_DIR/${svc}.service" ]; then
        cp "$INSTALL_DIR/${svc}.service" /etc/systemd/system/
        info "已安装 ${svc}.service"
    else
        warn "${svc}.service 不存在，跳过"
    fi
done

systemctl daemon-reload
info "systemd 配置已重载"

# ═════════════════════════════════════════════════════════════
#  步骤 4: 数据初始化（如果是空数据库）
# ═════════════════════════════════════════════════════════════
step "初始化数据..."

DB_EXISTS=false
DB_HAS_DATA=false
if [ -f "$INSTALL_DIR/tweets.db" ]; then
    DB_EXISTS=true
    TWEET_COUNT=$("$INSTALL_DIR/venv/bin/python" -c "
import sqlite3
conn = sqlite3.connect('$INSTALL_DIR/tweets.db')
count = conn.execute('SELECT count(*) FROM tweets').fetchone()[0]
print(count)
conn.close()
" 2>/dev/null || echo "0")
    if [ "$TWEET_COUNT" -gt 0 ] 2>/dev/null; then
        DB_HAS_DATA=true
        info "数据库已有 $TWEET_COUNT 条推文，跳过种子数据"
    fi
fi

if [ "$DB_HAS_DATA" = false ]; then
    info "填充示例数据..."
    "$INSTALL_DIR/venv/bin/python" "$INSTALL_DIR/seed_data.py" --days 3 2>/dev/null || {
        warn "种子数据生成失败，不影响核心功能（可稍后手动运行 python seed_data.py）"
    }
fi

# ═════════════════════════════════════════════════════════════
#  步骤 5: 数据目录权限
# ═════════════════════════════════════════════════════════════
step "设置权限..."

chown -R root:root "$INSTALL_DIR" 2>/dev/null || true
chmod -R 755 "$INSTALL_DIR" 2>/dev/null || true
# 确保日志文件可写
touch "$INSTALL_DIR/monitor.log" "$INSTALL_DIR/web.log" "$INSTALL_DIR/watchdog.log" 2>/dev/null || true
chmod 644 "$INSTALL_DIR"/*.log 2>/dev/null || true
info "权限已设置"

# ═════════════════════════════════════════════════════════════
#  步骤 6: 启动服务
# ═════════════════════════════════════════════════════════════
step "启动服务..."

for svc in x-monitor x-web x-watchdog; do
    if [ -f "/etc/systemd/system/${svc}.service" ]; then
        systemctl enable "$svc" 2>/dev/null || warn "无法启用 $svc"
        systemctl restart "$svc" 2>/dev/null || warn "无法重启 $svc"
    fi
done

sleep 3

# ═════════════════════════════════════════════════════════════
#  步骤 7: 状态验证
# ═════════════════════════════════════════════════════════════
step "验证服务状态..."

ALL_OK=true
for svc in x-monitor x-web x-watchdog; do
    STATUS=$(systemctl is-active "$svc" 2>/dev/null || echo "not-found")
    if [ "$STATUS" = "active" ]; then
        info "$svc: ${GREEN}active${NC}"
    else
        error "$svc: $STATUS"
        ALL_OK=false
        echo "  日志: journalctl -u $svc --no-pager -n 5"
    fi
done

# ═════════════════════════════════════════════════════════════
#  步骤 8: Web 看板验证
# ═════════════════════════════════════════════════════════════
step "验证 Web 看板..."

sleep 2
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8080/ 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
    info "Web 看板响应正常 (HTTP $HTTP_CODE)"
else
    warn "Web 看板响应异常 (HTTP $HTTP_CODE)，请稍等几秒后刷新"
fi

# API 检查
API_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8080/api/health 2>/dev/null || echo "000")
if [ "$API_CODE" = "200" ]; then
    info "健康检查 API 正常 (HTTP $API_CODE)"
fi

# ═════════════════════════════════════════════════════════════
#  完成
# ═════════════════════════════════════════════════════════════
PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || curl -s ip.sb 2>/dev/null || echo "YOUR_VPS_IP")

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          🎉 安装完成！                            ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BLUE}Web 看板:${NC}  http://${PUBLIC_IP}:8080"
echo -e "  ${BLUE}配置目录:${NC}  $INSTALL_DIR"
echo ""
echo -e "  ${YELLOW}常用命令:${NC}"
echo "    systemctl status x-monitor    # 监控服务状态"
echo "    systemctl status x-web        # Web 服务状态"
echo "    systemctl status x-watchdog   # 守护进程状态"
echo "    journalctl -u x-monitor -f    # 实时日志"
echo "    journalctl -u x-watchdog -f   # 守护日志"
echo "    python seed_data.py --days 7  # 生成更多示例数据"
echo ""
echo -e "  ${YELLOW}微信推送:${NC}"
echo "    配置在 config.json → wechat_push → pushplus_token"
echo "    获取 Token: https://www.pushplus.plus"
echo ""

if [ "$ALL_OK" = false ]; then
    warn "部分服务异常，请检查上述日志"
    exit 1
fi

exit 0
