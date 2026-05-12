# CLAUDE.md — ai-digest

## プロジェクト概要

Slack ワークスペース内の AI 関連メッセージを毎朝自動収集し、前日投稿された記事リンクをまとめて指定チャンネルに投稿する Python スクリプト。

GitHub Actions で毎日 JST 10:00 に自動実行される。

---

## ファイル構成

```
ai-digest/
├── ai_digest.py               # メインスクリプト（収集・整形・投稿）
├── requirements.txt           # 依存パッケージ（requests のみ）
├── .github/
│   └── workflows/
│       └── ai_digest.yml      # GitHub Actions ワークフロー定義
└── README.md                  # プロジェクト説明
```

### ai_digest.py の関数構成

| 関数 | 役割 |
|------|------|
| `get_yesterday_range_jst()` | JST 前日 0:00〜23:59 の Unix タイムスタンプを返す |
| `_get_with_retry()` | 429 レート制限時に `Retry-After` 秒待ってリトライする GET ラッパー |
| `search_messages()` | `search.messages` API でキーワード検索。`on:YYYY-MM-DD` クエリ演算子 + `ts` による二重日付フィルタ |
| `_extract_link()` | メッセージから記事 URL・タイトルを抽出。`attachments` (OGP 展開) を優先し、なければ本文の最初のリンクを使う |
| `extract_articles()` | メッセージ一覧から重複除去しチャンネル別に記事をまとめる |
| `build_message()` | Slack 投稿用の mrkdwn テキストを組み立てる |
| `post_to_slack()` | `chat.postMessage` で投稿（unfurl 無効） |

---

## 環境変数

| 変数名 | 説明 |
|--------|------|
| `SLACK_TOKEN` | Slack User OAuth Token（`xoxp-...`）。`search.messages` を呼ぶためにはユーザートークンが必要（Bot トークンは search API 非対応）。GitHub Actions では Secrets に登録する。 |

---

## 投稿先チャンネル

| 定数 | 値 | チャンネル |
|------|----|-----------|
| `TARGET_CHANNEL_ID` | `C0B3ABK2JKE` | `#ai活用` |

チャンネルを変更する場合は `ai_digest.py` の `TARGET_CHANNEL_ID` を書き換える。

---

## 検索キーワード

`ai_digest.py` の `KEYWORDS` リストで管理している。

```python
KEYWORDS = ["AI", "生成AI", "ChatGPT", "Claude", "Gemini", "LLM", "機械学習"]
```

キーワードを追加・削除する場合はこのリストを編集するだけでよい。  
キーワードが増えると API 呼び出し回数が増えるため、レート制限に注意（キーワード間に 3 秒の sleep あり）。

---

## GitHub Actions スケジュール

```yaml
schedule:
  - cron: "0 1 * * *"   # 毎日 UTC 01:00 = JST 10:00
```

手動実行は GitHub Actions UI の「Run workflow」ボタンから行える（`workflow_dispatch` 対応）。

使用アクション:
- `actions/checkout@v6`（Node.js 24 対応）
- `actions/setup-python@v6`（Node.js 24 対応）

---

## ローカルでの動作確認

```bash
# 依存パッケージをインストール
pip install -r requirements.txt

# Slack トークンをセットして実行
SLACK_TOKEN=xoxp-... python ai_digest.py
```

実行ログの見方:

```
Searching 2026/05/11 (1747062000-1747148399)   # 検索対象日付と Unix 範囲
  keyword: AI                                   # キーワードごとに API 呼び出し
  keyword: 生成AI
  ...
Total raw messages: 42                          # 重複あり・日付フィルタ前の件数
Unique articles: 7                              # 重複除去後の記事数
Posted successfully.
```

---

## よくある修正ポイント

### キーワードを追加する

`ai_digest.py` の `KEYWORDS` リストに追記する。

```python
KEYWORDS = ["AI", "生成AI", "ChatGPT", "Claude", "Gemini", "LLM", "機械学習", "新キーワード"]
```

### 投稿チャンネルを変更する

`TARGET_CHANNEL_ID` をチャンネルの ID（Slack でチャンネルを右クリック→「チャンネル詳細を表示」から確認）に変更する。

### 投稿フォーマットを変更する

`build_message()` を編集する。mrkdwn 記法を使用している。

### タイトル最小文字数を変更する

`MIN_TITLE_LEN = 15` を変更する。短くすると短いテキストのリンクも採用される。

### 実行時刻を変更する

`.github/workflows/ai_digest.yml` の cron 式を変更する（UTC 表記）。

### レート制限が頻発する場合

`main()` の `time.sleep(3)` を増やす。429 エラー時は `Retry-After` ヘッダーの秒数（デフォルト 60 秒）待機してリトライする実装になっている。
