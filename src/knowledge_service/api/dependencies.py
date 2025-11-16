"""Shared API dependencies."""

from fastapi import Header

def get_user_id(x_user_id: str = Header(..., alias="X-User-ID")) -> str:
    """Extract user ID from gateway headers."""
    return x_user_id


def get_user_email(x_user_email: str = Header(..., alias="X-User-Email")) -> str:
    """Extract user email from gateway headers."""
    return x_user_email


def get_user_roles(x_user_roles: str = Header(..., alias="X-User-Roles")) -> str:
    """Extract user roles from gateway headers."""
    return x_user_roles
