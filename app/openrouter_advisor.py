"""
OpenRouter Powered Investment Advisor
Uses OpenRouter API for advanced investment recommendations
"""

import requests
import logging
import json
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class OpenRouterAdvisor:
    """OpenRouter-powered investment advisor"""
    
    def __init__(self, api_key: str, model: str = "openai/gpt-4o-mini"):
        """Initialize OpenRouter advisor"""
        self.api_key = api_key
        self.model = model
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:5000",
            "X-Title": "Fin-Buddy"
        }
        logger.info(f"✓ OpenRouter Advisor initialized with model: {model}")
    
    def get_investment_advice(self, user_context: Dict[str, Any]) -> str:
        """Get investment advice from OpenRouter"""
        try:
            username = user_context.get('username', 'User')
            balance = user_context.get('balance', 0)
            expenses = user_context.get('expenses', {})
            market_data = user_context.get('market_data', {})
            
            # Calculate expense total
            total_expense = sum(expenses.values()) if expenses else 0
            
            prompt = f"""
You are an expert Indian financial advisor.
Provide investment recommendations in Hindi/Hinglish (e.g., "Tera portfolio mein 50% stocks, 30% gold, 20% cash rakna chahiye")

USER FINANCIAL PROFILE:
- Name: {username}
- Monthly Income: ₹{balance + total_expense:,.0f} (assumed)
- Monthly Expenses: ₹{total_expense:,.0f}
- Current Balance: ₹{balance:,.0f}
- Expense Categories: {json.dumps(expenses, ensure_ascii=False)}

CURRENT MARKET CONDITIONS:
- Gold Price: ₹{market_data.get('gold_price', 'N/A')}/gram
- Bitcoin: ₹{market_data.get('bitcoin_price', 'N/A')}
- Nifty 50: {market_data.get('nifty_50', 'N/A')}
- S&P 500: {market_data.get('sp500', 'N/A')}

Give 3-4 specific investment recommendations in Hindi/Hinglish based on:
1. Their balance and risk profile
2. Current market conditions
3. Long-term wealth building
4. Emergency fund (3 months expenses)

Keep it practical and actionable. Use emojis. Respond in Hindi/Hinglish.
"""
            
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert Indian financial advisor. Always respond in Hindi/Hinglish."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 500
            }
            
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                advice = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                logger.info("✓ Investment advice received from OpenRouter")
                return advice
            else:
                logger.error(f"OpenRouter error: {response.status_code} - {response.text}")
                return self._fallback_advice(user_context)
        
        except Exception as e:
            logger.error(f"OpenRouter request failed: {str(e)}")
            return self._fallback_advice(user_context)
    
    def _fallback_advice(self, user_context: Dict[str, Any]) -> str:
        """Fallback advice when API fails"""
        balance = user_context.get('balance', 0)
        
        if balance > 100000:
            return "Tera balance achha hai bhai! Ab 40% stocks, 30% gold, 20% bonds, 10% cash rakna chahiye. Long-term SIP start kar! 📈"
        elif balance > 50000:
            return "Balance theek hai. Emergency fund pehle banao (3 months ka kharcha). Uske baad 60% stocks, 30% gold, 10% cash. 💪"
        elif balance > 10000:
            return "Abhi savings badhane par focus kar. Monthly SIP shuru kar ₹5000 ka. Gold aur mutual funds mein invest kar. 🎯"
        else:
            return "Pehle income increase kar aur expenses control kar. Uske baad invest kar. Emergency fund banao priority! 💰"
