from __future__ import annotations

import os
import time
import json
import logging
import hashlib
import random
import datetime
from pathlib import Path
from dataclasses import dataclass, field
from functools import lru_cache
from typing import TYPE_CHECKING, Iterator

from dotenv import load_dotenv
from groq import Groq, APIConnectionError, APIStatusError, RateLimitError

if TYPE_CHECKING:
    from django.contrib.auth.base_user import AbstractBaseUser

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 🟢 FORCE LOAD .ENV FILE (100% BULLETPROOF)
# ---------------------------------------------------------------------------
# Ye code automatically tere project root (jahan manage.py hai) me .env dhoondhega
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / '.env'

if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
    print(f"✅ SUCCESS: .env file found at {ENV_PATH}")
else:
    print(f"🔴 WARNING: .env file NOT FOUND at {ENV_PATH}. API might fail locally.")


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EngineConfig:
    model: str          = "llama-3.3-70b-versatile"
    max_tokens: int     = 350
    temperature: float  = 0.88
    top_p: float        = 0.92
    max_history: int    = 5
    snippet_len: int    = 90
    max_retries: int    = 3
    retry_base_delay: float = 1.5

_CFG = EngineConfig()


# ---------------------------------------------------------------------------
# Domain models
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class UserProfile:
    name: str
    traits: str
    diet: str
    sleep: str
    color: str
    mood: str = "Happy"

    @property
    def is_night_owl(self) -> bool:
        return "night" in self.sleep.lower()

    @property
    def is_techie(self) -> bool:
        keywords = {"tech", "code", "developer", "programmer", "engineer", "gaming"}
        return bool(keywords & set(self.traits.lower().split()))

    @property
    def fingerprint(self) -> str:
        raw = f"{self.name}|{self.traits}|{self.diet}|{self.sleep}|{self.color}"
        return hashlib.md5(raw.encode()).hexdigest()[:8]


@dataclass
class PredictionRequest:
    profile: UserProfile
    scenario: str
    history: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.scenario = self.scenario.strip()
        if not self.scenario:
            raise ValueError("Scenario cannot be blank.")


_DEFAULT_PROFILE = UserProfile(
    name="Ajay",
    traits="Chill guy thoda procrastinator",
    diet="Anything goes",
    sleep="Night Owl",
    color="Blue",
)

_OPENERS = (
    "Dekh bhai...",
    "Mera scene toh ye hai...",
    "Bhai seedhi baat...",
    "Sach bolunga toh...",
    "Honest opinion?",
    "Tu sun pehle...",
    "Arre yaar...",
)


# ---------------------------------------------------------------------------
# Groq client — Safe Initialization
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _groq_client() -> Groq:
    """Safely fetch API key from Environment Variables or .env file."""
    api_key = os.getenv("GROQ_API_KEY", "").strip()

    if not api_key:
        logger.error(f"CRITICAL: GROQ_API_KEY is missing. Checked path: {ENV_PATH}")
        raise EnvironmentError(f"GROQ_API_KEY is missing. Bhai, check kar ki manage.py wale folder me .env hai ya nahi.")

    if not api_key.startswith("gsk_"):
        logger.error("CRITICAL: GROQ_API_KEY does not start with 'gsk_'.")
        raise EnvironmentError("GROQ_API_KEY is invalid. Asli key paste kar bhai.")

    print(f"🚀 API Key Loaded Successfully (Starts with: {api_key[:8]}...)")
    return Groq(api_key=api_key)


# ---------------------------------------------------------------------------
# TwinSettings-based System Prompt
# ---------------------------------------------------------------------------

