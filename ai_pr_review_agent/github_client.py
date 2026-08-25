import os
from github import Github

class GitHubClient:
    def __init__(self, repo_full_name):
        # Authenticate using the token provided by GitHub Actions or environment variable
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            raise ValueError("GITHUB_TOKEN environment variable is not set")

        self.github = Github(token)
        self.repo = self.github.get_repo(repo_full_name)

    def post_comment(self, pr_number, body):
        """Posts a comment to the specified PR."""
        try:
            pr = self.repo.get_pull(pr_number)
            pr.create_issue_comment(body)
            print(f"Successfully posted comment on PR #{pr_number}")
        except Exception as e:
            print(f"Failed to post comment: {e}")
            raise
