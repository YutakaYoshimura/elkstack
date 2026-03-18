# Ubuntu 20.x での ELK スタック構築手順

Ubuntu 20.04 / 20.10 上で Docker Compose を使い、予知保全 PoC 環境を構築する手順。
Windows 版（`01_学習手順.md`）と同じ構成を Ubuntu で再現する。

---

## Docker のライセンスについて

本手順では **Docker Engine (CE)** と **Docker Compose V2** を使用する。いずれも Apache License 2.0 のオープンソースであり、**商用利用に制限はない**。

よく混同される「Docker は商用利用が有料」という話は **Docker Desktop** に関するもの。Docker Desktop と Docker Engine は別製品であり、ライセンスも異なる。

| ツール | ライセンス | 商用利用 | 備考 |
|---|---|---|---|
| **Docker Engine (CE)** | Apache 2.0 | **無料** | 本手順で使用。Ubuntu に直接インストール |
| **Docker Compose V2** | Apache 2.0 | **無料** | 本手順で使用。docker compose コマンド |
| Docker Desktop | Docker Subscription Service Agreement | **有料の場合あり** | 従業員250人以上 or 年間売上$10M以上の企業は有料。本手順では**使用しない** |

> **公式ドキュメントの引用**: "The licensing and distribution terms for Docker and Moby open-source projects, such as Docker Engine, aren't changing."（Docker Engine のライセンスは変更されない）

### 情報ソース

- Docker Desktop ライセンス条件: https://docs.docker.com/subscription/desktop-license/
- Docker Engine (Moby) ライセンス: https://github.com/moby/moby （Apache License 2.0）
- Docker Compose ライセンス: https://github.com/docker/compose （Apache License 2.0）

---

## 前提条件

- Ubuntu 20.04 LTS（または 20.10）
- メモリ **8GB 以上**（推奨 16GB）
- ディスク空き容量 20GB 以上
- root 権限（sudo が使えること）

---

## 自動構築スクリプト（推奨）

以下のスクリプトで Docker のインストールからコンテナ起動・データ投入確認まで一括で実行できる。

```bash
cd ~/learn_elk_stack
chmod +x scripts/setup-ubuntu.sh
sudo ./scripts/setup-ubuntu.sh
```

スクリプトが行う処理:
1. Docker Engine のインストール（未インストールの場合）
2. カーネルパラメータの設定（`vm.max_map_count`）
3. `.env` ファイルの準備
4. 全コンテナの起動
5. `kibana_system` パスワードの自動設定
6. データ投入の確認

完了後、ブラウザで http://localhost:5601 にアクセスし、`01_学習手順.md` の Step 2 から開始する。

> 以下は手動で構築する場合の手順。スクリプトを使った場合は読み飛ばして OK。

---

## Step 0: Docker Engine のインストール

Ubuntu 20.x には Docker Desktop ではなく **Docker Engine** を直接インストールする。

### 0-1. 古いバージョンの削除（存在する場合のみ）

```bash
sudo apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null
```

### 0-2. 必要なパッケージのインストール

```bash
sudo apt-get update
sudo apt-get install -y \
  ca-certificates \
  curl \
  gnupg \
  lsb-release
```

### 0-3. Docker 公式 GPG キーの追加

```bash
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
```

### 0-4. リポジトリの追加

```bash
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```

### 0-5. Docker Engine のインストール

