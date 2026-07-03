import requests
import logging
from typing import Any, Dict, List, Optional, Union


class LmStudioClient:
    """
    A client for interacting with LM Studio and other OpenAI-compatible APIs.
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:1234/v1",
        api_key: str = "not-needed",
        timeout=None,
    ):
        """
        Initialize the client.

        Args:
            base_url: The base URL of the API (e.g., "http://127.0.0.1:1234/v1").
            api_key: The API key (not typically needed for local servers).
            timeout: Timeout in seconds for request operations.
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)

    # ------------------------------------------------------------------
    # REPEAT DETECTION
    # ------------------------------------------------------------------
    @staticmethod
    def _detect_repeat(
        text: str,
        min_pattern=8,
        max_pattern=120,
        min_repetitions=3,
    ):
        n = len(text)

        for size in range(min_pattern, min(max_pattern, n // min_repetitions) + 1):

            pattern = text[-size:]

            repetitions = 1
            pos = n - size

            while pos - size >= 0 and text[pos-size:pos] == pattern:
                repetitions += 1
                pos -= size

            if repetitions >= min_repetitions:
                return text[:pos+size], True

        return False

    # ------------------------------------------------------------------
    # STREAMING WITH REPEAT DETECTION
    # ------------------------------------------------------------------
    def send_streaming(
        self,
        user: str,
        system: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        max_retries: int = 5,
    ) -> Optional[str]:
        """
        Stream a chat completion, detect repeat loops, retry on loop.

        Returns the best (longest) non-looped response, or the best partial
        response if all attempts looped.
        """
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user})

        best_response: Optional[str] = None

        for attempt in range(1, max_retries + 2):  # 1 original + max_retries
            try:
                response = self._stream_completion(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                # Successful (non-looped) response
                if response is not None and not response.startswith("[LOOPED] "):
                    content = response
                    if best_response is None or len(content) > len(best_response):
                        best_response = content
                    # If we got a good response, no need to retry
                    break
                else:
                    # Loop detected — save partial and retry
                    partial = response.replace("[LOOPED] ", "") if response else None
                    if partial and (best_response is None or len(partial) > len(best_response)):
                        best_response = partial

            except Exception as e:
                self.logger.error(f"Streaming attempt {attempt} failed: {e}")
                continue

        return best_response

    def _stream_completion(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Optional[str]:
        """
        Perform a single streaming chat completion.

        Returns the accumulated content string. If a repeat loop is detected,
        aborts early and returns content prefixed with ``[LOOPED] ``.
        """
        url = f"{self.base_url}/chat/completions"
        payload = {
            "messages": messages,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        payload = {k: v for k, v in payload.items() if v is not None}

        session = requests.Session()
        accumulated = []

        try:
            resp = session.post(
                url,
                headers=self._get_headers(),
                json=payload,
                timeout=self.timeout,
                stream=True,
            )
            resp.raise_for_status()

            for line in resp.iter_lines():
                if not line:
                    continue
                line_str = line.decode("utf-8") if isinstance(line, bytes) else line
                if not line_str.startswith("data: "):
                    continue
                data = line_str[6:]
                if data == "[DONE]":
                    break
                try:
                    import json
                    chunk = json.loads(data)
                    delta = (
                        chunk.get("choices", [{}])[0]
                        .get("delta", {})
                        .get("content", "")
                    )
                    if delta:
                        accumulated.append(delta)
                        print(delta, end="", flush=True)

                        # Check for repeats periodically (every 10 deltas)
                        if len(accumulated) % 10 == 0:
                            full = "".join(accumulated)
                            if self._detect_repeat(full):
                                # Strip the repeated tail
                                content = self._strip_repeat_tail(full)
                                return "[LOOPED] " + content
                except json.JSONDecodeError:
                    continue

            content = "".join(accumulated)
            return content

        except requests.RequestException as e:
            self.logger.error(f"Streaming error: {e}")
            content = "".join(accumulated)
            return content if content else None
        finally:
            session.close()

    @staticmethod
    def _strip_repeat_tail(text: str, window_size: int = 300) -> str:
        """Remove the repeating tail from text, keeping only the clean portion."""
        if len(text) <= window_size:
            return text
        return text[:-window_size]

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def list_models(self) -> Dict[str, Any]:
        """List available models."""
        url = f"{self.base_url}/models"
        try:
            response = requests.get(
                url, headers=self._get_headers(), timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            self.logger.error(f"Error listing models: {e}")
            raise

    def send(
        self,
        user: str,
        system: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Optional[str]:
        """
        Convenience wrapper for chat completions using system + user prompts.
        Returns assistant content or None on failure.
        """

        messages = []

        if system:
            messages.append({"role": "system", "content": system})

        messages.append({"role": "user", "content": user})

        try:
            response = self.chat_completions(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            # Safe extraction (prevents KeyError crashes)
            return response.get("choices", [{}])[0].get("message", {}).get("content")

        except Exception as e:
            self.logger.error(f"Chat completion failed in send(): {e}")
            return None

    def chat_completions(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stop: Optional[Union[str, List[str]]] = None,
        stream: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Create a chat completion.
        """
        url = f"{self.base_url}/chat/completions"
        payload = {
            "messages": messages,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stop": stop,
            "stream": stream,
        }
        # Remove None values to avoid sending them in the payload
        payload = {k: v for k, v in payload.items() if v is not None}

        try:
            response = requests.post(
                url, headers=self._get_headers(), json=payload, timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            self.logger.error(f"Error in chat completions: {e}")
            raise

    def completions(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stop: Optional[Union[str, List[str]]] = None,
        stream: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Create a completion.
        """
        url = f"{self.base_url}/completions"
        payload = {
            "prompt": prompt,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stop": stop,
            "stream": stream,
        }
        payload = {k: v for k, v in payload.items() if v is not None}

        try:
            response = requests.post(
                url, headers=self._get_headers(), json=payload, timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            self.logger.error(f"Error in completions: {e}")
            raise

    def embeddings(
        self,
        input: Union[str, List[str]],
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get embeddings for the given input.
        """
        url = f"{self.base_url}/embeddings"
        payload = {
            "input": input,
            "model": model,
        }
        payload = {k: v for k, v in payload.items() if v is not None}

        try:
            response = requests.post(
                url, headers=self._get_headers(), json=payload, timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            self.logger.error(f"Error in embeddings: {e}")
            raise

    def responses(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Create a response (custom endpoint provided by user).
        """
        url = f"{self.base_url}/responses"
        payload = {"messages": messages, "model": model, **kwargs}
        payload = {k: v for k, v in payload.items() if v is not None}

        try:
            response = requests.post(
                url, headers=self._get_headers(), json=payload, timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            self.logger.error(f"Error in responses: {e}")
            raise

    def __repr__(self) -> str:
        return f"<LmStudioAPI(base_url='{self.base_url}')>"
