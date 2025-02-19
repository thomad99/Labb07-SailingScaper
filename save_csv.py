import os
import subprocess

def push_to_github(filename):
    """Push the saved CSV file to a GitHub repository."""
    
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")
    GITHUB_REPO = os.getenv("GITHUB_REPO")

    if not GITHUB_TOKEN or not GITHUB_USERNAME or not GITHUB_REPO:
        print("❌ GitHub credentials missing! Set GITHUB_TOKEN, GITHUB_USERNAME, and GITHUB_REPO in Render.")
        return
    
    # ✅ Correctly format the GitHub repository URL
    repo_url = f"https://{GITHUB_USERNAME}:{GITHUB_TOKEN}@github.com/{GITHUB_USERNAME}/{GITHUB_REPO}.git"
    print(f"🔍 Using GitHub URL: {repo_url}")  # Debugging

    repo_dir = "/tmp/repo"

    # ✅ Remove any existing repo before cloning
    subprocess.run(["rm", "-rf", repo_dir])

    # ✅ Clone the repository
    clone_result = subprocess.run(["git", "clone", repo_url, repo_dir], capture_output=True, text=True)

    if clone_result.returncode != 0:
        print("❌ Git Clone Failed:", clone_result.stderr)
        return

    # ✅ Ensure repository directory exists before proceeding
    if not os.path.exists(repo_dir):
        print("❌ Error: Repository directory does not exist!")
        return

    # ✅ Set Git user identity (Fixes the "Author identity unknown" error)
    subprocess.run(["git", "-C", repo_dir, "config", "user.email", "david.thomas@thinworld.net"], check=True)
    subprocess.run(["git", "-C", repo_dir, "config", "user.name", GITHUB_USERNAME], check=True)

    # ✅ Move CSV file into the cloned repo
    subprocess.run(["mv", filename, f"{repo_dir}/race_results.csv"], check=True)

    # ✅ Commit and push changes
    subprocess.run(["git", "-C", repo_dir, "add", "race_results.csv"], check=True)
    subprocess.run(["git", "-C", repo_dir, "commit", "-m", "Auto-uploaded regatta results"], check=True)
    subprocess.run(["git", "-C", repo_dir, "push", "origin", "main"], check=True)

    print("✅ CSV file successfully pushed to GitHub!")
