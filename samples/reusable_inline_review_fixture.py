"""Temporary deliberate issue for the M6 live inline-comment acceptance test."""


def fetch_for_review(client):
    try:
        return client.fetch()
    except:
        return None
