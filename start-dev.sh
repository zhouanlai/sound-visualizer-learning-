#!/usr/bin/env bash
# 一键启动「看得见的声音」前后端开发环境
# 用法: ./start-dev.sh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
BACKEND_PORT="${BACKEND_PORT:-8000}"

# 选择 Python 命令（macOS 通常只有 python3）
PY_CMD="${PYTHON:-}"
if [[ -z "$PY_CMD" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    PY_CMD="python3"
  elif command -v python >/dev/null 2>&1; then
    PY_CMD="python"
  else
    echo "[错误] 未找到 python3/python，请先安装 Python 3.9+" >&2
    exit 1
  fi
fi

cleanup() {
  echo ""
  echo "[信息] 正在停止开发服务..."
  [[ -n "${BACKEND_PID:-}" ]] && kill "$BACKEND_PID" 2>/dev/null || true
  [[ -n "${FRONTEND_PID:-}" ]] && kill "$FRONTEND_PID" 2>/dev/null || true
  wait "${BACKEND_PID:-}" "${FRONTEND_PID:-}" 2>/dev/null || true
  echo "[信息] 已停止"
}
trap cleanup EXIT INT TERM

wait_for_port() {
  local port="$1"
  local name="$2"
  local tries=0
  until curl -s -o /dev/null "http://localhost:${port}/"; do
    tries=$((tries + 1))
    if [[ $tries -gt 30 ]]; then
      echo "[错误] ${name} 启动超时（${port} 端口无响应）" >&2
      return 1
    fi
    sleep 1
  done
  echo "[信息] ${name} 已就绪: http://localhost:${port}"
}

# 启动后端
# 重要: 使用 env -u PYTHONPATH 启动，避免 IDE(如 CodeBuddy) 注入的 Python shim
# 拦截 librosa/numba 的临时文件操作导致接口 500（SystemExit）。
echo "[信息] 启动后端 (${PY_CMD})..."
(cd "$BACKEND_DIR" && exec env -u PYTHONPATH "$PY_CMD" main.py) &
BACKEND_PID=$!

# 启动前端
echo "[信息] 启动前端 (npm run dev)..."
(cd "$ROOT_DIR" && exec npm run dev) &
FRONTEND_PID=$!

# 等待服务就绪
wait_for_port "$BACKEND_PORT" "后端" || true
wait_for_port "$FRONTEND_PORT" "前端" || true

echo ""
echo "======================================================"
echo "  看得见的声音 - 开发环境已启动"
echo "  前端:  http://localhost:${FRONTEND_PORT}"
echo "  后端:  http://localhost:${BACKEND_PORT}  (API 文档 /docs)"
echo "  按 Ctrl+C 停止全部服务"
echo "======================================================"

wait
