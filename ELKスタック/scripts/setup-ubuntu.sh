#!/bin/bash
# =============================================================================
# ELK スタック予知保全 PoC — Ubuntu 20.x 自動構築スクリプト
# =============================================================================
#
# 使い方:
#   chmod +x scripts/setup-ubuntu.sh
#   sudo ./scripts/setup-ubuntu.sh
#
# 実行内容:
#   1. Docker Engine のインストール（未インストールの場合）
#   2. カーネルパラメータの設定（vm.max_map_count）
#   3. 環境変数ファイルの準備
#   4. コンテナの起動
#   5. kibana_system パスワードの設定
#   6. データ投入の確認
#
# =============================================================================

set -euo pipefail

# --- 色付き出力 ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info()    { echo -e "${BLUE}[INFO]${NC} $*"; }
success() { echo -e "${GREEN}[OK]${NC} $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# --- root チェック ---
if [[ $EUID -ne 0 ]]; then
  error "このスクリプトは root 権限で実行してください: sudo $0"
fi

# 実行ユーザーを取得（sudo 経由の場合は SUDO_USER）
ACTUAL_USER="${SUDO_USER:-$USER}"

# プロジェクトルートを特定（スクリプトの1つ上のディレクトリ）
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

info "プロジェクトディレクトリ: $PROJECT_DIR"

# =============================================================================
# Step 1: Docker Engine のインストール
# =============================================================================
install_docker() {
  if command -v docker &> /dev/null; then
    success "Docker は既にインストールされています: $(docker --version)"
    return
  fi

  info "Docker Engine をインストールしています..."

  # 古いバージョンの削除
  apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true

  # 必要なパッケージ
  apt-get update
  apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

  # GPG キーの追加
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg

  # リポジトリの追加
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
    $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

  # インストール
  apt-get update
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

  # ユーザーを docker グループに追加
  usermod -aG docker "$ACTUAL_USER"

  success "Docker Engine のインストールが完了しました"
}

# =============================================================================
# Step 2: Docker Compose V2 の確認
# =============================================================================
check_compose() {
  if docker compose version &> /dev/null; then
    success "Docker Compose V2 が利用可能です: $(docker compose version --short)"
  else
    error "Docker Compose V2 が見つかりません。docker-compose-plugin をインストールしてください。"
  fi
}

# =============================================================================
# Step 3: カーネルパラメータの設定
# =============================================================================
setup_kernel_params() {
  local current_value
  current_value=$(sysctl -n vm.max_map_count)

  if [[ "$current_value" -ge 262144 ]]; then
    success "vm.max_map_count は既に設定済みです ($current_value)"
    return
  fi

  info "vm.max_map_count を設定しています..."

  # 即時反映
  sysctl -w vm.max_map_count=262144

  # 永続化（重複追加を防止）
  if ! grep -q "vm.max_map_count" /etc/sysctl.conf; then
    echo "vm.max_map_count=262144" >> /etc/sysctl.conf
  fi

  success "vm.max_map_count = 262144 に設定しました"
}

# =============================================================================
# Step 4: 環境変数ファイルの準備
# =============================================================================
setup_env() {
  cd "$PROJECT_DIR"

  if [[ -f .env ]]; then
    success ".env ファイルは既に存在します"
    return
  fi

  if [[ ! -f .env.sample ]]; then
    error ".env.sample が見つかりません。リポジトリが正しくクローンされているか確認してください。"
  fi

  cp .env.sample .env
  chown "$ACTUAL_USER:$ACTUAL_USER" .env
  success ".env ファイルを作成しました（.env.sample からコピー）"
}

# =============================================================================
# Step 5: コンテナの起動
# =============================================================================
start_containers() {
  cd "$PROJECT_DIR"

  info "コンテナを起動しています（初回はイメージのダウンロードに数分かかります）..."
  docker compose up -d

  success "全コンテナを起動しました"
}

# =============================================================================
# Step 6: Elasticsearch の起動待機
# =============================================================================
wait_for_elasticsearch() {
  local max_wait=120
  local interval=5
  local elapsed=0

  info "Elasticsearch の起動を待機しています（最大 ${max_wait} 秒）..."

  while [[ $elapsed -lt $max_wait ]]; do
    if curl -s -u elastic:changeme http://localhost:9200/_cluster/health 2>/dev/null | grep -q '"status"'; then
      success "Elasticsearch が起動しました"
      return
    fi
    sleep $interval
    elapsed=$((elapsed + interval))
    echo -n "."
  done

  echo ""
  error "Elasticsearch の起動がタイムアウトしました。docker compose logs elasticsearch を確認してください。"
}

# =============================================================================
# Step 7: kibana_system パスワードの設定
# =============================================================================
setup_kibana_password() {
  info "kibana_system ユーザーのパスワードを設定しています..."

  # .env からパスワードを読み取る
  local elastic_password kibana_password
  elastic_password=$(grep -E "^ELASTIC_PASSWORD=" "$PROJECT_DIR/.env" | cut -d'=' -f2)
  elastic_password="${elastic_password:-changeme}"
  kibana_password=$(grep -E "^KIBANA_PASSWORD=" "$PROJECT_DIR/.env" | cut -d'=' -f2)
  kibana_password="${kibana_password:-changeme}"

  # セキュリティ初期化の完了を待機（最大60秒）
  info "Elasticsearch セキュリティの初期化を待機しています..."
  local max_wait=60
  local interval=5
  local elapsed=0

  while [[ $elapsed -lt $max_wait ]]; do
    local response
    response=$(curl -s -o /dev/null -w "%{http_code}" \
      -u "elastic:${elastic_password}" \
      "http://localhost:9200/_security/_authenticate" 2>/dev/null)

    if [[ "$response" == "200" ]]; then
      break
    fi
    sleep $interval
    elapsed=$((elapsed + interval))
    echo -n "."
  done

  if [[ $elapsed -ge $max_wait ]]; then
    warn "セキュリティ初期化のタイムアウト。手動で設定してください:"
    warn "  docker exec -it elasticsearch bin/elasticsearch-reset-password -u kibana_system -i"
    return
  fi

  # API でパスワードを変更（対話式を回避）
  # リトライ付き（初期化直後は一時的に失敗する場合がある）
  local retry
  for retry in 1 2 3; do
    response=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
      -u "elastic:${elastic_password}" \
      "http://localhost:9200/_security/user/kibana_system/_password" \
      -H "Content-Type: application/json" \
      -d "{\"password\": \"${kibana_password}\"}")

    if [[ "$response" == "200" ]]; then
      success "kibana_system のパスワードを設定しました"
      break
    fi

    if [[ $retry -lt 3 ]]; then
      info "リトライ中... ($retry/3)"
      sleep 5
    else
      warn "kibana_system のパスワード設定に失敗しました（HTTP $response）。手動で設定してください:"
      warn "  docker exec -it elasticsearch bin/elasticsearch-reset-password -u kibana_system -i"
    fi
  done

  # Kibana を再起動
  info "Kibana を再起動しています..."
  docker compose -f "$PROJECT_DIR/docker-compose.yml" restart kibana
}