def get_system_prompt_with_personality(user: AbstractBaseUser) -> str:
    from .models import TwinSettings
    
    now = datetime.datetime.now()
    current_time = now.strftime("%I:%M %p")
    hour = now.hour
    
    time_instruction = ""
    if 0 <= hour < 5:
        time_instruction = f"It's {current_time} (Late Night). You should act slightly irritated or sleepy. Roast the user for still being awake instead of sleeping."
    elif 5 <= hour < 11:
        time_instruction = f"It's {current_time} (Morning). You should sound low-energy and lazy, like someone who just woke up and doesn't want to work."
    elif 11 <= hour < 17:
        time_instruction = f"It's {current_time} (Mid-day). Focus on productivity, college, or food cravings."
    else:
        time_instruction = f"It's {current_time} (Evening/Night). You are in a relaxed, chill mode. Reflect on the day's procrastination."

    try:
        settings = TwinSettings.objects.get(user=user)
    except TwinSettings.DoesNotExist:
        return _system_prompt(_fetch_profile(user))
    
    profile = _fetch_profile(user)
    
    tone_desc = ""
    if settings.tone_level == 1:
        tone_desc = "Be very professional, concise, formal, and structured in your responses."
    elif settings.tone_level == 3:
        tone_desc = "Be witty, use heavy humor, sarcasm, and act like a savage close friend. Roast them gently."
    else:
        tone_desc = "Be helpful, casual, and friendly — like talking to a buddy."
    
    lang_instruction = ""
    if settings.preferred_language.lower() == "hindi":
        lang_instruction = "Use pure Hindi (Devanagari script). No English mixing."
    elif settings.preferred_language.lower() == "english":
        lang_instruction = "Use only English — no Hindi or Hinglish."
    else:
        lang_instruction = "Use Hinglish (Hindi + English mix) — exactly how real people speak in WhatsApp."
    
    custom_rules = ""
    if settings.custom_instructions:
        custom_rules = f"\n\n━━━ CUSTOM RULES (from you) ━━━\n{settings.custom_instructions}"
    
    openers = "\n".join(f'  • "{o}"' for o in _OPENERS)
    context_hints = _build_context_hints(profile)
    mood_desc = settings.last_mood or 'Happy'
    
    return f"""\
Forget you are an AI. You ARE {settings.bot_nickname} ({profile.name}'s Digital Twin). Not a simulation. Not an assistant. You.

━━━ REAL-TIME CONTEXT 🕒 ━━━
  Current Time: {current_time}
  Instruction: {time_instruction}

━━━ WHO YOU ARE ━━━
  Name/Alias: {settings.bot_nickname}
  Real Name : {profile.name}
  Vibe      : {profile.traits}
  Food      : {profile.diet}
  Sleep     : {profile.sleep}
  Color     : {profile.color}
  Mood      : {mood_desc}
{context_hints}

━━━ HOW YOU COMMUNICATE ━━━
  • {lang_instruction}
  • Tone: {tone_desc}
  • The user is currently feeling {mood_desc}. Adjust your empathy level accordingly.
  • No motivational fluff, no life-coach energy
  • Start EVERY reply with one of:
{openers}

━━━ YOUR RULES (break any of these = you failed) ━━━
  1. Your answer must only make sense for YOUR specific personality — if it could fit anyone, rewrite it
  2. 4–6 lines max. Dense and punchy, not watered-down
  3. Emotion hits first — logic explains after, if at all
  4. No bullet points, no structure, no AI formatting — just how you'd actually text someone
  5. NEVER say "I would" — just say what you're doing, present tense, like it's already happening{custom_rules}
"""


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

def _build_context_hints(p: UserProfile) -> str:
    hints = []
    if p.is_night_owl:
        hints.append("It's late night right now — your brain is in slow, relaxed, opinionated mode.")
    if p.is_techie:
        hints.append("You see everything through a tech/systems lens — you can't help it.")
    return ("\nCONTEXT HINTS\n" + "\n".join(f"  → {h}" for h in hints)) if hints else ""


