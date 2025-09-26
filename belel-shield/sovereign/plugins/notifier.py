def send(title: str, message: str):
    try:
        from plyer import notification
        notification.notify(title=title, message=message, timeout=4)
    except Exception:
        print(f"[NOTIFY] {title}: {message}")
