# task-queue v3 Makefile
# 5 个 target：start / status / review / consume / test
.PHONY: start stop status review consume test help

ROOT     := $(HOME)/.hermes/skills/task-queue
PY       := python
TODAY    := $(shell date +%Y-%m-%d)

help:              ## 显示所有 target
	@echo "task-queue v3 — 主动推进 + 心跳 + 复盘"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

start:             ## 启动 watchdog（后台，60s 扫描）
	$(PY) $(ROOT)/watchdog.py start 60

stop:              ## 停 watchdog
	$(PY) $(ROOT)/watchdog.py stop

status:            ## 看 watchdog 状态 + 活跃任务健康度
	$(PY) $(ROOT)/watchdog.py status

review:            ## 生成今日 review（不推）
	$(PY) $(ROOT)/review.py daily --no-push

consume:           ## 拉所有积压告警并清空
	$(PY) -c "import sys; sys.path.insert(0, '$(ROOT)'); from push import consume_pending; \
import json; \
from datetime import datetime; \
ns = consume_pending(); \
print(f'共 {len(ns)} 条积压通知'); \
[print(f\"  [{n['level']}] {datetime.fromtimestamp(n['at']).strftime('%H:%M:%S')}  {n['msg'][:100]}\") for n in ns]"

test:              ## 跑端到端测试
	$(PY) $(ROOT)/test_task_queue_v3.py
