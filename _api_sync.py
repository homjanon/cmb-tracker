#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
经 GitHub Contents API 把本地若干文件推送到仓库（替代被墙的 git push）。
用法（在本机、仓库根目录下执行）：
  set GITHUB_TOKEN=<gh token>
  python _api_sync.py --owner homjanon --repo cmb-tracker --branch main \
      scripts/render_report.py scripts/run_daily.py \
      scripts/zhaozhao_five_dim.py .github/workflows/daily.yml output/cmb_report.json
依赖：仅标准库（urllib / base64 / json）。
"""
import os
import sys
import json
import base64
import argparse
import urllib.request
import urllib.error

API = "https://api.github.com"


def api(token, method, path, data=None):
    url = API + path
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "cmb-tracker-sync",
    }
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", "replace")
        print(f"HTTP {e.code} {method} {path}: {err[:600]}", file=sys.stderr)
        raise


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--owner", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--branch", default="main")
    ap.add_argument("--message", default="feat: 产出 output/cmb_report.json（招招五维·买入区间）")
    ap.add_argument("files", nargs="+")
    args = ap.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("缺少环境变量 GITHUB_TOKEN", file=sys.stderr)
        sys.exit(1)

    root = os.getcwd()
    base = f"/repos/{args.owner}/{args.repo}"

    # 1) 当前分支最新提交
    ref = api(token, "GET", f"{base}/git/refs/heads/{args.branch}")
    base_sha = ref["object"]["sha"]
    commit = api(token, "GET", f"{base}/git/commits/{base_sha}")
    base_tree = commit["tree"]["sha"]

    # 2) 逐个建 blob
    entries = []
    for fpath in args.files:
        abs_path = os.path.join(root, fpath)
        if not os.path.exists(abs_path):
            print(f"跳过不存在的文件：{fpath}", file=sys.stderr)
            continue
        with open(abs_path, "rb") as fh:
            raw = fh.read()
        blob = api(token, "POST", f"{base}/git/blobs",
                   {"content": base64.b64encode(raw).decode("ascii"), "encoding": "base64"})
        repo_path = fpath.replace("\\", "/")
        if repo_path.startswith("./"):   # 仅去掉 "./" 前缀，保留 ".github" 等以点开头的真实路径
            repo_path = repo_path[2:]
        entries.append({"path": repo_path, "mode": "100644",
                        "type": "blob", "sha": blob["sha"]})
        print(f"  blob ✓ {repo_path}")

    if not entries:
        print("没有可推送的文件")
        return

    # 3) 新 tree（基于 base_tree 覆盖）
    tree = api(token, "POST", f"{base}/git/trees",
               {"base_tree": base_tree, "tree": entries})

    # 4) 新 commit
    new_commit = api(token, "POST", f"{base}/git/commits",
                     {"message": args.message, "tree": tree["sha"],
                      "parents": [base_sha]})

    # 5) 更新 ref
    api(token, "PATCH", f"{base}/git/refs/heads/{args.branch}",
        {"sha": new_commit["sha"]})

    print(f"✅ 已推送 {len(entries)} 个文件 → "
          f"{args.owner}/{args.repo}@{args.branch} ({new_commit['sha'][:7]})")


if __name__ == "__main__":
    main()
