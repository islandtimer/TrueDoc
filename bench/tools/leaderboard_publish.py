"""Create the public model repository and upload the entry folder. The token is the one `hf auth login`
stored; this script never reads or prints it.

usage: python bench/tools/leaderboard_publish.py <entry folder> <repo id>   (the folder leaderboard_entry.py built)
"""
import sys

from huggingface_hub import HfApi

folder, repo_id = sys.argv[1], sys.argv[2]
api = HfApi()
print("acting as:", api.whoami()["name"])
url = api.create_repo(repo_id, repo_type="model", private=False, exist_ok=True)
print("repository:", url)
info = api.upload_folder(
    folder_path=folder,
    repo_id=repo_id,
    repo_type="model",
    commit_message="TrueDoc run 97 on olmOCR-bench: 86.8, with all 1,403 page outputs and the scorer's log",
)
print("commit:", info.oid if hasattr(info, "oid") else info)
files = api.list_repo_files(repo_id, repo_type="model")
print("files on the hub:", len(files))
print("has the entry file:", ".eval_results/olmocrbench.yaml" in files)
print("outputs:", sum(1 for f in files if f.startswith("outputs/") and f.endswith(".md")))
print("scoring:", sorted(f for f in files if f.startswith("scoring/")))
