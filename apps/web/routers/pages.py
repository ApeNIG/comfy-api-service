"""
Web page routes

Serves HTML pages for the Creator web interface:
- Auth pages (login, signup)
- Dashboard
- Onboarding flow
- Settings

Uses Jinja2 templating for server-side rendering.
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from apps.creator.dependencies import get_current_user_optional
from apps.creator.models.domain import User

router = APIRouter()

# Initialize Jinja2 templates
templates = Jinja2Templates(directory="apps/web/templates")


@router.get("/", response_class=HTMLResponse)
async def home_page(
    request: Request,
    user: User = Depends(get_current_user_optional),
):
    """
    Home page.

    If authenticated: redirect to dashboard
    If not authenticated: show landing page with CTA to sign up
    """
    if user:
        # Redirect to dashboard if already logged in
        return templates.TemplateResponse(
            "redirect.html",
            {
                "request": request,
                "redirect_url": "/dashboard",
                "message": f"Welcome back, {user.full_name}!",
            },
        )

    # Show landing page
    return templates.TemplateResponse(
        "landing.html",
        {"request": request},
    )


@router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    user: User = Depends(get_current_user_optional),
):
    """
    Login/signup page.

    Beautiful glassmorphism design with:
    - Email/password login
    - Google OAuth
    - Tab switching between login/signup
    - Friendly error messages
    - Loading states with animations
    """
    if user:
        # Already logged in, redirect to dashboard
        return templates.TemplateResponse(
            "redirect.html",
            {
                "request": request,
                "redirect_url": "/dashboard",
                "message": "You're already logged in!",
            },
        )

    return templates.TemplateResponse(
        "auth.html",
        {
            "request": request,
            "google_oauth_url": "/auth/google",  # Google OAuth start URL
        },
    )


@router.get("/signup", response_class=HTMLResponse)
async def signup_page(
    request: Request,
    user: User = Depends(get_current_user_optional),
):
    """
    Signup page (alias for login page with signup tab active).
    """
    if user:
        return templates.TemplateResponse(
            "redirect.html",
            {
                "request": request,
                "redirect_url": "/dashboard",
                "message": "You're already logged in!",
            },
        )

    return templates.TemplateResponse(
        "auth.html",
        {
            "request": request,
            "google_oauth_url": "/auth/google",
            "default_tab": "signup",  # Show signup tab by default
        },
    )


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(
    request: Request,
    user: User = Depends(get_current_user_optional),
):
    """
    Main dashboard page.

    Shows:
    - Recent jobs with real-time status
    - Usage stats (jobs remaining, trial days)
    - Quick actions (upload file, connect Drive)
    - Subscription info

    Requires authentication.
    """
    if not user:
        # Not logged in, redirect to login
        return templates.TemplateResponse(
            "redirect.html",
            {
                "request": request,
                "redirect_url": "/login",
                "message": "Please log in to continue",
            },
        )

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
        },
    )


@router.get("/onboarding", response_class=HTMLResponse)
async def onboarding_page(
    request: Request,
    user: User = Depends(get_current_user_optional),
):
    """
    Onboarding flow for new users.

    Steps:
    1. Welcome message
    2. Connect Google Drive
    3. Choose folder to watch
    4. Test upload
    5. Done!

    Beautiful step-by-step wizard with progress indicator.
    """
    if not user:
        return templates.TemplateResponse(
            "redirect.html",
            {
                "request": request,
                "redirect_url": "/login",
                "message": "Please log in to continue",
            },
        )

    return templates.TemplateResponse(
        "onboarding.html",
        {
            "request": request,
            "user": user,
        },
    )


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    user: User = Depends(get_current_user_optional),
):
    """
    User settings page.

    Sections:
    - Profile (name, email)
    - Drive integration (connect/disconnect, folder)
    - Subscription (upgrade, billing)
    - Notifications (email preferences)
    - Security (password change, sessions)
    """
    if not user:
        return templates.TemplateResponse(
            "redirect.html",
            {
                "request": request,
                "redirect_url": "/login",
                "message": "Please log in to continue",
            },
        )

    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "user": user,
        },
    )
