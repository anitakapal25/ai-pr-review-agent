"""Deliberate review issue for the GitHub Actions end-to-end test."""


def fetch_user(client):
    try:
        return client.fetch_user()
    except:
        return None
