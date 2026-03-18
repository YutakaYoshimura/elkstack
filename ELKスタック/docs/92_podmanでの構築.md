# Podman での構築（Windows 11）

Docker Desktop の代わりに **Podman** を使って、同じ ELK スタック環境を構築する手順。

## Docker Desktop との違い

| 項目 | Docker Desktop | Podman |
|---|---|---|
| ライセンス | 大規模企業は有料（従業員250人超 or 年間売上1,000万ドル超） | **完全無料**（Apache 2.0） |
| デーモン | Docker デーモン（常駐プロセス）が必要 | **デーモン不要** |
| 動作環境 | WSL2 または Hyper-V | WSL2 上の Podman Machine |
| GUI | Docker Desktop | Podman Desktop（任意） |
| Compose | docker compose（組み込み） | docker compose + Podman ソケット |

> **Podman を選ぶ理由**: Docker Desktop のライセンス制約を回避したい場合、またはデーモンレスの軽量な構成を好む場合。

---

## 前提条件

- Windows 11（Home / Pro どちらでも可）
- ハードウェア仮想化（VT-x / AMD-V）が BIOS で有効
- ホスト PC のメモリ **8GB 以上**（推奨 16GB）
- ディスク空き容量 20GB 以上

> **8GB PC でも動作可能**。`.env` のメモリ設定を下げる必要がある。詳しくは [01_学習手順.md](01_学習手順.md) の「メモリ要件の詳細」を参照。

---

## Step 1: WSL2 の準備

Podman は Linux カーネルが必要なため、WSL2 上で動作する。

```powershell
# 管理者権限の PowerShell で実行
wsl --install
```

既にインストール済みの場合は、バージョンを確認する。

```powershell
wsl --version
```

> WSL2 がインストールされていない場合、再起動を求められることがある。

---

## Step 2: WSL2 のメモリ設定

ELK スタックは最低 8GB のメモリが必要。WSL2 のデフォルトではメモリが不足する可能性があるため、事前に設定する。

`%USERPROFILE%\.wslconfig` ファイルを作成（または編集）する。

```powershell
# エクスプローラーで開く場合
notepad "$env:USERPROFILE\.wslconfig"
```

以下の内容を記述する:

```ini
[wsl2]
memory=12GB
processors=4
swap=2GB
```

> **memory の目安**: 物理メモリの 75% 程度を割り当てる。16GB PC なら 12GB、32GB PC なら 16GB。

設定を反映するために WSL を再起動する。

```powershell
wsl --shutdown
```

---

## Step 3: Podman のインストール

### 方法 A: CLI のみ（最小構成）

```powershell
winget install -e --id RedHat.Podman
```

### 方法 B: Podman Desktop も一緒に（推奨）

Podman Desktop は Docker Desktop に相当する GUI ツール。コンテナの状態確認やログ閲覧が GUI でできる。

```powershell
winget install -e --id RedHat.Podman
winget install -e --id RedHat.Podman-Desktop
```

> Podman Desktop を使う場合、初回起動時にセットアップウィザードが表示され、Podman Machine の初期化まで GUI でガイドされる。その場合は Step 4 のコマンド実行は不要。

---

## Step 4: Podman Machine の初期化と起動

Podman は WSL2 上の仮想マシン（Podman Machine）の中でコンテナを実行する。

```powershell
# Podman Machine を初期化（WSL2 バックエンドが自動選択される）
podman machine init

# 起動
podman machine start

# 動作確認
podman info
podman run hello-world
```

`Hello from Docker!`（互換メッセージ）が表示されれば成功。

### トラブルシューティング

```powershell
# Machine の状態確認
podman machine list

# 問題がある場合はリセット
podman machine stop
podman machine rm
podman machine init
podman machine start
```

---

## Step 5: Docker Compose のセットアップ

### なぜ Docker Compose を使うのか

Podman で Compose ファイルを扱う方法は3つある:

| 方法 | 概要 | 推奨度 |
|---|---|---|
| **Docker Compose v2 + Podman ソケット** | Docker Compose を Podman の互換 API 経由で使う | **推奨** |
| `podman compose` | Podman の薄いラッパー（上記のどちらかを内部で呼び出す） | 便利 |
| `podman-compose`（Python 製） | Compose ファイルを podman コマンドに変換 | 非推奨（後述） |

**本プロジェクトでは Docker Compose v2 + Podman ソケットを推奨する。**

理由:
- `depends_on: condition: service_healthy` が確実に動作する（podman-compose では不安定）
- `mem_limit` / `deploy.resources` が正しく処理される
- 既存の docker-compose.yml をほぼ無修正で使える

