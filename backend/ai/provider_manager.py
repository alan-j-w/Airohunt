import os
import json
import httpx
from typing import Optional, Dict, Any

SETTINGS_FILE = "settings.json"

def get_ai_settings() -> Dict[str, str]:
    settings = {}
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                settings = json.load(f)
        except Exception:
            pass
            
    # Fallback to environment variables if not set in settings.json
    return {
        "active_provider": settings.get("active_provider") or os.getenv("AI_PROVIDER", "openai").lower(),
        "openai_api_key": settings.get("openai_api_key") or os.getenv("OPENAI_API_KEY", ""),
        "groq_api_key": settings.get("groq_api_key") or os.getenv("GROQ_API_KEY", ""),
        "gemini_api_key": settings.get("gemini_api_key") or os.getenv("GEMINI_API_KEY", ""),
        "ollama_url": settings.get("ollama_url") or os.getenv("OLLAMA_URL", "http://localhost:11434"),
    }

class ProviderManager:
    def __init__(self):
        self.settings = get_ai_settings()

    def refresh_settings(self):
        self.settings = get_ai_settings()

    async def call_llm(self, system_prompt: str, user_prompt: str, response_format_json: bool = False, provider: str = None) -> str:
        self.refresh_settings()
        
        target_provider = (provider or self.settings.get("active_provider") or "openai").lower()
        
        # Build the chain of attempts: Active Provider -> Fallbacks -> Local Heuristic Fallback
        chain = [target_provider]
        all_providers = ["openai", "groq", "gemini", "ollama"]
        
        for p in all_providers:
            if p not in chain:
                chain.append(p)
                
        # Try each in order
        for current_prov in chain:
            try:
                res = await self._execute_call(current_prov, system_prompt, user_prompt, response_format_json)
                if res:
                    return res
            except Exception as e:
                print(f"Provider {current_prov} failed: {str(e)}. Attempting next in chain...")
                
        # If all LLMs fail, raise exception to let heuristic layers run
        raise Exception("All configured AI providers failed.")

    async def _execute_call(self, provider: str, system_prompt: str, user_prompt: str, json_format: bool) -> Optional[str]:
        if provider == "openai":
            key = self.settings["openai_api_key"]
            if not key:
                raise ValueError("OpenAI key not configured")
            return await self._call_openai_compatible(
                base_url="https://api.openai.com/v1",
                api_key=key,
                model="gpt-4o-mini",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                json_format=json_format
            )
            
        elif provider == "groq":
            key = self.settings["groq_api_key"]
            if not key:
                raise ValueError("Groq key not configured")
            return await self._call_openai_compatible(
                base_url="https://api.groq.com/openai/v1",
                api_key=key,
                model="llama-3.1-8b-instant",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                json_format=json_format
            )
            
        elif provider == "gemini":
            key = self.settings["gemini_api_key"]
            if not key:
                raise ValueError("Gemini key not configured")
            return await self._call_gemini_api(key, system_prompt, user_prompt, json_format)
            
        elif provider == "ollama":
            url = self.settings["ollama_url"]
            # Call Ollama API (Llama3 or default)
            return await self._call_ollama_api(url, system_prompt, user_prompt, json_format)
            
        return None

    async def _call_openai_compatible(self, base_url: str, api_key: str, model: str, system_prompt: str, user_prompt: str, json_format: bool) -> str:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.2
        }
        if json_format:
            payload["response_format"] = {"type": "json_object"}

        async with httpx.AsyncClient() as client:
            response = await client.post(f"{base_url}/chat/completions", json=payload, headers=headers, timeout=12.0)
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]
            else:
                raise Exception(f"OpenAI-compatible API Error ({response.status_code}): {response.text}")

    async def _call_gemini_api(self, api_key: str, system_prompt: str, user_prompt: str, json_format: bool) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        
        prompt_combined = f"{system_prompt}\n\nUSER INPUT:\n{user_prompt}"
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt_combined}]
            }],
            "generationConfig": {
                "temperature": 0.2
            }
        }
        if json_format:
            payload["generationConfig"]["responseMimeType"] = "application/json"

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers, timeout=12.0)
            if response.status_code == 200:
                data = response.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return text
            else:
                raise Exception(f"Gemini API Error ({response.status_code}): {response.text}")

    async def _call_ollama_api(self, ollama_url: str, system_prompt: str, user_prompt: str, json_format: bool) -> str:
        # Tries to call Ollama on local host, defaulting to 'llama3' or 'mistral' or whatever model is loaded
        headers = {"Content-Type": "application/json"}
        payload = {
            "model": "llama3", # default target
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False,
            "options": {
                "temperature": 0.2
            }
        }
        if json_format:
            payload["format"] = "json"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(f"{ollama_url}/api/chat", json=payload, headers=headers, timeout=15.0)
                if response.status_code == 200:
                    data = response.json()
                    return data["message"]["content"]
                else:
                    raise Exception(f"Ollama API Error ({response.status_code}): {response.text}")
            except httpx.ConnectError:
                raise Exception("Ollama server is not running on localhost.")

    async def test_connection(self, provider: str, key: str, url: str = "") -> tuple[bool, str]:
        test_system = "You are a test assistant."
        test_user = "Reply with 'OK'."
        try:
            if provider == "openai":
                if not key or not key.strip():
                    return False, "API Key is empty. Please enter a valid OpenAI API key."
                res = await self._call_openai_compatible("https://api.openai.com/v1", key, "gpt-4o-mini", test_system, test_user, False)
            elif provider == "groq":
                if not key or not key.strip():
                    return False, "API Key is empty. Please enter a valid Groq API key."
                res = await self._call_openai_compatible("https://api.groq.com/openai/v1", key, "llama-3.1-8b-instant", test_system, test_user, False)
            elif provider == "gemini":
                if not key or not key.strip():
                    return False, "API Key is empty. Please enter a valid Gemini API key."
                res = await self._call_gemini_api(key, test_system, test_user, False)
            elif provider == "ollama":
                res = await self._call_ollama_api(url or "http://localhost:11434", test_system, test_user, False)
            else:
                return False, "Unknown AI Provider configuration selected."
            
            if res and "ok" in res.lower():
                return True, "Connection successful."
            return False, f"Unexpected response from provider: {res}"
        except Exception as e:
            print(f"Test connection failed for {provider}: {str(e)}")
            # Return user friendly messages for common errors
            err_str = str(e)
            if "401" in err_str or "unauthorized" in err_str.lower():
                return False, "Authentication failed. Please verify that your API key is correct and active."
            elif "429" in err_str or "rate limit" in err_str.lower() or "quota" in err_str.lower():
                return False, "Rate limit exceeded or insufficient quota/billing balance on this API key."
            return False, err_str
