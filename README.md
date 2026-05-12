# AI Digest

毎朝10時（JST）に前日のAI関連記事をSlackから収集し、#ai活用 チャンネルにまとめて投稿するBot。  
外部AIサービスは使わず、**Slack APIのみ**で完結します。

## 動作概要

1. Slack全チャンネルを `AI / 生成AI / ChatGPT / Claude / Gemini / LLM / 機械学習` で検索
2. メッセージ内のリッチリンク（`<URL|タイトル>`）から記事URLを抽出・重複除去
3. チャンネルごとにグループ化し、以下のフォーマットで `#ai活用`（`C0B3ABK2JKE`）に投稿

```
📰 *昨日（M/D）のAI関連記事まとめ*

*#チャンネル名 より*
1. <URL|タイトル>
2. <URL|タイトル>

_自動収集 · YYYY/MM/DD_
```

## ファイル構成

```
ai-digest/
├── ai_digest.py                  # メインスクリプト
├── requirements.txt              # 依存: requests のみ
├── README.md
└── .github/
    └── workflows/
        └── ai_digest.yml        # 毎日 UTC 01:00 / 手動実行
```

## セットアップ手順

### 1. GitHubリポジトリを作成して push する

```bash
cd /path/to/ai-digest
git init
git add .
git commit -m "initial commit"
```

GitHubで新しいリポジトリを作成したあと:

```bash
git remote add origin https://github.com/<your-name>/<your-repo>.git
git branch -M main
git push -u origin main
```

### 2. GitHub Secrets に SLACK_TOKEN を登録する

1. GitHubリポジトリの **Settings** を開く
2. 左メニューの **Secrets and variables → Actions** を選択
3. **New repository secret** をクリック
4. 以下を入力して **Add secret**

| Name | Secret |
|---|---|
| `SLACK_TOKEN` | Slack User OAuth Token（`xoxp-...`） |

### 3. Slack App の User Token Scopes を設定する

> `search:read` は User Token でのみ利用可能なため、Bot Token ではなく **User OAuth Token（xoxp-）** が必要です。

1. [Slack API サイト](https://api.slack.com/apps) でアプリを選択（または新規作成）
2. 左メニューの **OAuth & Permissions** を開く
3. **User Token Scopes** セクションで以下の2つを追加

| スコープ | 用途 |
|---|---|
| `search:read` | 全チャンネルのメッセージ検索 |
| `chat:write` | チャンネルへのメッセージ投稿 |

4. **Reinstall App** でワークスペースに再インストールし、発行された **User OAuth Token**（`xoxp-...`）をコピーして手順2のSecretに登録する

### 4. 手動実行でテストする

1. GitHubリポジトリの **Actions** タブを開く
2. 左メニューの **AI Digest** を選択
3. **Run workflow → Run workflow** をクリック
4. 実行ログを開き、最終行に `Posted successfully.` と表示されれば成功

## ローカル実行

```bash
pip install -r requirements.txt
export SLACK_TOKEN=xoxp-...
python ai_digest.py
```
