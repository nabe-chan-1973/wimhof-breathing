# -*- coding: utf-8 -*-
"""VOICEVOX でガイド音声のクリップを一括生成する。

セリフの原本は index.html の `const L = { ... }`。ここを読んで、
キーごとに voice/<キー>.mp3 を作る。

使い方:
    1. VOICEVOX を起動しておく（エンジンが 127.0.0.1:50021 で待ち受ける）
    2. python tools/voicevox.py list                 使える声の一覧
    3. python tools/voicevox.py make --speaker 13    voice/ に全クリップを生成
    4. python tools/embed_voice.py                   index.html に埋め込む

ffmpeg があれば mp3 に変換する。無ければ wav のまま置く（サイズは6倍ほど）。
"""
import argparse
import glob
import io
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(ROOT, "index.html")
OUT = os.path.join(ROOT, "voice")
API = "http://127.0.0.1:50021"


def find_ffmpeg():
    """PATH に無くても、winget や choco の既定の場所なら拾う。
    winget で入れた直後は、既存のシェルの PATH にまだ反映されていない。"""
    p = shutil.which("ffmpeg")
    if p:
        return p
    pats = [
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Packages",
                     "Gyan.FFmpeg*", "ffmpeg-*", "bin", "ffmpeg.exe"),
        os.path.join(os.environ.get("ProgramData", ""), "chocolatey", "bin", "ffmpeg.exe"),
        r"C:\ffmpeg\bin\ffmpeg.exe",
    ]
    for pat in pats:
        hit = sorted(glob.glob(pat))
        if hit:
            return hit[-1]
    return None


def lines():
    """index.html の L テーブルから (キー, セリフ) を取り出す。"""
    s = io.open(HTML, encoding="utf-8").read()
    i = s.index("const L = {")
    j = s.index("\n};", i)
    return re.findall(r'(\w+)\s*:\s*"((?:[^"\\]|\\.)*)"', s[i:j])


def _get(path):
    with urllib.request.urlopen(API + path, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def _post(path, params, data=None):
    url = API + path + "?" + urllib.parse.urlencode(params)
    headers = {"Content-Type": "application/json"} if data else {}
    req = urllib.request.Request(url, data=data, method="POST", headers=headers)
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def check_engine():
    try:
        _get("/version")
    except Exception:
        sys.exit(
            "VOICEVOX エンジンに繋がりません（" + API + "）。\n"
            "VOICEVOX を起動してから、もう一度実行してください。"
        )


def cmd_list():
    check_engine()
    for sp in _get("/speakers"):
        for st in sp["styles"]:
            print("%5d  %s（%s）" % (st["id"], sp["name"], st["name"]))
    print("\n落ち着いた読み上げなら 青山龍星・冥鳴ひまり・九州そら あたりが合います。")


def cmd_make(speaker, speed, pitch, intonation, only):
    check_engine()
    items = lines()
    if only:
        keys = set(only.split(","))
        items = [(k, t) for k, t in items if k in keys]
        if not items:
            sys.exit("--only で指定したキーが見つかりません。")

    os.makedirs(OUT, exist_ok=True)
    ff = find_ffmpeg()
    if not ff:
        print("※ ffmpeg が見つからないので wav のまま出力します。"
              "（mp3 にすると6分の1ほどのサイズになります）\n")

    total = 0
    for n, (key, text) in enumerate(items, 1):
        q = json.loads(_post("/audio_query", {"text": text, "speaker": speaker}).decode("utf-8"))
        q["speedScale"] = speed
        q["pitchScale"] = pitch
        q["intonationScale"] = intonation
        q["outputSamplingRate"] = 24000
        q["outputStereo"] = False
        # 前後の無音を削る。「すって／はいて」が拍からずれないように。
        q["prePhonemeLength"] = 0.0
        q["postPhonemeLength"] = 0.05
        wav = _post("/synthesis", {"speaker": speaker}, json.dumps(q).encode("utf-8"))

        wpath = os.path.join(OUT, key + ".wav")
        mpath = os.path.join(OUT, key + ".mp3")
        io.open(wpath, "wb").write(wav)
        if ff:
            subprocess.run(
                [ff, "-y", "-loglevel", "error", "-i", wpath,
                 "-ac", "1", "-ar", "24000", "-b:a", "64k", mpath],
                check=True,
            )
            os.remove(wpath)
            size = os.path.getsize(mpath)
        else:
            size = os.path.getsize(wpath)
        total += size
        print("[%2d/%2d] %-11s %6.1f KB  %s" % (n, len(items), key, size / 1024.0, text[:28]))

    print("\n合計 %.0f KB を %s に出力しました。" % (total / 1024.0, OUT))
    print("続けて  python tools/embed_voice.py  で index.html に埋め込みます。")


def main():
    ap = argparse.ArgumentParser(description="VOICEVOX でガイド音声を作る")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("list", help="使える声の一覧を出す")
    m = sub.add_parser("make", help="クリップを生成する")
    m.add_argument("--speaker", type=int, required=True, help="list で調べた声のID")
    m.add_argument("--speed", type=float, default=0.95, help="話す速さ（既定 0.95）")
    m.add_argument("--pitch", type=float, default=0.0, help="声の高さ（-0.15〜0.15 くらい）")
    m.add_argument("--intonation", type=float, default=0.9, help="抑揚（既定 0.9・控えめ）")
    m.add_argument("--only", default="", help="キーをカンマ区切りで指定して一部だけ作り直す")
    a = ap.parse_args()

    if a.cmd == "list":
        cmd_list()
    elif a.cmd == "make":
        cmd_make(a.speaker, a.speed, a.pitch, a.intonation, a.only)
    else:
        ap.print_help()
        print("\nセリフは全部で %d 本です。" % len(lines()))


if __name__ == "__main__":
    main()
