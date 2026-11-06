from urllib.parse import unquote, urlparse


def get_auth_from_url(url: str) -> tuple:
    """Given a url with authentication components, extract them into a tuple of
    username,password.

    :rtype: (str,str)
    """
    parsed = urlparse(url)

    try:
        auth = (unquote(parsed.username), parsed.password)
    except (AttributeError, TypeError):
        auth = ("", "")

    return auth


def urldefragauth(url: str) -> str:
    """Given a url remove the fragment and the authentication part.

    :rtype: str
    """
    scheme, netloc, path, params, query, fragment = __import__("urllib.parse").parse.urlparse(url)

    # see func:`prepend_scheme_if_needed`
    if not netloc:
        netloc, path = path, netloc

    netloc = netloc.rsplit("@", 1)[-1]

    from urllib.parse import urlunparse

    return urlunparse((scheme, netloc, path, params, query, ""))