### Docker Compose v2 のインストール

Podman Desktop をインストール済みであれば、Docker Compose は自動的に利用可能になる場合がある。そうでない場合は手動でインストールする。

```powershell
# winget でインストール
winget install -e --id Docker.DockerCompose
```

> Docker Compose v2 はスタンドアロンの CLI ツールとしてインストールでき、Docker Desktop は不要。

### Podman ソケットの有効化

Docker Compose が Podman と通信するために、環境変数を設定する。

```powershell
# 現在のセッションで有効にする
$env:DOCKER_HOST = "npipe:////./pipe/podman-machine-default"

# 永続的に設定する場合（ユーザー環境変数に追加）
[System.Environment]::SetEnvironmentVariable("DOCKER_HOST", "npipe:////./pipe/podman-machine-default", "User")
```

> この設定により、`docker compose` コマンドが Docker デーモンではなく Podman Machine に接続するようになる。

### 動作確認

```powershell
# Docker Compose が Podman 経由で動作することを確認
docker compose version
```

---

## Step 6: レジストリの設定

本プロジェクトで使うコンテナイメージは以下のレジストリから取得する:

| イメージ | レジストリ |
|---|---|
| Elasticsearch, Kibana, Logstash | `docker.elastic.co` |
| ElastAlert2 | `docker.io`（Docker Hub） |

現在の `docker-compose.yml` では完全修飾名（`docker.elastic.co/elasticsearch/...`）で指定しているため、通常は追加設定なしで動作する。

念のため、レジストリ設定を確認・追加しておく:

```powershell
# Podman Machine 内に SSH 接続
podman machine ssh

# registries.conf を確認
cat /etc/containers/registries.conf

# 以下の行がなければ追加
# unqualified-search-registries = ["docker.io", "docker.elastic.co"]
sudo sh -c 'echo '"'"'unqualified-search-registries = ["docker.io", "docker.elastic.co"]'"'"' >> /etc/containers/registries.conf'

# SSH を抜ける
exit
```

### イメージの事前ダウンロード（任意）

Compose で起動する前にイメージを個別にダウンロードしておくと、初回起動がスムーズ。

```powershell
podman pull docker.elastic.co/elasticsearch/elasticsearch:8.17.0
podman pull docker.elastic.co/kibana/kibana:8.17.0
podman pull docker.elastic.co/logstash/logstash:8.17.0
podman pull docker.io/jertel/elastalert2:latest

# ダウンロード確認
podman images
```

---

## Step 7: ELK スタックの起動

ここからは Docker Desktop の場合とほぼ同じ手順。

### 7-1. 環境変数ファイルの準備

```powershell
cd D:\Develop\ELKスタック
copy .env.sample .env
```

### 7-2. コンテナ起動

```powershell
docker compose up -d
```

> `docker compose`（Docker Compose v2）が、`DOCKER_HOST` 環境変数を通じて Podman Machine に接続し、コンテナを起動する。

初回はイメージのダウンロード（Step 6 で未実施の場合）とビルド（python-ml）に時間がかかる。

### 7-3. 起動確認

```powershell
# 全コンテナが running であることを確認
docker compose ps

# Elasticsearch の稼働確認
curl -u elastic:changeme http://localhost:9200/_cluster/health?pretty
```

> **curl がない場合**: PowerShell では `Invoke-RestMethod` を使う。
> ```powershell
> $cred = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("elastic:changeme"))
> Invoke-RestMethod -Uri "http://localhost:9200/_cluster/health?pretty" -Headers @{Authorization="Basic $cred"}
> ```

### 7-4. kibana_system ユーザーのパスワード設定

```powershell
docker exec -it elasticsearch bin/elasticsearch-reset-password -u kibana_system -i
```

プロンプトが表示されたら `changeme` を入力。

> **Podman での注意**: `-it` フラグが Podman でも同様に動作する。`docker exec` は `DOCKER_HOST` 経由で Podman に接続する。

```powershell
docker compose restart kibana
```

### 7-5. Kibana にアクセス

ブラウザで http://localhost:5601 を開く。

- ユーザー名: `elastic`
- パスワード: `changeme`

ここから先は [01_学習手順.md](01_学習手順.md) の **Step 2** 以降と同じ手順で進められる。

---

## Podman 環境でのよく使うコマンド

Docker Desktop の場合と同じコマンドがそのまま使える（`DOCKER_HOST` 設定済みの場合）。

```powershell
# 起動 / 停止
docker compose up -d
docker compose down

# ログ確認
docker compose logs -f elasticsearch

# データ件数確認
curl -u elastic:changeme "http://localhost:9200/sensor-data-*/_count?pretty"

# ML 学習・推論
docker exec python-ml python train_model.py
docker exec python-ml python batch_inference.py

# 完全クリーンアップ
docker compose down -v
```

