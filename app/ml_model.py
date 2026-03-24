import numpy as np
from datetime import datetime, timedelta
from app.models import Expense, Income
from flask import current_app
from sklearn.linear_model import LinearRegression
from collections import defaultdict
import requests
import json
import logging

logger = logging.getLogger(__name__)

# Import advanced ML modules
try:
    from app.advanced_ml import LSTMPredictor, ARIMAPredictor, EnsembleForecaster, GARCHVolatilityModel
except (ImportError, Exception) as e:
    logger.debug(f"Advanced ML not available: {str(e)}")

try:
    from app.financial_modeling import FinancialHealthAnalyzer, PortfolioOptimizer, FutureValueCalculator
except (ImportError, Exception):
    pass

try:
    from app.risk_analysis import RiskAnalyzer, VaRCalculator, SensitivityAnalyzer
except (ImportError, Exception):
    pass

class SpendingPredictor:
    def __init__(self):
        self.model = LinearRegression()
        self.ensemble_forecaster = EnsembleForecaster()
    
    def prepare_data(self, user_id):
        """Prepare historical spending data for prediction"""
        from app import db
        
        # Get last 30 days of expenses
        thirty_days_ago = datetime.now() - timedelta(days=30)
        expenses = Expense.query.filter(
            Expense.user_id == user_id,
            Expense.date >= thirty_days_ago
        ).order_by(Expense.date).all()
        
        if len(expenses) < 5:  # Not enough data
            return None, None
        
        # Prepare features (day of month) and target (amount)
        X = np.array([[e.date.day] for e in expenses])
        y = np.array([e.amount for e in expenses])
        
        return X, y
    
    def predict_next_month(self, user_id, use_advanced_ml=True):
        """
        Predict spending for next 30 days using advanced ML if available
        Args:
            user_id: User ID
            use_advanced_ml: Use ensemble forecasting (LSTM + ARIMA) instead of basic linear regression
        """
        from app import db
        
        # Prepare data
        X, y = self.prepare_data(user_id)
        
        if X is None or len(X) < 5:
            return {
                'total_predicted': 0,
                'daily_average': 0,
                'message': 'Not enough data for predictions. Add more expenses!',
                'model_used': 'none'
            }
        
        # Try advanced ML ensemble forecasting
        if use_advanced_ml and len(y) >= 20:
            try:
                ensemble_result = self.ensemble_forecaster.ensemble_forecast(y)
                if 'error' not in ensemble_result:
                    ensemble_result['model_used'] = 'Ensemble (LSTM + ARIMA)'
                    ensemble_result['message'] = f'Advanced ML prediction using {ensemble_result.get("model_confidence", "multiple models")}'
                    return ensemble_result
            except Exception as e:
                logger.warning(f"Ensemble forecasting failed: {str(e)}, falling back to Linear Regression")
        
        # Fallback to simple Linear Regression
        self.model.fit(X, y)
        future_days = np.array([[i] for i in range(1, 32)])
        predictions = self.model.predict(future_days)
        predictions = np.maximum(predictions, 0)
        
        total_predicted = sum(predictions)
        daily_avg = total_predicted / 30
        
        high_spending_days = []
        for i, pred in enumerate(predictions):
            if pred > daily_avg * 1.5:
                high_spending_days.append(i+1)
        
        return {
            'total_predicted': round(total_predicted, 2),
            'daily_average': round(daily_avg, 2),
            'high_spending_days': high_spending_days[:3],
            'message': f'Expected to spend ₹{round(total_predicted, 2)} next month',
            'model_used': 'Linear Regression (Baseline)'
        }


class ComprehensiveFinancialAnalysis:
    """Integrated financial analysis using advanced ML, financial modeling, and risk analysis"""
    
    def __init__(self):
        self.health_analyzer = FinancialHealthAnalyzer()
        self.risk_analyzer = RiskAnalyzer()
        self.portfolio_optimizer = PortfolioOptimizer()
        self.var_calculator = VaRCalculator()
        self.sensitivity_analyzer = SensitivityAnalyzer()
    
    def generate_comprehensive_report(self, user_id, user_balance, total_income, 
                                    total_expenses, age=30):
        """
        Generate comprehensive financial analysis report combining all modules
        Returns multi-faceted financial health assessment with ML predictions and risk analysis
        """
        from app import db
        from datetime import datetime, timedelta
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'sections': {}
        }
        
        # 1. Financial Health Analysis
        health_metrics = self.health_analyzer.calculate_financial_metrics(
            total_income, total_expenses, user_balance
        )
        report['sections']['financial_health'] = health_metrics
        
        # 2. Risk Analysis
        risk_analysis = self.risk_analyzer.calculate_financial_risks(
            total_income, total_expenses, user_balance
        )
        report['sections']['risk_assessment'] = risk_analysis
        
        # 3. Portfolio Optimization
        monthly_surplus = total_income - total_expenses
        if monthly_surplus > 0:
            recommended_allocation = self.portfolio_optimizer.generate_allocation(
                monthly_surplus, risk_profile='moderate', age=age
            )
            report['sections']['portfolio_recommendation'] = recommended_allocation
        
        # 4. Future Value Projections
        if monthly_surplus > 0:
            sip_projection = FutureValueCalculator.calculate_sip_returns(
                monthly_surplus, annual_return=0.12, years=20
            )
            report['sections']['20_year_sip_projection'] = sip_projection
        
        # 5. Retirement Planning
        retirement_plan = FutureValueCalculator.retirement_planner(
            age, retirement_age=60, annual_expenses=total_expenses * 12
        )
        report['sections']['retirement_plan'] = retirement_plan
        
        # 6. Sensitivity Analysis
        if monthly_surplus > 0:
            sensitivity = self.sensitivity_analyzer.sensitivity_to_returns(
                user_balance, monthly_surplus, years=20
            )
            report['sections']['sensitivity_analysis'] = sensitivity
        
        return report


