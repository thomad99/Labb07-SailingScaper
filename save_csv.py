import os
import subprocess

def save_to_csv(csv_content, filename="/tmp/regatta_results.csv"):
    """Save formatted CSV data and push to GitHub."""
    
    # ✅ Save CSV locally in `/tmp/`
    with open(filename, "w", newline="", encoding="utf-8") as file:
        file.write(csv_content)
    
    # ✅ Push to GitHub
    push_to_github(filename)

    return filename

def push_to_github(filename):
    """Push the saved CSV file to a GitHub repository."""
    
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")
    GITHUB_REPO = os.getenv("GITHUB_REPO")

    if not GITHUB_TOKEN or not GITHUB_USERNAME or not GITHUB_REPO:
        print("❌ GitHub credentials missing! Set GITHUB_TOKEN, GITHUB_USERNAME, and GITHUB_REPO.")
        return
    
    repo_url = f"https://{GITHUB_USERNAME}:{GITHUB_TOKEN}@github.com/{GITHUB_REPO}.git"

    # ✅ Clone the repository to `/tmp/repo`
    repo_dir = "/tmp/repo"
    subprocess.run(["rm", "-rf", repo_dir])  # Remove old repo
    subprocess.run(["git", "clone", repo_url, repo_dir])

    # ✅ Move CSV file into the repo
    subprocess.run(["mv", filename, f"{repo_dir}/race_results.csv"])

    # ✅ Commit and push the file
    subprocess.run(["git", "-C", repo_dir, "add", "race_results.csv"])
    subprocess.run(["git", "-C", repo_dir, "commit", "-m", "Auto-uploaded regatta results"])
    subprocess.run(["git", "-C", repo_dir, "push"])

    print("✅ CSV file successfully pushed to GitHub!")