# =============================================================================
# Step 8: Kibana の起動待機
# =============================================================================
wait_for_kibana() {
  local max_wait=180
  local interval=5
  local elapsed=0

  info "Kibana の起動を待機しています（最大 ${max_wait} 秒、初回は時間がかかります）..."

  while [[ $elapsed -lt $max_wait ]]; do
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:5601/api/status 2>/dev/null | grep -q "200"; then
      success "Kibana が起動しました"
      return
    fi
    sleep $interval
    elapsed=$((elapsed + interval))
    echo -n "."
  done

  echo ""
  warn "Kibana の起動に時間がかかっています。しばらく待ってから http://localhost:5601 にアクセスしてください。"
}

# =============================================================================
# Step 9: データ投入の確認
# =============================================================================
check_data() {
  info "データ投入状況を確認しています..."

  # Logstash のデータ投入を待機（最大60秒）
  local max_wait=60
  local interval=10
  local elapsed=0

  while [[ $elapsed -lt $max_wait ]]; do
    local count
    count=$(curl -s -u elastic:changeme "http://localhost:9200/sensor-data-*/_count" 2>/dev/null | grep -o '"count":[0-9]*' | cut -d: -f2)

    if [[ -n "$count" && "$count" -gt 0 ]]; then
      success "データ投入完了: ${count} 件"
      return
    fi

    sleep $interval
    elapsed=$((elapsed + interval))
    info "Logstash がデータを投入中... (${elapsed}秒経過)"
  done

  warn "データがまだ投入されていません。Logstash のログを確認してください:"
  warn "  docker compose logs logstash --tail=50"
}

# =============================================================================
# メイン処理
# =============================================================================
main() {
  echo ""
  echo "============================================="
  echo " ELK スタック予知保全 PoC — 自動構築"
  echo " Ubuntu 20.x"
  echo "============================================="
  echo ""

  install_docker
  check_compose
  setup_kernel_params
  setup_env
  start_containers
  wait_for_elasticsearch
  setup_kibana_password
  wait_for_kibana
  check_data

  echo ""
  echo "============================================="
  echo -e " ${GREEN}構築完了${NC}"
  echo "============================================="
  echo ""
  echo " Kibana:         http://localhost:5601"
  echo " Elasticsearch:  http://localhost:9200"
  echo " ユーザー名:     elastic"
  echo " パスワード:     changeme"
  echo ""

  if [[ "$ACTUAL_USER" != "root" ]]; then
    local in_docker_group
    in_docker_group=$(groups "$ACTUAL_USER" 2>/dev/null | grep -c docker)
    if [[ "$in_docker_group" -eq 0 ]] || ! su - "$ACTUAL_USER" -c "docker ps" &>/dev/null; then
      warn "docker グループの変更を反映するため、一度ログアウトして再ログインしてください。"
    fi
  fi

  echo " 次のステップ:"
  echo "   1. ブラウザで http://localhost:5601 にアクセス"
  echo "   2. 01_学習手順.md の Step 2 からスタート"
  echo ""
}

main "$@"
