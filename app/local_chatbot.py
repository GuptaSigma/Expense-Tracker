"""
Local AI Fin-Buddy Chatbot (No External API Required)
Works with user's balance and market data to provide smart financial advice
"""

import random
import logging
from typing import Optional, Dict, Any
from datetime import datetime

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

class LocalAIChatbot:
    """Local chatbot for financial advice without external API dependency"""
    
    def __init__(self):
        """Initialize local chatbot"""
        self.model_name = "local-financial-advisor"
        logger.info("✓ Local AI Chatbot initialized (no API key needed)")
    
    def get_financial_context(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract financial context for analysis"""
        return {
            'balance': user_data.get('balance', 0),
            'username': user_data.get('username', 'User'),
            'gold_price': user_data.get('market_data', {}).get('gold_price', 0),
            'bitcoin_price': user_data.get('market_data', {}).get('bitcoin_price', 0),
            'nifty_50': user_data.get('market_data', {}).get('nifty_50', 0),
            'sp500': user_data.get('market_data', {}).get('sp500', 0),
            'expenses': user_data.get('expenses', {}),
        }
    
    def _get_balance_response(self, context: Dict, language: str = "english") -> str:
        """Response for balance-related queries"""
        balance = context['balance']
        username = context['username']
        
        if language == "english":
            if balance < 5000:
                return f"Hi {username}, your balance is quite low - ₹{balance:,.0f}. Your first goal should be creating an emergency fund (3 months of expenses). 💰"
            elif balance < 50000:
                return f"Your balance is good - ₹{balance:,.0f}. Try saving 50% and investing 50% of your income. 📈"
            else:
                return f"Great! You have ₹{balance:,.0f}. Consider diversifying: Gold 10%, Stocks 40%, Cash 50%. 🎯"
        else:  # hindi
            if balance < 5000:
                return f"Bhai {username}, tera balance kaafi kam hai - ₹{balance:,.0f}. Tera first goal emergency fund banana chahiye: 3 months ka kharcha alag se rakh! 💰"
            elif balance < 50000:
                return f"Tera balance theek hai - ₹{balance:,.0f}. Ab tera 50% savings mein rakh aur 50% investment mein try kar! 📈"
            else:
                return f"Bahut acha! Tera balance ₹{balance:,.0f} hai. Ab tu diversify kar: Gold 10%, Stocks 40%, Cash 50% rakna theek rahega! 🎯"
    
    def _get_spending_response(self, context: Dict, language: str = "english") -> str:
        """Response for spending analysis"""
        expenses = context['expenses']
        balance = context['balance']
        
        if language == "english":
            if not expenses:
                return "You don't have any tracked expenses yet. Add them and I'll analyze your spending! 📊"
            
            total_spending = sum(expenses.values())
            highest_category = max(expenses.items(), key=lambda x: x[1]) if expenses else None
            
            if highest_category:
                category, amount = highest_category
                savings = int(amount * 0.1)
                return f"Your highest expense is {category} - ₹{amount:,.0f}. You could save ₹{savings:,.0f} by reducing here! 💡"
            
            if total_spending > balance * 0.3:
                return f"Your monthly spending is ₹{total_spending:,.0f} - that's too much. Follow the 30% rule: spend only 30% of income! 🎯"
            else:
                return f"Your spending is under control! Keep managing smartly! 👍"
        else:  # hindi
            if not expenses:
                return "Abhi teri koi spending track nahi ho rahi. Add karo na expenses aur main analysis doon! 📊"
            
            total_spending = sum(expenses.values())
            highest_category = max(expenses.items(), key=lambda x: x[1]) if expenses else None
            
            if highest_category:
                category, amount = highest_category
                return f"Tera {category} kharcha sabse zyada hai - ₹{amount:,.0f}. Yaha ₹{int(amount*0.1)} bacha sakta hai! 💡"
            
            if total_spending > balance * 0.3:
                return f"Tera monthly spend ₹{total_spending:,.0f} hai jo ki theek nahi. 30% rule follow kar - sirf 30% kharcha kar! 🎯"
            else:
                return f"Tera spending control mein hai! Keep karting smartly! 👍"
    
    def _get_market_response(self, context: Dict, language: str = "english") -> str:
        """Response for market-related queries"""
        gold_price = context['gold_price']
        bitcoin_price = context['bitcoin_price']
        nifty_50 = context['nifty_50']
        
        if language == "english":
            responses = [
                f"Gold is currently at ₹{gold_price:,.0f}/gram. Bitcoin is at ₹{bitcoin_price:,.0f}. Nifty 50 is at {nifty_50:,.0f}. Consider your risk profile before investing! 📊",
                f"Gold prices are stable. Bitcoin is more volatile. Diversify your investments across different assets! 🎯",
                f"Nifty 50 is at {nifty_50:,.0f}. A good time to invest in index funds if you have long-term goals! 📈"
            ]
        else:  # hindi
            responses = [
                f"Gold abhi ₹{gold_price:,.0f}/gram par hai. Bitcoin ₹{bitcoin_price:,.0f} par. Nifty 50 {nifty_50:,.0f} par hai. Apni risk profile dekh kar invest kar! 📊",
                f"Gold stable hai. Bitcoin volatile hai. Different assets mein invest kar - diversification zaruri hai! 🎯",
                f"Nifty 50 {nifty_50:,.0f} par hai. Long-term goals hain toh index funds sahi choice hain! 📈"
            ]
        
        return random.choice(responses)
    
    def _get_investment_response(self, context: Dict, language: str = "english") -> str:
        """Response for investment queries"""
        balance = context['balance']
        
        if language == "english":
            responses = [
                f"Start with your emergency fund first (3 months expenses). Then invest in index funds or ETFs. 💎",
                f"Your balance is ₹{balance:,.0f}. You can start with ₹{int(balance*0.3)} in stocks and keep ₹{int(balance*0.7)} safe. 🎯",
                f"SIP (Systematic Investment Plan) is best for beginners. Start with ₹500-1000 monthly! 📈",
                f"Don't chase quick returns. Invest for 5+ years and see wealth multiply! ⏳"
            ]
        else:  # hindi
            responses = [
                f"Pehle emergency fund banao (3 months ka kharcha). Phir index funds ya mutual funds mein invest kar! 💎",
                f"Tera balance ₹{balance:,.0f} hai. ₹{int(balance*0.3)} stocks mein aur ₹{int(balance*0.7)} safe rakho! 🎯",
                f"SIP se shuru kar - ₹500-1000 monthly. Ye best way hai beginners ke liye! 📈",
                f"Quick returns ki na soch. 5+ saal ke liye invest kar aur wealth dekh 10x ho jayega! ⏳"
            ]
        
        return random.choice(responses)
    
    def _get_goal_response(self, context: Dict, language: str = "english") -> str:
        """Response for goals and planning"""
        balance = context['balance']
        
        if language == "english":
            goal_responses = [
                f"Start an emergency fund with ₹{int(balance*0.5)}. Then work towards your goals! 🎯",
                f"Long-term goals need consistent investing. Start now and compound will do the magic! 💫",
                f"Set SMART goals - Specific, Measurable, Achievable, Relevant, Time-bound! 📝",
                f"Review your goals every 6 months and adjust your investments accordingly! 📊"
            ]
        else:  # hindi
            goal_responses = [
                f"Pehle emergency fund banao ₹{int(balance*0.5)} ka. Phir apne goals par kaam kar! 🎯",
                f"Long-term goals ke liye consistent invest kar. Compound interest ka magic dekh! 💫",
                f"Goals theek handle kar - specific, measurable, achievable, relevant, time-bound! 📝",
                f"6 mahine mein apne goals review kar aur investments adjust kar! 📊"
            ]
        
        return random.choice(goal_responses)
    
    def _get_general_response(self, user_message: str, language: str = "english") -> str:
        """General financial advice responses"""
        if language == "english":
            general_responses = [
                "Start small but start today! Invest and build wealth! 🚀",
                "Use the Rule of 72: divide 72 by your interest rate to find how long money doubles! 📊",
                "Your biggest asset is time, not money! Invest early! ⏳",
                "Save first, spend later - this is the rule of successful people! 💎",
                "Diversification is key - don't put all eggs in one basket! 🎯",
                "Markets go down but recover. Stay invested for the long-term! 📈",
                "Create a monthly budget and track it - this is the most important step! 📝",
                "Think twice before any financial decision, especially spending! 🤔",
            ]
        else:  # hindi
            general_responses = [
                "Bhai, start small but start today! Paise invest karna shuru kar na! 🚀",
                "Rule of 72: tera paisa mere interest rate se divide karke 72 divide karke dekh - kaab double hoga! 📊",
                "Teri biggest asset tera paisa nahi, tera time hai! Jaldi invest kar! ⏳",
                "Save pehle, spend baad mein - ye hi successful logo ka rule hai! 💎",
                "Diversification key hai - saara paisa ek jagah mat rakh! 🎯",
                "Market mein sab down hone se panic mat kar - long term mein up aata hai! 📈",
                "Monthly budget banao aur track karo - ye sab se important step! 📝",
                "Kisi bhi decision se pehle 2 baar soch - specially paison ke! 🤔",
            ]
        
        return random.choice(general_responses)
    
    def chat(self, user_message: str, user_data: Dict[str, Any]) -> str:
        """
        Generate response based on user message and financial context
        
        Args:
            user_message: User's question/message
            user_data: User's financial context
            
        Returns:
            Smart financial advice response
        """
        try:
            # Detect language from user message
            language = detect_language(user_message)
            
            message_lower = user_message.lower()
            context = self.get_financial_context(user_data)
            
            # Balance-related queries
            if any(word in message_lower for word in ['balance', 'paisa', 'how much', 'kitna', 'mere pas', 'available']):
                return self._get_balance_response(context, language)
            
            # Spending/expense queries
            elif any(word in message_lower for word in ['spend', 'expense', 'kharcha', 'spending', 'cost', 'category']):
                return self._get_spending_response(context, language)
            
            # Market queries
            elif any(word in message_lower for word in ['gold', 'bitcoin', 'crypto', 'nifty', 'market', 'stock', 'trend', 'price']):
                return self._get_market_response(context, language)
            
            # Investment queries
            elif any(word in message_lower for word in ['invest', 'investment', 'portfolio', 'fund', 'mutual', 'trading']):
                return self._get_investment_response(context, language)
            
            # Goal-related queries
            elif any(word in message_lower for word in ['goal', 'plan', 'future', 'retire', 'wedding', 'house', 'save']):
                return self._get_goal_response(context, language)
            
            # Default general response
            else:
                return self._get_general_response(user_message, language)
            
        except Exception as e:
            logger.error(f"Chat error: {str(e)}")
            language = detect_language(user_message)
            if language == "english":
                return "Let me help you. Please try asking again! 🤖"
            else:
                return "Ek second mere server ko time de, phir dobara try kar! 🤖"
