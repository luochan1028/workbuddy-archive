#!/bin/bash
# ╔══════════════════════════════════════════════════════════════╗
# ║  x-monitor v2.1 — 增量更新脚本                                ║
# ║  适用于 VPS 上已有旧版本，需要更新代码的场景                     ║
# ╚══════════════════════════════════════════════════════════════╝
#
# 用法 (在 VPS 上):
#   bash /opt/x-monitor/deploy.sh
#
# 或从本地上传并部署:
#   scp x-monitor/*.py x-monitor/*.sh x-monitor/requirements.txt root@IP:/opt/x-monitor/
#   ssh root@IP "bash /opt/x-monitor/deploy.sh"
#
set -e

INSTALL_DIR="/opt/x-monitor"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; }
step()  { echo -e "\n${BLUE}==>${NC} $1"; }

echo -e "${BLUE}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  x-monitor v2.1 — 增量更新                          ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════╝${NC}"

cd "$INSTALL_DIR"

# ═══════════ 1. 备份当前数据库 ═══════════
step "备份数据库..."
if [ -f tweets.db ]; then
    BACKUP_NAME="tweets_backup_$(date +%Y%m%d_%H%M%S).db"
    cp tweets.db "$BACKUP_NAME"
    info "已备份: $BACKUP_NAME ($(du -h tweets.db | cut -f1))"
fi

# ═══════════ 2. 停服务 ═══════════
step "停止服务..."
for svc in x-monitor x-web x-watchdog; do
    if systemctl is-active --quiet "$svc" 2>/dev/null; then
        systemctl stop "$svc"
        info "已停止 $svc"
    fi
done

# ═══════════ 3. 更新依赖 ═══════════
step "更新 Python 依赖..."
if [ -f venv/bin/pip ]; then
    venv/bin/pip install --upgrade pip -q
    venv/bin/pip install -r requirements.txt -q
    info "依赖已更新"
else
    warn "venv 不存在，跳过依赖更新"
fi

# ═══════════ 4. 复制 service 文件 ═══════════
step "更新 systemd 配置..."
for svc in x-monitor x-web x-watchdog; do
    if [ -f "${svc}.service" ]; then
        cp "${svc}.service" /etc/systemd/system/
        info "已更新 ${svc}.service"
    fi
done
systemctl daemon-reload

# ═══════════ 5. 启动服务 ═══════════
step "启动服务..."
for svc in x-monitor x-web x-watchdog; do
    systemctl enable "$svc" 2>/dev/null || true
    systemctl start "$svc"
done

sleep 3

# ═══════════ 6. 状态检查 ═══════════
step "服务状态..."
ALL_OK=true
for svc in x-monitor x-web x-watchdog; do
    STATUS=$(systemctl is-active "$svc" 2>/dev/null || echo "not-found")
    if [ "$STATUS" = "active" ]; then
        info "$svc: active"
    else
        error "$svc: $STATUS"
        echo "  日志: journalctl -u $svc --no-pager -n 5"
        ALL_OK=false
    fi
done

# ═══════════ 7. Web 验证 ═══════════
step "Web 验证..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8080/api/health 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
    info "健康检查 API: OK"
else
    warn "健康检查 API: HTTP $HTTP_CODE"
fi

echo ""
if [ "$ALL_OK" = true ]; then
    echo -e "${GREEN}🎉 更新完成，所有服务运行正常！${NC}"
else
    echo -e "${RED}⚠️ 部分服务异常，请检查日志${NC}"
    exit 1
fi
