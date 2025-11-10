"""IP address extraction from HTTP requests with reverse proxy support."""

from typing import Optional
from fastapi import Request


def get_client_ip(request: Request) -> str:
    """
    Extract real client IP from request, handling Traefik/reverse proxy headers.
    
    Order of precedence:
    1. X-Forwarded-For (first IP in comma-separated list - the original client)
    2. X-Real-IP (Nginx/CloudFlare standard)
    3. request.client.host (direct connection fallback)
    
    Args:
        request: FastAPI Request object
        
    Returns:
        Client IP address as string
        
    Note:
        For production deployments behind reverse proxies, ensure that proxy headers
        are only accepted from trusted sources to prevent IP spoofing.
        
    TODO: Add IP whitelist validation for proxy headers to prevent spoofing
          TRUSTED_PROXIES = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]
          Only trust X-Forwarded-For if direct connection IP is in TRUSTED_PROXIES
    """
    # Check X-Forwarded-For header (Traefik, HAProxy, AWS ELB)
    # Format: "client, proxy1, proxy2" - we want the first IP (original client)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP in the list (the original client)
        client_ip = forwarded_for.split(",")[0].strip()
        if client_ip:
            return client_ip
    
    # Check X-Real-IP header (Nginx, CloudFlare)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    
    # Fallback to direct connection (no proxy)
    if request.client and request.client.host:
        return request.client.host
    
    # Ultimate fallback
    return "unknown"


def get_user_agent(request: Request) -> Optional[str]:
    """
    Extract User-Agent header from request.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        User-Agent string or None if not present
    """
    return request.headers.get("User-Agent")
