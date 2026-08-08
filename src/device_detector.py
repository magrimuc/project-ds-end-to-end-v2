import streamlit as st

def is_mobile_device() -> bool:
    """
    Detects if the client is accessing the app from a mobile browser.
    Inspects WebSocket connection headers or defaults to false.
    """
    try:
        # Streamlit >= 1.30.0 WebSocket headers retrieval
        from streamlit.web.server.websocket_headers import _get_websocket_headers
        headers = _get_websocket_headers()
        if headers:
            user_agent = headers.get("User-Agent", "").lower()
            mobile_keywords = ["mobile", "android", "iphone", "ipad", "phone", "opera mini", "iemobile"]
            return any(keyword in user_agent for keyword in mobile_keywords)
    except Exception:
        pass
    return False