class BudgetOptimizer:
    def generate_insights(self, user_id):
        """Generate AI insights about spending patterns"""
        from app import db
        
        insights = []
        
        # Category analysis
        categories = db.session.query(
            Expense.category, 
            db.func.sum(Expense.amount).label('total'),
            db.func.count(Expense.id).label('count')
        ).filter_by(user_id=user_id).group_by(Expense.category).all()
        
        if not categories:
            return ["Start adding expenses to get AI insights!"]
        
        # Find highest spending category
        if categories:
            top_category = max(categories, key=lambda x: x.total)
            insights.append(
                f"💰 Highest spending: {top_category.category} (₹{round(top_category.total, 2)})"
            )
        
        # Average transaction value
        total_spend = sum(c.total for c in categories)
        total_transactions = sum(c.count for c in categories)
        if total_transactions > 0:
            avg_transaction = total_spend / total_transactions
            insights.append(f"📊 Average transaction: ₹{round(avg_transaction, 2)}")
        
        # Budget suggestion
        if len(categories) >= 3:
            suggested_budget = round(total_spend * 0.9, 2)  # 10% less than current
            insights.append(
                f"🎯 Suggested monthly budget: ₹{suggested_budget} "
                f"(10% reduction saves ₹{round(total_spend * 0.1, 2)})"
            )
        
        # Anomaly detection (if any expense is 3x normal)
        for cat in categories:
            avg_per_transaction = cat.total / cat.count if cat.count > 0 else 0
            large_expenses = Expense.query.filter(
                Expense.user_id == user_id,
                Expense.category == cat.category,
                Expense.amount > avg_per_transaction * 3
            ).count()
            
            if large_expenses > 0:
                insights.append(
                    f"⚠️ Found {large_expenses} unusually large {cat.category} expenses!"
                )
        
        return insights[:5]  # Return top 5 insights
    
    def get_ai_suggestions(self, user_id):
        """Get AI-powered spending suggestions using OpenRouter API"""
        from app import db
        from config import Config
        
        try:
            # Get spending data
            categories = db.session.query(
                Expense.category,
                db.func.sum(Expense.amount).label('total'),
                db.func.count(Expense.id).label('count')
            ).filter_by(user_id=user_id).group_by(Expense.category).all()
            
            # Get income data
            total_income = db.session.query(db.func.sum(Income.amount))\
                .filter_by(user_id=user_id).scalar() or 0
            
            # Prepare spending summary
            spending_summary = "\n".join([
                f"- {cat.category}: ₹{round(cat.total, 2)} ({cat.count} transactions)"
                for cat in categories
            ])
            
            total_spend = sum(c.total for c in categories)
            
            # Create prompt for OpenRouter
            prompt = f"""Based on this spending data:
Total Monthly Income: ₹{round(total_income, 2)}
Total Monthly Spending: ₹{round(total_spend, 2)}

Spending by Category:
{spending_summary}

Provide 3-4 short, actionable budget optimization suggestions in ENGLISH ONLY. 
Keep suggestions professional, practical and specific to the spending patterns. Format as bullet points."""

            # Call OpenRouter API
            headers = {
                'Authorization': f'Bearer {Config.OPENROUTER_API_KEY}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'model': Config.OPENROUTER_MODEL,
                'messages': [
                    {'role': 'user', 'content': prompt}
                ],
                'temperature': 0.7,
                'max_tokens': 500
            }
            
            response = requests.post(
                Config.OPENROUTER_API_URL,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'choices' in data and len(data['choices']) > 0:
                    suggestion = data['choices'][0]['message']['content']
                    return suggestion
            
            # Fallback if API fails
            return "💡 Based on your spending, try reducing discretionary expenses by 10-15% and allocate that amount to savings or investments."
        
        except Exception as e:
            print(f"OpenRouter API Error: {str(e)}")
            return "💡 Keep tracking your expenses to get personalized savings recommendations."

    
    def get_investment_coach(self, user_id, user_balance, total_income, total_spend):
        """Get Gemini AI-powered investment coaching"""
        try:
            from app.market_data import get_market_data, get_investment_advice
            
            # Get market data
            market_data = get_market_data()
            
            # Get spending patterns
            categories = self._get_spending_breakdown(user_id)
            
            # Get investment recommendations
            spending_data = {'monthly_expenses': [c[1] for c in categories]}
            recommendations = get_investment_advice(user_balance, spending_data)
            
            # Prepare coaching info
            coaching_info = {
                'current_balance': user_balance,
                'monthly_income': total_income,
                'monthly_spending': total_spend,
                'savings_rate': ((total_income - total_spend) / total_income * 100) if total_income > 0 else 0,
                'gold_price': market_data['gold']['gold_price_24k'],
                'bitcoin_price': market_data['crypto']['bitcoin']['price'],
                'nifty_50': market_data['indices']['nifty_50']['price'],
                'top_recommendations': [r for r in recommendations if r['priority'] in ['critical', 'high']][:3]
            }
            
            # Generate coaching message
            prompt = f"""You are a financial investment coach for an Indian user. Provide personalized investment advice based on this profile:

Monthly Income: ₹{total_income:.2f}
Monthly Spending: ₹{total_spend:.2f}
Current Balance: ₹{user_balance:.2f}
Savings Rate: {coaching_info['savings_rate']:.1f}%

Current Market Rates (INR):
- Gold (24K): ₹{market_data['gold']['gold_price_24k']:.2f}/gram
- Bitcoin: ₹{market_data['crypto']['bitcoin']['price']:.2f}
- Nifty 50: {market_data['indices']['nifty_50']['price']:.2f}
- Bitcoin 24h Change: {market_data['crypto']['bitcoin']['change_24h']:.2f}%

Give 2-3 short, actionable investment suggestions in Hindi-influenced English. Focus on practical wealth building for Indians.
Keep it conversational and encouraging."""
            
            # Try to call OpenRouter API (fallback if needed)
            try:
                headers = {
                    'Authorization': f'Bearer {requests.get("http://localhost", timeout=0.001).status_code}',  # Dummy header
                    'Content-Type': 'application/json'
                }
                response = requests.post(
                    'https://openrouter.ai/api/v1/chat/completions',
                    headers=headers,
                    json={'messages': [{'role': 'user', 'content': prompt}]},
                    timeout=5
                )
                if response.status_code == 200:
                    return response.json()['choices'][0]['message']['content']
            except:
                pass
            
            # Return structured recommendations if API fails
            return self._format_investment_recommendations(coaching_info, recommendations)
        
        except Exception as e:
            logger.error(f"Investment coaching error: {str(e)}")
            return "💡 Focus on building a 3-6 month emergency fund first, then start SIPs in diversified index funds."
    
    def _get_spending_breakdown(self, user_id):
        """Helper to get spending breakdown"""
        from app import db
        return db.session.query(
            Expense.category,
            db.func.sum(Expense.amount).label('total')
        ).filter_by(user_id=user_id).group_by(Expense.category).all()

    def check_overspending(self, user_id, category):
        """Check if user is overspending in a category"""
        from app import db
        from datetime import datetime, timedelta

        # Get this month's spending in category
        first_of_month = datetime.now().replace(day=1)
        monthly_spent = db.session.query(db.func.sum(Expense.amount))\
            .filter(
                Expense.user_id == user_id,
                Expense.category == category,
                Expense.date >= first_of_month
            ).scalar() or 0

        # Get average monthly spending over recent history
        three_months_ago = datetime.now() - timedelta(days=90)
        avg_monthly = db.session.query(db.func.avg(Expense.amount))\
            .filter(
                Expense.user_id == user_id,
                Expense.category == category,
                Expense.date >= three_months_ago
            ).scalar() or 0

        return bool(avg_monthly > 0 and monthly_spent > avg_monthly * 0.8)
    
    def _format_investment_recommendations(self, coaching_info, recommendations):
        """Format recommendations into readable text"""
        msg = "🎯 **Investment Coaching Report**\n\n"
        msg += f"Your Savings Rate: {coaching_info['savings_rate']:.1f}% - "
        
        if coaching_info['savings_rate'] > 30:
            msg += "**Excellent! 💪 You're saving well.**\n\n"
        elif coaching_info['savings_rate'] > 20:
            msg += "**Good savings habit. Keep it up!**\n\n"
        else:
            msg += "**Focus on increasing savings rate.**\n\n"
        
        msg += "**Top Action Items:**\n"
        for i, rec in enumerate(recommendations[:3], 1):
            msg += f"{i}. {rec['asset']}: {rec['reason']}\n"
        
        return msg
