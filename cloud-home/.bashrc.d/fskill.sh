# 找技能 - 在老大指定的 4 个市场里搜索
# 用法: fskill <关键词>
# 例子: fskill mt5
#      fskill obsidian --source official
#      fskill mql5 -l 10
# 简写: fsl mt5

fskill() {
  local query="$1"
  shift
  if [ -z "$query" ]; then
    echo "用法: fskill <关键词> [hermes skills search 的参数]"
    echo "例子: fskill mt5"
    echo "      fskill mql5 --source official"
    echo "      fskill obsidian -l 20"
    return 1
  fi
  hermes skills search "$query" "$@"
}

alias fsl=fskill
alias fsk=fskill
