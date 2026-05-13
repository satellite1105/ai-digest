import os
import re
import time
from collections import defaultdict
from datetime import datetime, timezone, timedelta

import requests

SLACK_TOKEN = os.environ["SLACK_TOKEN"]
TARGET_CHANNEL_ID = "C0B3ABK2JKE"
KEYWORDS = ["AI", "生成AI", "ChatGPT", "Claude", "Gemini", "LLM", "機械学習"]

JST = timezone(timedelta(hours=9))


def get_yesterday_range_jst() -> tuple[int, int]:
    now_jst = datetime.now(JST)
    yesterday = now_jst.date() - timedelta(days=1)
    start = datetime(yesterday.year, yesterday.month, yesterday.day, 0, 0, 0, tzinfo=JST)
    end = datetime(yesterday.year, yesterday.month, yesterday.day, 23, 59, 59, tzinfo=JST)
    return int(start.timestamp()), int(end.timestamp())


def _get_with_retry(url: str, headers: dict, params: dict) -> requests.Response:
    while True:
        resp = requests.get(url, headers=headers, params=params)
        if resp.status_code == 429:
            wait = int(resp.headers.get("Retry-After", 60))
            print(f"Rate limited (429). Waiting {wait}s before retry...")
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp


def search_messages(keyword: str, oldest: int, latest: int) -> list[dict]:
    url = "https://slack.com/api/search.messages"
    headers = {"Authorization": f"Bearer {SLACK_TOKEN}"}
    messages = []
    page = 1

    # search.messages ignores oldest/latest params; use the `on:` search operator instead
    date_str = datetime.fromtimestamp(oldest, tz=JST).strftime("%Y-%m-%d")
    query = f"{keyword} on:{date_str}"

    while True:
        params = {
            "query": query,
            "count": 100,
            "page": page,
        }
        resp = _get_with_retry(url, headers, params)
        data = resp.json()

        if not data.get("ok"):
            print(f"search.messages error for '{keyword}': {data.get('error')}")
            break

        matches = data.get("messages", {}).get("matches", [])
        # client-side filter as safety net in case on: uses a different timezone
        for m in matches:
            if oldest <= float(m.get("ts", 0)) <= latest:
                messages.append(m)

        paging = data.get("messages", {}).get("paging", {})
        if page >= paging.get("pages", 1):
            break
        page += 1
        time.sleep(1)

    return messages


MIN_TITLE_LEN = 15


def _extract_link(msg: dict) -> tuple[str, str] | None:
    """Return (url, title) for a message, preferring OGP attachments over raw text links."""
    rich_link_pattern = re.compile(r"<(https?://[^|>]+)\|([^>]+)>")

    attachments = msg.get("attachments") or []
    if attachments:
        att = attachments[0]
        url = att.get("original_url") or att.get("title_link") or ""
        title = (att.get("title") or "").strip()
        if url and len(title) >= MIN_TITLE_LEN:
            return url, title

    m = rich_link_pattern.search(msg.get("text", ""))
    if m:
        url, title = m.group(1), m.group(2).strip()
        if len(title) >= MIN_TITLE_LEN:
            return url, title

    return None


def extract_articles(messages: list[dict], oldest: int, latest: int) -> dict[str, list[dict]]:
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    by_channel: dict[str, list[dict]] = defaultdict(list)

    for msg in messages:
        if not (oldest <= float(msg.get("ts", 0)) <= latest):
            continue
        if msg.get("channel", {}).get("id") == TARGET_CHANNEL_ID:
            continue

        result = _extract_link(msg)
        if result is None:
            continue
        url, title = result

        if url in seen_urls or title in seen_titles:
            continue
        seen_urls.add(url)
        seen_titles.add(title)
        channel_name = msg.get("channel", {}).get("name", "不明")
        by_channel[channel_name].append({"url": url, "title": title})

    return by_channel


def build_message(by_channel: dict[str, list[dict]], oldest: int) -> str:
    yesterday_dt = datetime.fromtimestamp(oldest, tz=JST)
    date_md = yesterday_dt.strftime("%-m/%-d")
    date_full = yesterday_dt.strftime("%Y/%m/%d")

    if not by_channel:
        return (
            f":newspaper: *昨日（{date_md}）のAI関連記事まとめ*\n\n"
            "本日はAI関連記事が見つかりませんでした。\n\n"
            f"_自動収集 · {date_full}_"
        )

    lines = [f":newspaper: *昨日（{date_md}）のAI関連記事まとめ*\n"]

    for channel_name, articles in sorted(by_channel.items()):
        lines.append(f"*#{channel_name} より*")
        for i, a in enumerate(articles, 1):
            lines.append(f"{i}. <{a['url']}|{a['title']}>")
        lines.append("")

    lines.append(f"_自動収集 · {date_full}_")
    return "\n".join(lines)


def post_to_slack(text: str) -> None:
    url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Authorization": f"Bearer {SLACK_TOKEN}",
        "Content-Type": "application/json; charset=utf-8",
    }
    payload = {
        "channel": TARGET_CHANNEL_ID,
        "text": text,
        "mrkdwn": True,
        "unfurl_links": False,
        "unfurl_media": False,
    }
    resp = requests.post(url, headers=headers, json=payload)
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"chat.postMessage failed: {data.get('error')}")
    print("Posted successfully.")


def main() -> None:
    oldest, latest = get_yesterday_range_jst()
    print(f"Searching {datetime.fromtimestamp(oldest, tz=JST).strftime('%Y/%m/%d')} ({oldest}-{latest})")

    all_messages: list[dict] = []
    for keyword in KEYWORDS:
        print(f"  keyword: {keyword}")
        msgs = search_messages(keyword, oldest, latest)
        all_messages.extend(msgs)
        time.sleep(3)

    print(f"Total raw messages: {len(all_messages)}")
    by_channel = extract_articles(all_messages, oldest, latest)
    total = sum(len(v) for v in by_channel.values())
    print(f"Unique articles: {total}")

    message = build_message(by_channel, oldest)
    post_to_slack(message)


if __name__ == "__main__":
    main()
