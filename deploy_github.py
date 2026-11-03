"""Deploy project to GitHub repository via GitHub REST API without requiring Git CLI."""
import os
import sys
import base64
import json
import urllib.request
import urllib.error

ROOT = r"C:\Users\vigne\.gemini\antigravity\scratch\ai-testing-agent"

def is_ignored(rel_path):
    p = rel_path.replace("\\", "/")
    ignore_prefixes = ("ai_testing.db", "sandbox/", "uploads/", "__pycache__/", ".git/")
    ignore_substrings = ("__pycache__", ".db", ".sqlite", ".pyc")
    if p.startswith(ignore_prefixes):
        return True
    if any(s in p for s in ignore_substrings):
        return True
    return False

def get_deployable_files():
    files_to_upload = []
    for root, dirs, files in os.walk(ROOT):
        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, ROOT)
            if not is_ignored(rel_path):
                files_to_upload.append((rel_path, full_path))
    return files_to_upload

def api_request(url, token, data=None, method="GET"):
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "AI-Testing-Agent-Deployer")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if data is not None:
        req.add_header("Content-Type", "application/json")
        encoded_data = json.dumps(data).encode("utf-8")
    else:
        encoded_data = None
    try:
        with urllib.request.urlopen(req, data=encoded_data, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(error_body)
        except Exception:
            return e.code, {"message": error_body}

def deploy(token, repo_name, is_private=False, description="AI Model Testing, Evaluation and Forensic Investigation Agent"):
    print("Checking authenticated GitHub user...")
    status, user_info = api_request("https://api.github.com/user", token)
    if status != 200:
        print(f"Error authenticating with GitHub token (HTTP {status}): {user_info.get('message')}")
        return False

    username = user_info.get("login")
    print(f"Authenticated as GitHub user: @{username}")

    # Check if repository already exists, if not create it
    repo_url = f"https://api.github.com/repos/{username}/{repo_name}"
    status, repo_info = api_request(repo_url, token)
    if status == 404:
        print(f"Repository '{repo_name}' not found. Creating new repository under @{username}...")
        create_payload = {
            "name": repo_name,
            "description": description,
            "private": is_private,
            "auto_init": True
        }
        status, new_repo = api_request("https://api.github.com/user/repos", token, data=create_payload, method="POST")
        if status not in [200, 201]:
            print(f"Failed to create repository: {new_repo}")
            return False
        print(f"Repository created: https://github.com/{username}/{repo_name}")
    elif status == 200:
        print(f"Using existing repository: https://github.com/{username}/{repo_name}")
    else:
        print(f"Unexpected error checking repository (HTTP {status}): {repo_info}")
        return False

    files = get_deployable_files()
    print(f"\nUploading {len(files)} clean project files (ai_testing.db and secrets excluded)...")

    success_count = 0
    for rel_path, full_path in files:
        gh_path = rel_path.replace("\\", "/")
        try:
            with open(full_path, "rb") as f:
                content_bytes = f.read()
            b64_content = base64.b64encode(content_bytes).decode("utf-8")

            # Check if file exists in repo to get SHA (for updating)
            file_url = f"https://api.github.com/repos/{username}/{repo_name}/contents/{gh_path}"
            status, file_info = api_request(file_url, token)
            sha = file_info.get("sha") if status == 200 else None

            payload = {
                "message": f"deploy: add/update {gh_path}",
                "content": b64_content,
                "branch": "main"
            }
            if sha:
                payload["sha"] = sha

            status, upload_res = api_request(file_url, token, data=payload, method="PUT")
            if status in [200, 201]:
                print(f"  [OK] {gh_path}")
                success_count += 1
            else:
                print(f"  [FAILED] {gh_path}: {upload_res.get('message')}")
        except Exception as e:
            print(f"  [ERROR] {gh_path}: {str(e)}")

    print(f"\nDeployment completed: {success_count}/{len(files)} files pushed successfully!")
    print(f"Repository URL: https://github.com/{username}/{repo_name}")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python deploy_github.py <github_token> <repo_name> [is_private: true/false]")
        sys.exit(1)
    tok = sys.argv[1]
    rname = sys.argv[2]
    priv = sys.argv[3].lower() == "true" if len(sys.argv) > 3 else False
    deploy(tok, rname, priv)
