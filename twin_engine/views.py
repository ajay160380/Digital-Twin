"""
views.py — Digital Twin Dashboard
==================================
Authentication, dashboard, AI prediction, and AI debate views.
All AJAX endpoints return consistent JSON envelopes: {ok, data/error}.
"""

from __future__ import annotations

import logging
from functools import wraps
from typing import Any

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.http import HttpRequest, JsonResponse, StreamingHttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .models import PastChoice, TwinSettings, UserPreference
from .logic import get_ai_debate, get_digital_twin_prediction, get_funny_roast, stream_digital_twin_prediction, get_daily_routine, get_ghostwriter_reply

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# CONSTANTS
# ──────────────────────────────────────────────────────────────

SPOTIFY_MOOD_PLAYLISTS: dict[str, str] = {
    "Happy":     "https://open.spotify.com/embed/playlist/37i9dQZF1DXdPec7aLTmlC",
    "Chill":     "https://open.spotify.com/embed/playlist/37i9dQZF1DX4WYpdgoIcn6",
    "Stressed":  "https://open.spotify.com/embed/playlist/37i9dQZF1DWZqd5JICZI0u",
    "Motivated": "https://open.spotify.com/embed/playlist/37i9dQZF1DX76Wlfdnj7AP",
    "Tired":     "https://open.spotify.com/embed/playlist/37i9dQZF1DWZd79rJ6a7lp",
    "Focused":   "https://open.spotify.com/embed/playlist/37i9dQZF1DWZeKCadgRdKQ",
}

DEFAULT_MOOD = "Chill"
MAX_SCENARIO_LENGTH = 1_000   # characters
MAX_TOPIC_LENGTH = 500


# ──────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────

def _json_ok(data: Any, status: int = 200) -> JsonResponse:
    """Consistent success envelope: {ok: true, data: ...}"""
    return JsonResponse({"ok": True, "data": data}, status=status)


def _json_error(message: str, status: int = 400) -> JsonResponse:
    """Consistent error envelope: {ok: false, error: ...}"""
    return JsonResponse({"ok": False, "error": message}, status=status)


def _get_spotify_link(mood: str | None) -> str:
    """Return a Spotify embed URL for the given mood (falls back to Chill)."""
    return SPOTIFY_MOOD_PLAYLISTS.get(mood or DEFAULT_MOOD, SPOTIFY_MOOD_PLAYLISTS[DEFAULT_MOOD])