```bash
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

### 0-6. 現在のユーザーを docker グループに追加

```bash
sudo usermod -aG docker $USER
```

> **重要**: グループ変更を反映するため、一度ログアウトして再ログインする。

### 0-7. インストール確認

```bash
docker --version
docker compose version
```

`docker compose version` で `v2.x.x` が表示されれば OK。

---

## Step 1: リポジトリの取得と環境起動

### 1-1. リポジトリのクローン

```bash
cd ~
git clone https://github.com/mizuta0711/learn_elk_stack.git
cd learn_elk_stack
```

> 既にリポジトリがある場合は `git pull` で最新化する。

### 1-2. 環境変数ファイルの準備

```bash
cp .env.sample .env
```

必要に応じてパスワードやメモリ設定を変更する。デフォルト値のまま使用しても問題ない。

**8GB メモリの場合**は `.env` を以下のように変更する:

```ini
ES_MEM_LIMIT=1g
LS_MEM_LIMIT=512m
KIBANA_MEM_LIMIT=512m
```

さらに `docker-compose.yml` の Elasticsearch の JVM ヒープも変更する:

```yaml
- "ES_JAVA_OPTS=-Xms512m -Xmx512m"   # デフォルトの 1g → 512m に変更
```

### 1-3. カーネルパラメータの設定

Elasticsearch はデフォルトで多くのメモリマップ領域を使用するため、カーネルパラメータの変更が必要。

```bash
# 一時的に設定（再起動で消える）
sudo sysctl -w vm.max_map_count=262144

# 永続化（再起動後も有効）
echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf
```

### 1-4. コンテナ起動

```bash
docker compose up -d
```

初回はイメージのダウンロードに時間がかかる（約 2-3GB）。

### 1-5. 起動確認

```bash
# 全コンテナが running であることを確認
docker compose ps

# Elasticsearch の稼働確認（status: green or yellow が返れば OK）
curl -u elastic:changeme http://localhost:9200/_cluster/health?pretty
```

> **うまくいかない場合**: `docker compose logs elasticsearch` でログを確認する。

### 1-6. kibana_system ユーザーのパスワード設定

Kibana が Elasticsearch に接続するために必要な初回設定。

```bash
docker exec -it elasticsearch bin/elasticsearch-reset-password -u kibana_system -i
```

プロンプトが表示されたら、`.env` の `KIBANA_PASSWORD` と同じ値（`changeme`）を入力する。

設定後、Kibana コンテナを再起動する。

```bash
docker compose restart kibana
```

### 1-7. Kibana にアクセス

ブラウザで http://localhost:5601 を開く。

- ユーザー名: `elastic`
- パスワード: `changeme`

> Ubuntu Desktop を使っている場合はそのままブラウザでアクセスできる。Ubuntu Server の場合は、SSH ポートフォワーディング（`ssh -L 5601:localhost:5601 user@server`）を使うか、ファイアウォールで 5601 ポートを開放する。

---

## Step 2: データ投入を確認する

Logstash が `data/sensor_data.csv` を自動的に読み込んで Elasticsearch にインデックスする。

### 2-1. 投入状況の確認

```bash
# データ件数を確認（38,880 件前後になるはず）
curl -u elastic:changeme "http://localhost:9200/sensor-data-*/_count?pretty"
```

### 2-2. データが 0 件の場合

```bash
# Logstash のログを確認
docker compose logs logstash --tail=50

# 再起動して再読み込み
docker compose restart logstash
```

---

## Step 3: ML 異常検知ジョブの作成

Kibana の GUI 操作で異常検知モデルを作成する。手順は Windows 版と同一。

1. 左メニュー → **機械学習** → **異常検知** → **ジョブを作成**
2. データビュー `sensor-data` を選択 → **マルチメトリック** を選択
3. **完全なデータを使用** → 次へ
4. メトリック: `Mean(vibration)`, `Mean(temperature)`, `Mean(current)` を追加
5. 影響: `device_id.keyword`、バケットスパン: `15m`
6. ジョブID: `sensor-anomaly-detection`
7. ジョブを作成

> データビューがまだない場合は、**Stack Management** → **データビュー** から `sensor-data-*` パターンで作成する（タイムスタンプフィールド: `@timestamp`）。

---

## Step 4: Python ML で異常検知（オプション）

独自の ML モデル（LightGBM）による異常検知を実行する。

```bash
# モデル学習
docker exec python-ml python train_model.py

# バッチ推論（結果が prediction-results インデックスに書き込まれる）
docker exec python-ml python batch_inference.py