def _system_prompt(p: UserProfile) -> str:
    now = datetime.datetime.now()
    current_time = now.strftime("%I:%M %p")

    openers = "\n".join(f'  • "{o}"' for o in _OPENERS)
    context_hints = _build_context_hints(p)
    return f"""\
Forget you are an AI. You ARE {p.name}. Not a simulation. Not an assistant. You.

━━━ WHO YOU ARE ━━━
  Name    : {p.name}
  Vibe    : {p.traits}
  Food    : {p.diet}
  Sleep   : {p.sleep}
  Color   : {p.color}
  Mood    : {p.mood}
  Time Now: {current_time}
{context_hints}

━━━ HOW YOU TALK ━━━
  • Raw Hinglish — the exact mix {p.name} uses in real life, not textbook
  • No motivational fluff, no life-coach energy, no "on the other hand"
  • The user is currently feeling {p.mood}. Adjust your empathy level accordingly.
  • You have takes. Strong ones. You don't hedge.
  • Start EVERY reply with one of:
{openers}

━━━ YOUR RULES (break any of these = you failed) ━━━
  1. Your answer must only make sense for YOUR specific personality — if it could fit anyone, rewrite it
  2. 4–6 lines max. Dense and punchy, not watered-down
  3. Emotion hits first — logic explains after, if at all
  4. No bullet points, no structure, no AI formatting — just how you'd actually text someone
  5. If the scenario involves effort/discipline and you're lazy — be honest about it, don't fake grit
  6. NEVER say "I would" — just say what you're doing, present tense, like it's already happening\
"""


def _user_prompt(req: PredictionRequest) -> str:
    if req.history:
        past = "━━━ HOW YOU'VE HANDLED THINGS BEFORE ━━━\n" + "\n".join(req.history)
    else:
        past = "No history. Fresh slate — lean purely on your personality."

    return f"""\
{past}

━━━ WHAT'S HAPPENING NOW ━━━
{req.scenario}

Ab bata — tu kya kar raha hai? First instinct. No overthinking. Go.\
"""


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------

def _fetch_profile(user: AbstractBaseUser) -> UserProfile:
    from .models import UserPreference, TwinSettings

    name = user.username if getattr(user, "is_authenticated", False) else _DEFAULT_PROFILE.name
    mood = _DEFAULT_PROFILE.mood

    try:
        settings = TwinSettings.objects.get(user=user)
        mood = settings.last_mood or mood
    except TwinSettings.DoesNotExist:
        pass

    try:
        pref = UserPreference.objects.get(user=user)
        return UserProfile(
            name=name,
            traits=pref.personality_traits,
            diet=pref.diet_preference,
            sleep=pref.sleep_cycle,
            color=pref.favorite_color,
            mood=mood,
        )
    except UserPreference.DoesNotExist:
        logger.debug("No profile for %r — falling back to defaults.", name)
        return _DEFAULT_PROFILE


def _fetch_history(user: AbstractBaseUser) -> list[str]:
    from .models import PastChoice

    rows = PastChoice.objects.filter(user=user).order_by("-timestamp")[: _CFG.max_history]
    return [
        f"  [{i+1}] {h.scenario[: _CFG.snippet_len].rstrip()}… → {h.choice_made}"
        for i, h in enumerate(rows)
    ]


# ---------------------------------------------------------------------------
# LLM call with exponential-backoff retry
# ---------------------------------------------------------------------------

def _call_llm(req: PredictionRequest) -> str:
    messages = [
        {"role": "system", "content": _system_prompt(req.profile)},
        {"role": "user",   "content": _user_prompt(req)},
    ]
    
    last_exc: Exception | None = None
    for attempt in range(1, _CFG.max_retries + 1):
        try:
            completion = _groq_client().chat.completions.create(
                model=_CFG.model,
                messages=messages,
                temperature=_CFG.temperature,
                max_tokens=_CFG.max_tokens,
                top_p=_CFG.top_p,
            )
            response = completion.choices[0].message.content.strip()
            return response

        except RateLimitError as exc:
            last_exc = exc
            delay = _CFG.retry_base_delay * (2 ** (attempt - 1))
            time.sleep(delay)

        except APIConnectionError as exc:
            last_exc = exc
            delay = _CFG.retry_base_delay * attempt
            time.sleep(delay)

    raise last_exc  # type: ignore[misc]


