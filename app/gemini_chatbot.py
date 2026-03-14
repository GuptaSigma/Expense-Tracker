"""
Gemini Powered AI Fin-Buddy Chatbot
Uses Google Gemini API for advanced financial advice
Falls back to OpenRouter, then to LocalAIChatbot if APIs fail
"""

import google.generativeai as genai
import requests
import logging
from typing import Optional, Dict, Any
from app.local_chatbot import LocalAIChatbot

logger = logging.getLogger(__name__)

def detect_language(text: str) -> str:
    """Detect if text is in English or Hindi/Hinglish"""
    # Hindi characters ranges: Devanagari script
    hindi_chars = 0
    total_chars = 0
    
    for char in text:
        # Count only letters (ignore spaces, punctuation, numbers)
        if char.isalpha() or ('\u0900' <= char <= '\u097F'):
            total_chars += 1
            # Devanagari script range (Hindi/Sanskrit)
            if '\u0900' <= char <= '\u097F':
                hindi_chars += 1
    
    # If more than 15% of letters are Hindi characters, treat as Hindi/Hinglish
    if total_chars > 0 and hindi_chars / total_chars > 0.15:
        return "hindi"
    
    # Check for Hindi keywords even if script is minimal
    hindi_keywords = ['mera', 'kitna', 'kya', 'hai', 'chahiye', 'karu', 'sone', 'kharcha', 'paisa', 'aapka', 'tera', 'mere']
    if any(keyword in text.lower() for keyword in hindi_keywords):
        return "hindi"
    
    return "english"

class GeminiChatbot:
    """Gemini-powered chatbot with OpenRouter + local fallback"""
    
    def __init__(self, gemini_key: str = None, openrouter_key: str = None, 
                 gemini_model: str = "gemini-2.0-flash", openrouter_model: str = "openai/gpt-4o-mini"):
        """Initialize Gemini chatbot with fallbacks"""
        try:
            self.gemini_key = gemini_key
            self.gemini_model = gemini_model
            self.openrouter_key = openrouter_key
            self.openrouter_model = openrouter_model
            
            if gemini_key:
                genai.configure(api_key=gemini_key)
                self.gemini_client = genai.GenerativeModel(gemini_model)
            else:
                self.gemini_client = None
            
            self.local_chatbot = LocalAIChatbot()  # Fallback
            logger.info(f"✓ Chatbot initialized: Gemini (primary) → OpenRouter (fallback) → Local (backup)")
        except Exception as e:
            logger.error(f"Chatbot init error: {str(e)}")
            self.gemini_client = None
            self.local_chatbot = LocalAIChatbot()
    
    def chat(self, message: str, user_context: Dict[str, Any]) -> str:
        """
        Get response from Gemini API with fallbacks
        1. Try Gemini API
        2. Fall back to OpenRouter
        3. Fall back to local chatbot
        """
        try:
            # Try Gemini first
            if self.gemini_client:
                return self._gemini_response(message, user_context)
        except Exception as e:
            logger.warning(f"Gemini failed: {str(e)[:100]}")
        
        # Try OpenRouter as fallback
        try:
            if self.openrouter_key:
                return self._openrouter_response(message, user_context)
        except Exception as e:
            logger.warning(f"OpenRouter failed: {str(e)[:100]}")
        
        # Fall back to local chatbot (always works)
        return self.local_chatbot.chat(message, user_context)
    
    def _gemini_response(self, message: str, user_context: Dict[str, Any]) -> str:
        """Get response from Gemini API"""
        username = user_context.get('username', 'User')
        balance = user_context.get('balance', 0)
        expenses = user_context.get('expenses', {})
        market_data = user_context.get('market_data', {})
        
        # Detect language of user message
        language = detect_language(message)
        
        if language == "hindi":
            response_lang = "Respond in Hindi/Hinglish mix (like: 'Tera balance theek hai, ab invest kar!')"
        else:
            response_lang = "Respond in clear, professional English. Break down complex concepts simply."
        
        prompt = f"""
You are an expert Indian financial advisor (Fin-Buddy) named "Fin-Buddy".
{response_lang}

USER CONTEXT:
- Name: {username}
- Current Balance: ₹{balance:,.0f}
- Monthly Expenses: {expenses}
- Market Prices:
  - Gold: ₹{market_data.get('gold_price', 'N/A')}/gram
  - Bitcoin: ₹{market_data.get('bitcoin_price', 'N/A')}
  - Nifty 50: {market_data.get('nifty_50', 'N/A')}

USER MESSAGE: "{message}"

INSTRUCTIONS:
1. Give practical, actionable financial advice
2. Reference their actual balance and expenses
3. Keep response concise (2-3 sentences)
4. Always be encouraging with emojis
5. Match the user's language preference
"""
        
        response = self.gemini_client.generate_content(prompt)
        return response.text.strip()
    
    def _openrouter_response(self, message: str, user_context: Dict[str, Any]) -> str:
        """Get response from OpenRouter API as fallback"""
        username = user_context.get('username', 'User')
        balance = user_context.get('balance', 0)
        expenses = user_context.get('expenses', {})
        market_data = user_context.get('market_data', {})
        
        # Detect language of user message
        language = detect_language(message)
        
        if language == "hindi":
            lang_instruction = "You are an expert Indian financial advisor. Always respond in Hindi/Hinglish."
            example = "Give 2-3 sentences in Hindi/Hinglish with practical advice and emojis."
        else:
            lang_instruction = "You are an expert Indian financial advisor. Always respond in clear, professional English."
            example = "Give 2-3 sentences in English with practical advice and emojis. Break down complex concepts simply."
        
        headers = {
            "Authorization": f"Bearer {self.openrouter_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:5000",
            "X-Title": "Fin-Buddy"
        }
        
        prompt = f"""
{lang_instruction}

USER: {username}, Balance: ₹{balance:,.0f}, Expenses: {expenses}

Market Data:
- Gold: ₹{market_data.get('gold_price', 'N/A')}/gram
- Bitcoin: ₹{market_data.get('bitcoin_price', 'N/A')}
- Nifty 50: {market_data.get('nifty_50', 'N/A')}

Question: {message}

{example}
"""
        
        payload = {
            "model": self.openrouter_model,
            "messages": [
                {
                    "role": "system",
                    "content": lang_instruction
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 200
        }
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get('choices', [{}])[0].get('message', {}).get('content', '')
        else:
            raise Exception(f"OpenRouter error: {response.status_code}")

