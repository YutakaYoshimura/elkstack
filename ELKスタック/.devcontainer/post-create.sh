#!/bin/bash
set -e

echo "=== ELK Stack 初期化開始 ==="

# .env ファイルが無ければサンプルからコピー
if [ ! -f .env ]; then
  cp .env.sample .env
  echo ".env ファイルを作成しました"
fi

# 環境変数読み込み
source .env

# Docker Compose でサービス起動
echo "コンテナを起動中..."
docker compose up -d

# Elasticsearch の起動を待機
echo "Elasticsearch の起動を待機中..."
until curl -s -u "elastic:${ELASTIC_PASSWORD}" \
  http://localhost:9200/_cluster/health 2>/dev/null | grep -q '"status"'; do
  echo "  まだ起動中..."
  sleep 5
done
echo "Elasticsearch が起動しました"

# kibana_system ユーザーのパスワード設定
echo "kibana_system パスワードを設定中..."
curl -s -X POST \
  -u "elastic:${ELASTIC_PASSWORD}" \
  -H "Content-Type: application/json" \
  "http://localhost:9200/_security/user/kibana_system/_password" \
  -d "{\"password\":\"${KIBANA_PASSWORD}\"}"
echo ""
echo "kibana_system パスワード設定完了"

# Kibana の起動を待機
echo "Kibana の起動を待機中..."
until curl -s -o /dev/null -w "%{http_code}" http://localhost:5601/api/status 2>/dev/null | grep -q "200"; do
  echo "  まだ起動中..."
  sleep 10
done
echo "Kibana が起動しました"

echo ""
echo "=== ELK Stack 初期化完了 ==="
echo "  Elasticsearch: http://localhost:9200"
echo "  Kibana:        http://localhost:5601"
echo "  認証情報:      elastic / ${ELASTIC_PASSWORD}"