def _unauthenticated_redirect(view_func):
    """
    Redirect already-authenticated users away from auth pages (login/register).
    Works like @login_required but in reverse.
    """
    @wraps(view_func)
    def wrapper(request: HttpRequest, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("twin_dashboard")
        return view_func(request, *args, **kwargs)
    return wrapper

# ✅ NAYA HELPER: Accuracy Calculate Karne Ke Liye
def _calculate_accuracy(user) -> int:
    rated_choices = PastChoice.objects.filter(user=user).exclude(is_accurate=None)
    total_rated = rated_choices.count()
    if total_rated == 0:
        return 0
    accurate_count = rated_choices.filter(is_accurate=True).count()
    return int((accurate_count / total_rated) * 100)


# ──────────────────────────────────────────────────────────────
# 1. AUTHENTICATION VIEWS
# ──────────────────────────────────────────────────────────────

@_unauthenticated_redirect
@require_http_methods(["GET", "POST"])
def register(request: HttpRequest):
    """User registration. On success, auto-logs in and redirects to dashboard."""
    form = UserCreationForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        logger.info("New user registered: %s", user.username)
        return redirect("twin_dashboard")

    return render(request, "registration/register.html", {"form": form})


@_unauthenticated_redirect
@require_http_methods(["GET", "POST"])
def login_view(request: HttpRequest):
    """Standard login. Redirects to dashboard on success."""
    form = AuthenticationForm(request, data=request.POST or None)

    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        login(request, user)
        logger.info("User logged in: %s", user.username)
        return redirect("twin_dashboard")

    return render(request, "registration/login.html", {"form": form})


@require_http_methods(["GET", "POST"])
def logout_view(request: HttpRequest):
    """Log out and redirect to login page."""
    if request.user.is_authenticated:
        logger.info("User logged out: %s", request.user.username)
    logout(request)
    return redirect("login")


# ──────────────────────────────────────────────────────────────
# 2. HOME & MAIN DASHBOARD VIEWS
# ──────────────────────────────────────────────────────────────

def home(request: HttpRequest):
    """Landing page view. Redirects to dashboard if logged in."""
    if request.user.is_authenticated:
        return redirect("twin_dashboard")
    return render(request, "home.html")

@login_required
@require_http_methods(["GET", "POST"])
def twin_dashboard(request: HttpRequest):
    """
    Main dashboard. Handles POST actions.
    """
    user = request.user

    if request.method == "POST":
        action = _detect_action(request)

        if action == "get_prediction":
            if request.POST.get("stream") == "1":
                return _handle_prediction_stream(request, user)
            return _handle_prediction(request, user)

        if action == "get_debate":
            return _handle_debate(request, user)

        if action == "update_twin_settings":
            return _handle_update_settings(request, user)
            
        if action == "rate_prediction":
            return _handle_rate_prediction(request, user)

        if action == "get_routine":
            return _handle_routine(request, user)
            
        if action == "get_ghostwriter":
            return _handle_ghostwriter(request, user)

        # Unknown POST action
        return _json_error(f"Unknown action. POST keys received: {', '.join(request.POST.keys()) or 'none'}", status=400)

    # ── GET: render dashboard ──────────────────────────────────
    twin_settings, _ = TwinSettings.objects.get_or_create(user=user)
    user_pref, _     = UserPreference.objects.get_or_create(user=user)

    # User History Filter
    user_history = PastChoice.objects.filter(user=user).order_by('-timestamp')[:50]
    total_predictions = user_history.count()
    
    # ✅ NAYA: Backend calculate accuracy percentage
    accuracy_percentage = _calculate_accuracy(user)

    current_mood = twin_settings.last_mood or DEFAULT_MOOD
    mood_roast = get_funny_roast(current_mood)

    context = {
        "twin_settings":  twin_settings,
        "user_pref":      user_pref,
        "favorite_color": user_pref.favorite_color,
        "spotify_link":   _get_spotify_link(current_mood),
        "mood_options":   list(SPOTIFY_MOOD_PLAYLISTS.keys()),
        "mood_roast":     mood_roast,
        "user_history":   user_history,
        "total_predictions": total_predictions,
        "accuracy_percentage": accuracy_percentage  # ✅ Passed to HTML
    }
    return render(request, "twin_dashboard.html", context)


# ──────────────────────────────────────────────────────────────
# 3. DASHBOARD POST HANDLERS  (private helpers)
# ──────────────────────────────────────────────────────────────

def _detect_action(request: HttpRequest) -> str | None:
    """Return the first recognized action key from POST data, even if button value is empty."""
    for action in ("get_prediction", "get_debate", "update_twin_settings", "rate_prediction", "get_routine", "get_ghostwriter"):
        if action in request.POST:
            return action

    posted_action = request.POST.get("action", "").strip()
    if posted_action in {"get_prediction", "get_debate", "update_twin_settings", "rate_prediction", "get_routine", "get_ghostwriter"}:
        return posted_action

    return None


def _handle_prediction(request: HttpRequest, user) -> JsonResponse:
    """AJAX handler: generate an AI twin prediction and persist it."""
    scenario = request.POST.get("scenario", "").strip()

    if not scenario:
        return _json_error("Scenario cannot be empty.")
    if len(scenario) > MAX_SCENARIO_LENGTH:
        return _json_error(f"Scenario too long (max {MAX_SCENARIO_LENGTH} characters).")

    try:
        prediction = get_digital_twin_prediction(user, scenario)
    except Exception as exc:
        logger.exception("Prediction failed for user %s", user.username)
        return _json_error(f"Prediction error: {exc}", status=500)

    try:
        # ✅ NAYA: Choice ko variable me store kiya taaki iska ID frontend ko bhej sake
        choice = PastChoice.objects.create(user=user, scenario=scenario, choice_made=prediction)
        logger.debug("Prediction saved for user %s", user.username)
        return _json_ok({"prediction": prediction, "prediction_id": choice.id})
    except Exception:
        logger.exception("Prediction was generated but could not be saved for user %s", user.username)
        return _json_error("Prediction generated but failed to save.", status=500)


def _handle_prediction_stream(request: HttpRequest, user) -> StreamingHttpResponse | JsonResponse:
    """AJAX handler: stream an AI twin prediction safely."""
    scenario = request.POST.get("scenario", "").strip()

    if not scenario:
        return _json_error("Scenario cannot be empty.")
    if len(scenario) > MAX_SCENARIO_LENGTH:
        return _json_error(f"Scenario too long (max {MAX_SCENARIO_LENGTH} characters).")

    def event_stream():
        collected_chunks: list[str] = []
        try:
            for chunk in stream_digital_twin_prediction(user, scenario):
                if chunk:
                    collected_chunks.append(chunk)
                    yield chunk
        except Exception as exc:
            logger.exception("Streaming prediction failed for user %s", user.username)
            yield f"\nPrediction stream error: {exc}"
            return

        prediction = "".join(collected_chunks).strip()
        if prediction:
            try:
                PastChoice.objects.create(user=user, scenario=scenario, choice_made=prediction)
            except Exception:
                logger.exception("Streaming prediction was generated but could not be saved for user %s", user.username)

    return StreamingHttpResponse(event_stream(), content_type="text/plain; charset=utf-8")


# ✅ NAYA FUNCTION: Rate Prediction Handler
def _handle_rate_prediction(request: HttpRequest, user) -> JsonResponse:
    """AJAX handler: Save the user's accuracy rating for a past choice."""
    prediction_id = request.POST.get("prediction_id")
    is_accurate_str = request.POST.get("is_accurate")
    
    if not prediction_id:
        return _json_error("Missing prediction ID.")
        
    try:
        choice = PastChoice.objects.get(id=prediction_id, user=user)
        choice.is_accurate = (is_accurate_str == "true")
        choice.save()
        
        # Rating save hone ke baad naya average accuracy nikalo
        new_accuracy = _calculate_accuracy(user)
        return _json_ok({"new_accuracy": new_accuracy})
    except PastChoice.DoesNotExist:
        return _json_error("Prediction not found.")


def _handle_debate(request: HttpRequest, user) -> JsonResponse:
    """AJAX handler: generate an AI vs AI debate script."""
    topic    = request.POST.get("topic", "").strip()
    opponent = request.POST.get("opponent", "Strict Professor").strip() or "Strict Professor"

    if not topic:
        return _json_error("Debate topic cannot be empty.")
    if len(topic) > MAX_TOPIC_LENGTH:
        return _json_error(f"Topic too long (max {MAX_TOPIC_LENGTH} characters).")

    try:
        script = get_ai_debate(user, topic, opponent)
    except Exception as exc:
        logger.exception("Debate generation failed for user %s", user.username)
        return _json_error(f"Debate error: {exc}", status=500)

    return _json_ok({"script": script})


def _handle_routine(request: HttpRequest, user) -> JsonResponse:
    """AJAX handler: generate an AI daily routine."""
    try:
        routine = get_daily_routine(user)
    except Exception as exc:
        logger.exception("Routine generation failed for user %s", user.username)
        return _json_error(f"Routine error: {exc}", status=500)

    return _json_ok({"routine": routine})


def _handle_ghostwriter(request: HttpRequest, user) -> JsonResponse:
    """AJAX handler: generate an auto-reply."""
    sender = request.POST.get("sender", "").strip()
    message = request.POST.get("message", "").strip()

    if not sender or not message:
        return _json_error("Sender and Message cannot be empty.")

    try:
        reply = get_ghostwriter_reply(user, sender, message)
    except Exception as exc:
        logger.exception("Ghostwriter failed for user %s", user.username)
        return _json_error(f"Ghostwriter error: {exc}", status=500)

    return _json_ok({"reply": reply})


def _handle_update_settings(request: HttpRequest, user):
    """Form handler: update TwinSettings and optionally UserPreference."""
    twin_settings, _ = TwinSettings.objects.get_or_create(user=user)

    # ── TwinSettings fields ────────────────────────────────────
    twin_settings.bot_nickname        = request.POST.get("bot_nickname",        twin_settings.bot_nickname)        or twin_settings.bot_nickname
    twin_settings.preferred_language  = request.POST.get("preferred_language",  twin_settings.preferred_language)  or twin_settings.preferred_language
    twin_settings.last_mood           = request.POST.get("last_mood",           twin_settings.last_mood)           or twin_settings.last_mood
    twin_settings.custom_instructions = request.POST.get("custom_instructions", twin_settings.custom_instructions) or twin_settings.custom_instructions

    raw_tone = request.POST.get("tone_level", "")
    if raw_tone.isdigit():
        twin_settings.tone_level = int(raw_tone)

    twin_settings.save()
    logger.debug("TwinSettings updated for user %s", user.username)

    # ── UserPreference fields (optional section) ───────────────
    if "personality_traits" in request.POST:
        user_pref, _ = UserPreference.objects.get_or_create(user=user)
        user_pref.personality_traits = request.POST.get("personality_traits", user_pref.personality_traits) or user_pref.personality_traits
        user_pref.diet_preference    = request.POST.get("diet_preference",    user_pref.diet_preference)    or user_pref.diet_preference
        user_pref.sleep_cycle        = request.POST.get("sleep_cycle",        user_pref.sleep_cycle)        or user_pref.sleep_cycle
        user_pref.favorite_color     = request.POST.get("favorite_color",     user_pref.favorite_color)     or user_pref.favorite_color
        user_pref.save()
        logger.debug("UserPreference updated for user %s", user.username)

    return redirect("twin_dashboard")