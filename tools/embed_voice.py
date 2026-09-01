# -*- coding: utf-8 -*-
"""voice/ の音声クリップを index.html に埋め込む。

アーティファクトは外部サーバーへ通信できないため、音声は data URI として
HTML の中に持たせる。voice/ に無いセリフは、これまでどおり端末の読み上げになる。

    python tools/embed_voice.py            埋め込む
    python tools/embed_voice.py --clear    埋め込みを消して読み上げに戻す
"""
import argparse
import base64
import glob
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(ROOT, "index.html")
OUT = os.path.join(ROOT, "voice")
BEGIN = "/* VOICE_CLIPS_BEGIN */"
END = "/* VOICE_CLIPS_END */"
MIME = {".mp3": "audio/mpeg", ".wav": "audio/wav", ".ogg": "audio/ogg", ".m4a": "audio/mp4"}


def line_keys(src):
    i = src.index("const L = {")
    j = src.index("\n};", i)
    return [k for k, _ in re.findall(r'(\w+)\s*:\s*"((?:[^"\\]|\\.)*)"', src[i:j])]


def build_block():
    files = {}
    for f in sorted(glob.glob(os.path.join(OUT, "*"))):
        ext = os.path.splitext(f)[1].lower()
        if ext in MIME:
            files.setdefault(os.path.splitext(os.path.basename(f))[0], f)
    if not files:
        sys.exit("voice/ に音声ファイルがありません。先に tools/voicevox.py make を実行してください。")

    entries, total = [], 0
    for key in sorted(files):
        path = files[key]
        raw = io.open(path, "rb").read()
        total += len(raw)
        mime = MIME[os.path.splitext(path)[1].lower()]
        b64 = base64.b64encode(raw).decode("ascii")
        entries.append('"%s":"data:%s;base64,%s"' % (key, mime, b64))
    return files, total, "const VOICE_CLIPS = {\n" + ",\n".join(entries) + "\n};"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clear", action="store_true", help="埋め込みを消す")
    a = ap.parse_args()

    src = io.open(HTML, encoding="utf-8").read()
    i, j = src.index(BEGIN), src.index(END)

    if a.clear:
        block = "const VOICE_CLIPS = {};"
        report = "埋め込みを消しました。端末の読み上げに戻ります。"
    else:
        files, total, block = build_block()
        keys, have = line_keys(src), set(files)
        missing = [k for k in keys if k not in have]
        extra = sorted(have - set(keys))
        report = "%d 本 / %.0f KB を埋め込みました。" % (len(files), total / 1024.0)
        if missing:
            report += "\n読み上げのまま残るセリフ %d 本: %s" % (len(missing), ", ".join(missing))
        if extra:
            report += "\nL に無いファイル（無視されます）: %s" % ", ".join(extra)
        if total > 12 * 1024 * 1024:
            report += "\n⚠ 12MB を超えています。アーティファクトの上限16MBに近いので、"
            report += "ビットレートを下げるか wav を mp3 にしてください。"

    out = src[:i] + BEGIN + "\n" + block + "\n" + src[j:]
    io.open(HTML, "w", encoding="utf-8").write(out)
    print(report)
    print("index.html: %.1f MB" % (os.path.getsize(HTML) / 1048576.0))


if __name__ == "__main__":
    main()