Podman 固有のコマンド:

```powershell
# Podman Machine の起動 / 停止（毎回の作業開始・終了時）
podman machine start
podman machine stop

# コンテナ一覧（podman コマンドでも確認可能）
podman ps

# リソース使用状況
podman stats
```

---

## Docker Desktop との操作の対応表

| 操作 | Docker Desktop | Podman |
|---|---|---|
| 環境起動 | Docker Desktop を起動 | `podman machine start` |
| 環境停止 | Docker Desktop を終了 | `podman machine stop` |
| コンテナ起動 | `docker compose up -d` | `docker compose up -d`（同じ） |
| コンテナ停止 | `docker compose down` | `docker compose down`（同じ） |
| ログ確認 | `docker compose logs` | `docker compose logs`（同じ） |
| コンテナ内コマンド | `docker exec` | `docker exec`（同じ） |
| GUI でのコンテナ管理 | Docker Desktop の画面 | Podman Desktop の画面 |

> **ポイント**: `DOCKER_HOST` を設定しておけば、日常の `docker compose` コマンドは Docker Desktop の場合と全く同じ。違いは「環境の起動/停止」が Docker Desktop の起動/終了ではなく `podman machine start/stop` になる点だけ。

---

## トラブルシューティング

### Podman Machine が起動しない

```powershell
# 状態確認
podman machine list

# WSL のディストリビューション一覧を確認
wsl --list --verbose

# リセットして再作成
podman machine rm
podman machine init
podman machine start
```

### `docker compose` が接続できない

```
error: unable to connect to Podman
```

```powershell
# DOCKER_HOST が正しく設定されているか確認
echo $env:DOCKER_HOST
# 期待値: npipe:////./pipe/podman-machine-default

# Podman Machine が起動しているか確認
podman machine list
# STATE が "Running" であること

# ソケットパスの確認
podman machine inspect --format "{{.ConnectionInfo.PodmanSocket.Path}}"
```

### Elasticsearch がメモリ不足で起動しない

```powershell
# Podman Machine のメモリを確認
podman machine ssh -- free -h

# メモリが不足している場合は .wslconfig を編集
notepad "$env:USERPROFILE\.wslconfig"

# 編集後、WSL を再起動
wsl --shutdown
podman machine start
```

### イメージが pull できない

```
Error: initializing source ...: reading manifest ...
```

```powershell
# レジストリ設定を確認
podman machine ssh -- cat /etc/containers/registries.conf

# 完全修飾名で直接 pull してみる
podman pull docker.elastic.co/elasticsearch/elasticsearch:8.17.0
```

### コンテナ間の通信ができない

```
Connection refused: elasticsearch:9200
```

```powershell
# ネットワーク一覧を確認
podman network ls

# コンテナが同じネットワークにいるか確認
podman inspect elasticsearch --format '{{.NetworkSettings.Networks}}'
podman inspect kibana --format '{{.NetworkSettings.Networks}}'
```

---

## 補足: podman-compose を使わない理由

`podman-compose`（Python 製）は、以下の理由から本プロジェクトでは非推奨とする:

1. **`depends_on: condition: service_healthy` が不安定** — 依存先のヘルスチェックが完了する前に依存元のコンテナが起動してしまうバグが複数報告されている。本プロジェクトでは Kibana, Logstash, Python ML, ElastAlert2 の全サービスが Elasticsearch の `service_healthy` に依存しているため、この問題は致命的。

2. **`mem_limit` の変換が不完全** — `mem_limit` が `podman run` の `--memory` フラグに正しく変換されないケースがある。

3. **ネットワーキングモデルの違い** — podman-compose はデフォルトで Pod モデルを使い、Docker のブリッジネットワークとは異なる。サービス名での DNS 解決に問題が起きる場合がある。

Docker Compose v2 + Podman ソケットであれば、これらの問題はすべて回避できる。

---

## 補足: docker-compose.yml の Podman 対応改善（任意）

現在の `docker-compose.yml` は Podman + Docker Compose v2 でそのまま動作するが、より互換性を高めるには `mem_limit`（非推奨構文）を `deploy.resources` に書き換える方法がある。

```yaml
# 変更前（Compose 仕様で非推奨）
mem_limit: ${ES_MEM_LIMIT}

# 変更後（推奨）
deploy:
  resources:
    limits:
      memory: ${ES_MEM_LIMIT}
```

ただし、Docker Desktop 環境でも問題なく動作しているため、現時点では変更しなくても構わない。
