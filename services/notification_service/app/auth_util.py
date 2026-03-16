from fastapi import Header, HTTPException


def get_current_user_email(
    x_user_email: str | None = Header(default=None, alias="X-User-Email"),
) -> str:
    email = (x_user_email or "").strip()
    if not email:
        raise HTTPException(status_code=401, detail="Missing X-User-Email header")
    return email