# 推論結果の件数確認
curl -u elastic:changeme "http://localhost:9200/prediction-results/_count?pretty"
```

---

## Step 5: ダッシュボード作成

Kibana の GUI 操作で行う。手順は Windows 版と同一のため `01_学習手順.md` の Step 5 を参照。

---

## Step 6: ElastAlert2 の動作確認

### 6-1. ログの確認

```bash
docker compose logs -f elastalert
```

### 6-2. アラートルールのテスト

```bash
docker exec elastalert elastalert-test-rule \
  --start "2026-01-01T00:00:00" \
  --end "2026-01-25T00:00:00" \
  /opt/elastalert/rules/anomaly-alert.yaml
```

`Got XXX hits` と表示されれば成功。`realert: 30 minutes` の設定により、30分以内の重複アラートは抑制される。

---

## OS 再起動時の自動起動について

### Docker Engine の自動起動

Docker Engine はインストール時にデフォルトで自動起動が有効になっている。

```bash
# 自動起動の状態確認
sudo systemctl is-enabled docker
# → "enabled" なら OK

# 無効になっていた場合に有効化
sudo systemctl enable docker
```

### コンテナの自動起動

Docker Engine が起動しても、**コンテナは自動では起動しない**（`docker-compose.yml` に `restart` ポリシーが未設定のため）。

OS 再起動後は、以下のコマンドでコンテナを起動する:

```bash
cd ~/learn_elk_stack
docker compose up -d
```

> **常時稼働させたい場合**: `docker-compose.yml` の各サービスに `restart: unless-stopped` を追加すると、OS 再起動時にコンテナも自動起動する。
>
> ```yaml
> services:
>   elasticsearch:
>     restart: unless-stopped
>     ...
>   kibana:
>     restart: unless-stopped
>     ...
> ```
>
> 学習環境では手動起動で十分。本番環境では `restart` ポリシーの設定を推奨。

---

## Step 7: 片付け

```bash
# 一時停止（データ保持）
docker compose down

# 完全削除（データも消す）
docker compose down -v
```

---

## Windows 版との主な違い

| 項目 | Windows | Ubuntu |
|---|---|---|
| Docker | Docker Desktop | Docker Engine |
| シェル | PowerShell | bash |
| curl コマンド | `curl.exe`（PowerShell のエイリアス回避） | `curl`（そのまま使える） |
| vm.max_map_count | `wsl -d docker-desktop sysctl -w ...` | `sudo sysctl -w ...` |
| 改行エスケープ | `` ` ``（バッククォート） | `\`（バックスラッシュ） |
| パス区切り | `\`（バックスラッシュ） | `/`（スラッシュ） |
| Kibana アクセス | ブラウザで直接 | Desktop: 直接 / Server: SSH トンネル |

---

## トラブルシューティング

### Elasticsearch が起動しない

```bash
docker compose logs elasticsearch
```

- `max virtual memory areas vm.max_map_count [65530] is too low`
  → `sudo sysctl -w vm.max_map_count=262144` を実行
- `java.lang.OutOfMemoryError`
  → `.env` の `ES_MEM_LIMIT` を増やす

### docker compose コマンドが見つからない

```bash
# docker-compose（ハイフン版）ではなく docker compose（スペース版）を使用
docker compose version

# v1 がインストールされている場合は Docker Compose V2 プラグインを再インストール
sudo apt-get install -y docker-compose-plugin
```

### パーミッションエラー

```bash
# docker グループに追加されているか確認
groups $USER

# 追加されていない場合
sudo usermod -aG docker $USER
# → ログアウト・再ログイン
```

### Logstash がデータを読み込まない

```bash
docker compose logs logstash --tail=50

# data ディレクトリのパーミッションを確認
ls -la data/
```

### ファイアウォールで Kibana にアクセスできない（Ubuntu Server）

```bash
# UFW を使っている場合
sudo ufw allow 5601/tcp

# または SSH ポートフォワーディングで接続
ssh -L 5601:localhost:5601 user@server-ip
```