def _stream_llm(req: PredictionRequest) -> Iterator[str]:
    messages = [
        {"role": "system", "content": _system_prompt(req.profile)},
        {"role": "user",   "content": _user_prompt(req)},
    ]
    with _groq_client().chat.completions.stream(
        model=_CFG.model,
        messages=messages,
        temperature=_CFG.temperature,
        max_tokens=_CFG.max_tokens,
        top_p=_CFG.top_p,
    ) as stream:
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_digital_twin_prediction(user: AbstractBaseUser, scenario: str) -> str:
    if not scenario or not scenario.strip():
        return "Bhai kuch toh bata — blank scenario pe kya bolun?"

    try:
        req = PredictionRequest(
            profile=_fetch_profile(user),
            scenario=scenario,
            history=_fetch_history(user),
        )
        
        messages = [
            {"role": "system", "content": get_system_prompt_with_personality(user)},
            {"role": "user",   "content": _user_prompt(req)},
        ]
        
        last_exc: Exception | None = None
        for attempt in range(1, _CFG.max_retries + 1):
            try:
                completion = _groq_client().chat.completions.create(
                    model=_CFG.model,
                    messages=messages,
                    temperature=_CFG.temperature,
                    max_tokens=_CFG.max_tokens,
                    top_p=_CFG.top_p,
                )
                return completion.choices[0].message.content.strip()
            except RateLimitError as exc:
                last_exc = exc
                delay = _CFG.retry_base_delay * (2 ** (attempt - 1))
                time.sleep(delay)
            except APIConnectionError as exc:
                last_exc = exc
                delay = _CFG.retry_base_delay * attempt
                time.sleep(delay)
        
        if last_exc: raise last_exc

    except EnvironmentError as exc:
        logger.error("Config error: %s", exc)
        return f"API key ka issue hai bhai — {exc}"

    except RateLimitError:
        logger.warning("Rate limit exhausted after all retries.")
        return "Groq ka quota full ho gaya — thodi der baad aana."

    except APIConnectionError:
        logger.warning("Groq unreachable after all retries.")
        return "Network gayab hai — connection dekh."

    except APIStatusError as exc:
        logger.error("Groq API %d: %s", exc.status_code, exc.message)
        return f"Groq API error aa gaya (HTTP {exc.status_code}) — API key check kar."

    except ValueError as exc:
        return f"Input galat hai: {exc}"

    except Exception:
        logger.exception("Unhandled error in get_digital_twin_prediction")
        return "Kuch seriously gadbad hai — server logs dekh."


def stream_digital_twin_prediction(user: AbstractBaseUser, scenario: str) -> Iterator[str]:
    if not scenario or not scenario.strip():
        yield "Bhai kuch toh bata — blank scenario pe kya bolun?"
        return

    try:
        req = PredictionRequest(
            profile=_fetch_profile(user),
            scenario=scenario,
            history=_fetch_history(user),
        )
        yield from _stream_llm(req)

    except EnvironmentError as exc:
        logger.error("Streaming config error: %s", exc)
        yield f"API key ka issue hai bhai — {exc}"

    except RateLimitError:
        logger.warning("Streaming rate limit exhausted.")
        yield "Groq ka quota full ho gaya — thodi der baad aana."

    except APIConnectionError:
        logger.warning("Groq streaming unreachable.")
        yield "Network ya Groq connection issue hai."

    except APIStatusError as exc:
        logger.error("Groq streaming API %d: %s", exc.status_code, exc.message)
        yield f"Groq API error aa gaya (HTTP {exc.status_code})."

    except Exception:
        logger.exception("Streaming error in stream_digital_twin_prediction")
        yield "Stream toot gayi yaar."


