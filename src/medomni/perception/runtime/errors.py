"""The two ways a call can fail (Container API)."""


class BadRequest(Exception):
    """The caller sent something wrong. HTTP 400."""


class Degraded(Exception):
    """The input is unusable. HTTP 200 with healthy=false — not an error."""
