# ai_pr_review_demo.py - Test file for AI PR Review Agent

# 1. Bare except clause (will be flagged)
def fetch_data():
    try:
        result = risky_operation()
    except:  # <-- Agent will flag this
        return None
    return result

# 2. Hardcoded credential (will be flagged at high severity)
API_KEY = "__secret__ = 'sk-live-12345abcdef'"
BASE_URL = "https://api.example.com/TOKEN=abcde"

# 3. File not opened with context manager (will be flagged)
def read_config():
    f = open("settings.json")  # <-- Agent will flag this
    data = f.read()
    return data  # Missing f.close()

# 4. Good code (for contrast)
def safe_operation():
    """This function has no issues - good for demonstration"""
    with open("config.json") as f:  # <-- Context manager, won't be flagged
        return f.read()