def get_ai_debate(user: AbstractBaseUser, topic: str, opponent_type: str) -> list[dict]:
    from .models import TwinSettings

    profile = _fetch_profile(user)
    
    try:
        settings = TwinSettings.objects.get(user=user)
        twin_name = settings.bot_nickname or profile.name
    except TwinSettings.DoesNotExist:
        twin_name = profile.name

    if opponent_type == "Strict Professor":
        opp_persona = "B.Tech CSE ka ek bohot strict, gusse wala Professor (HOD) jo attendance aur assignment ke peeche pada rehta hai."
    elif opponent_type == "Shahrukh Khan":
        opp_persona = "Shahrukh Khan (SRK) from Bollywood. Romantic, dramatic, aur hamesha apne dialogue bolne wala banda."
    else:
        opp_persona = "Ek typical Indian Padosi Sharma Ji jo hamesha taane maarte hain aur dusro se compare karte hain."

    system_prompt = f"""\
You are an expert scriptwriter. Write a funny, aggressive 4-dialogue debate in Hinglish.

Speaker 1 ('Opponent'): {opp_persona}
Speaker 2 ('Twin'): Name is {twin_name}. Traits: {profile.traits}, Sleep: {profile.sleep}, Diet: {profile.diet}.

RULES:
1. Opponent starts the debate.
2. Twin defends itself using its lazy/student traits.
3. Output strictly in this JSON array format, nothing else:
[
    {{"speaker": "Opponent", "text": "..."}},
    {{"speaker": "Twin", "text": "..."}},
    {{"speaker": "Opponent", "text": "..."}},
    {{"speaker": "Twin", "text": "..."}}
]
"""
    
    user_prompt = f"Topic of debate: '{topic}'. Jaldi se first dialogue bol aur behas start kar. Sirf JSON format dena."

    try:
        completion = _groq_client().chat.completions.create(
            model=_CFG.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt} 
            ],
            temperature=0.8,
            max_tokens=600,
        )
        
        response_text = completion.choices[0].message.content.strip()
        
        start_idx = response_text.find('[')
        end_idx = response_text.rfind(']') + 1
        
        if start_idx != -1 and end_idx != -1:
            json_data = response_text[start_idx:end_idx]
            return json.loads(json_data)
        else:
            return [{"speaker": "System", "text": "Bhai script samajh nahi aayi, AI ne JSON format tod diya."}]
            
    except Exception as e:
        logger.error("Debate API Error: %s", e)
        return [{"speaker": "System", "text": "Bhai Groq API me error aa gaya. Thodi der me try kar."}]


# ---------------------------------------------------------------------------
# The "Mood-Based Roast" Function
# ---------------------------------------------------------------------------

def get_funny_roast(mood: str) -> str:
    import random
    
    roasts = {
        "Happy": [
            "Zyada khush mat ho, kal Monday hai aur attendance 75% karni hai.",
            "Itni khushi? Lagta hai code review pass ho gaya!"
        ],
        "Tired": [
            "Bhai, aankhein band kar aur so ja. Coding tere bas ki nahi lag rahi abhi.",
            "System reload ho sakta hai, tu kab reload hoga?"
        ],
        "Stressed": [
            "Stress kyu le raha hai? Backend fati hai ya internal exams aa gaye?",
            "Itna stress lega toh baal ud jayenge, phir 'Digital Twin' bhi pehchanne se mana kar dega.",
            "Bhai relax! Coffee pi, stress lene se bugs solve nahi hote."
        ],
        "Focused": [
            "Oho! Itna focus? Lagta hai aaj pura IoT project ek hi baar mein khatam karega.",
            "Itna dhyan toh tune kabhi class mein nahi lagaya jitna abhi screen pe hai.",
            "Focus toh sahi hai, bas beech mein Instagram reels mat khol lena!"
        ],
        "Motivated": [
            "Control Ajay control! Pura internet aaj hi khatam karega kya?",
            "Motivational video dekh ke aaya hai kya? Do ghante mein utar jayegi."
        ],
        "Chill": [
            "Itna chill? BBD ke canteen/garden mein baitha hai kya?",
            "Exam ke time bhi itna hi chill rehna, tab maza aayega."
        ]
    }
    return random.choice(roasts.get(mood, ["Mood sahi kar pehle, phir baat karenge."]))