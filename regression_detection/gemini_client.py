import os

import httpx
from google import genai
from google.genai import errors, types
from tenacity import RetryCallState, retry, retry_if_exception, stop_after_attempt, wait_exponential

RETRY_ATTEMPTS = 4
_BACKOFF = wait_exponential(multiplier=15, max=60)


def make_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY not set (put it in .env)")
    # Time out a hung call so generate retries it instead of waiting forever
    return genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=30_000))


def _should_retry(error: BaseException) -> bool:
    if isinstance(error, (httpx.TimeoutException, httpx.ConnectError, errors.ServerError)):
        return True
    return isinstance(error, errors.ClientError) and error.code in (408, 429)


def _wait(retry_state: RetryCallState) -> float:
    error = retry_state.outcome.exception()
    if isinstance(error, errors.ClientError) and error.code == 429:
        return _retry_delay(error)
    return _BACKOFF(retry_state)


def _retry_delay(error: errors.ClientError) -> float:
    for detail in error.details["error"]["details"]:
        if "retryDelay" in detail:
            return float(detail["retryDelay"].removesuffix("s"))
    # Wait out the per-minute window when Gemini gives no delay
    return 60


def _is_daily_limit(error: errors.ClientError) -> bool:
    for detail in error.details["error"]["details"]:
        for violation in detail.get("violations", []):
            if "PerDay" in violation["quotaId"]:
                return True
    return False


def _describe(error: BaseException) -> str:
    if isinstance(error, errors.APIError):
        return f"{error.code} {error.status}"
    return type(error).__name__


def _log_retry(retry_state: RetryCallState):
    model = retry_state.kwargs["model"]
    reason = _describe(retry_state.outcome.exception())
    delay = retry_state.next_action.sleep
    print(f"  {model}: {reason}, retrying in {delay:.0f}s (attempt {retry_state.attempt_number} of {RETRY_ATTEMPTS})")


@retry(
    retry=retry_if_exception(_should_retry),
    wait=_wait,
    stop=stop_after_attempt(RETRY_ATTEMPTS),
    before_sleep=_log_retry,
    reraise=True,
)
def generate(client: genai.Client, model: str, contents: list, config: types.GenerateContentConfig):
    try:
        return client.models.generate_content(model=model, contents=contents, config=config)
    except errors.ClientError as error:
        if error.code == 429 and _is_daily_limit(error):
            raise SystemExit(f"Daily request limit reached for {model}. {error.message}") from error
        raise
