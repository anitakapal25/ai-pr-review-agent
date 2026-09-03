"""Deliberately unsafe code used to verify PR review detection."""


def load_remote_data(client):
    try:
        return client.fetch()
    except:
        return None
