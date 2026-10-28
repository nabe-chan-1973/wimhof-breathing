# -*- coding: utf-8 -*-
"""index.html からアーティファクト版を作る。

アーティファクトは doctype / html / head / body を自前で包むので、
その外枠だけを剥がした HTML を書き出す。中身はいっさい変えない。

    python tools/make_artifact.py [出力先]

出力先を省くと、プロジェクト直下の build/artifact.html に置く。
"""
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(ROOT, "index.html")


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "build", "artifact.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)

    src = io.open(HTML, encoding="utf-8").read()
    head = src[src.index("<title>"): src.index("</head>")]
    body = src[src.index("<body>") + len("<body>"): src.rindex("</body>")]
    io.open(out, "w", encoding="utf-8").write(head.strip() + "\n" + body.strip() + "\n")

    print("%s  (%.1f MB)" % (out, os.path.getsize(out) / 1048576.0))


if __name__ == "__main__":
    main()
