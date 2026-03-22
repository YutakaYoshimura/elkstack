## Logstash sincedb_path 設定手順まとめ

---

### 環境
- Windows PowerShell
- Podman でLogstashコンテナを実行

---

### ① 設定ファイルの場所を確認

```powershell
podman exec logstash ls /usr/share/logstash/pipeline/
podman exec logstash ls /etc/logstash/conf.d/
```

見つからない場合：
```powershell
podman exec logstash find / -name "*.conf" 2>/dev/null
```

---

### ② sincedb_path の設定確認

```powershell
podman exec logstash grep -r "sincedb_path" /usr/share/logstash/pipeline/
podman exec logstash grep -r "sincedb_path" /etc/logstash/conf.d/
```

---

### ③ sincedb_path の設定方法

設定ファイル（logstash.conf）に下記を追記：

```ruby
input {
  file {
    path => "/var/log/your-app/*.log"
    start_position => "beginning"
    sincedb_path => "/var/lib/logstash/sincedb/your-app.sincedb"
  }
}
```

---

### ④ sincedb 保存先ディレクトリの作成（root権限が必要）

```powershell
# ディレクトリ作成
podman exec -u root logstash mkdir -p /var/lib/logstash/sincedb

# 権限付与
podman exec -u root logstash chmod 777 /var/lib/logstash/sincedb

# Logstash再起動
podman restart logstash

# ディレクトリ作成確認
podman exec logstash ls -la /var/lib/logstash/
```

---

### ⑤ インデックス登録の確認

```powershell
podman exec logstash curl -X GET "http://localhost:9200/_cat/indices?v"
```

---

### ⑥ トラブルシューティング

**インデックスが登録されない場合**
→ sincedbファイルに古い読み取り位置が残っている可能性があるため、削除してリセット

```powershell
podman exec logstash rm -f /var/lib/logstash/sincedb/your-app.sincedb
podman restart logstash
```

---

### ⑦ 補足：sincedb_path の主な設定値

| 用途 | 設定値 |
|------|--------|
| 通常運用 | `/var/lib/logstash/sincedb/your-app.sincedb` |
| 毎回最初から読む | `/dev/null` |
| テスト・開発用 | `/tmp/sincedb_test` |