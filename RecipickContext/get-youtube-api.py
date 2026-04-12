import sys
import re
import subprocess
import json
import os
from youtube_transcript_api import YouTubeTranscriptApi

def extract_video_id(url):
    patterns = [r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", r"youtu\.be\/([0-9A-Za-z_-]{11})"]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match: return match.group(1)
    return url

def format_time(seconds):
    """秒を [HH:MM:SS] 形式に変換"""
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"[{h:02d}:{m:02d}:{s:02d}]"

def get_video_info(video_id):
    """yt-dlpを使って動画情報を取得"""
    try:
        cmd = [
            'yt-dlp',
            '--dump-json',
            '--no-download',
            f'https://www.youtube.com/watch?v={video_id}'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            info = json.loads(result.stdout)
            return {
                'title': info.get('title', 'N/A'),
                'channel': info.get('uploader', info.get('channel', 'N/A')),
                'upload_date': info.get('upload_date', 'N/A'),
                'duration': info.get('duration', 0),
                'view_count': info.get('view_count', 'N/A')
            }
    except Exception:
        pass
    return None

def main():
    if len(sys.argv) < 2:
        print("使い方: uv run app-all.py \"URL\"")
        return

    video_id = extract_video_id(sys.argv[1])
    output_dir = "transcripts"
    filename = f"full_transcript_{video_id}.txt"
    filepath = os.path.join(output_dir, filename)

    # --- 重複チェック処理 ---
    if os.path.exists(filepath):
        print(f"!!! スキップ: すでにファイルが存在します ({filepath})")
        return
    # ----------------------

    # フォルダ作成
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    langs = ['ja', 'ja-JP', 'en']
    print(f"--- 取得を開始: {video_id} ---")

    try:
        video_info = get_video_info(video_id)

        ytt = YouTubeTranscriptApi()
        transcript_list = ytt.list(video_id)

        try:
            transcript = transcript_list.find_transcript(langs)
        except:
            transcript = next(iter(transcript_list))

        print(f"取得言語: {transcript.language} ({transcript.language_code})")
        data = transcript.fetch()

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("=" * 60 + "\n")
            if video_info:
                f.write(f"タイトル: {video_info['title']}\n")
                f.write(f"チャンネル: {video_info['channel']}\n")
                upload_date = video_info['upload_date']
                if upload_date != 'N/A' and len(upload_date) == 8:
                    formatted_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}"
                    f.write(f"公開日: {formatted_date}\n")
                else:
                    f.write(f"公開日: {upload_date}\n")

                view_count = video_info.get('view_count', 'N/A')
                if view_count != 'N/A':
                    f.write(f"再生回数: {view_count:,}\n")

            f.write(f"動画URL: https://www.youtube.com/watch?v={video_id}\n")
            f.write(f"字幕言語: {transcript.language} ({transcript.language_code})\n")
            f.write("=" * 60 + "\n\n")

            for item in data:
                # 辞書・オブジェクト両対応
                start = item['start'] if isinstance(item, dict) else item.start
                text = item['text'] if isinstance(item, dict) else item.text

                time_stamp = format_time(start)
                clean_text = text.replace('\n', ' ')
                f.write(f"{time_stamp} {clean_text}\n")

        print(f"--- 完了 ---")
        print(f"ファイルに保存しました: {filepath}")
        print(f"全 {len(data)} 行を取得しました。")

    except Exception as e:
        print(f"エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
