import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


class FinancialHealthAnalyzer:
    """Comprehensive financial health assessment"""
    
    @staticmethod
    def calculate_financial_metrics(monthly_income: float, monthly_expenses: float, 
                                    current_balance: float, savings_goal: float = None) -> Dict:
        """
        Calculate key financial health metrics
        Args:
            monthly_income: Monthly income in currency units
            monthly_expenses: Monthly expenses
            current_balance: Current account balance
            savings_goal: Target savings goal (optional)
        Returns:
            Dictionary with financial metrics
        """
        if monthly_income <= 0:
            return {'error': 'Monthly income must be positive'}
        
        monthly_surplus = monthly_income - monthly_expenses
        savings_rate = (monthly_surplus / monthly_income) * 100
        
        # Emergency fund analysis
        months_of_emergency_fund = current_balance / monthly_expenses if monthly_expenses > 0 else 0
        required_emergency_fund = monthly_expenses * 6  # 6 months standard
        emergency_fund_status = months_of_emergency_fund / 6 * 100  # % of recommended
        
        # Financial runway (how many months until money runs out)
        financial_runway = current_balance / monthly_expenses if monthly_expenses > current_balance else float('inf')
        
        # Debt capacity (how much can be safely borrowed)
        max_safe_debt = (monthly_income - monthly_expenses) * 60  # 5 years of surplus
        
        # Savings trajectory
        years_to_goal = None
        if savings_goal and monthly_surplus > 0:
            years_to_goal = (savings_goal - current_balance) / (monthly_surplus * 12) if savings_goal > current_balance else 0
        
        metrics = {
            'status': 'success',
            'monthly_income': float(monthly_income),
            'monthly_expenses': float(monthly_expenses),
            'monthly_surplus': float(monthly_surplus),
            'savings_rate_percent': float(savings_rate),
            'current_balance': float(current_balance),
            'emergency_fund_months': float(months_of_emergency_fund),
            'emergency_fund_status_percent': float(min(emergency_fund_status, 100)),
            'financial_runway_months': float(financial_runway) if financial_runway != float('inf') else -1,
            'max_safe_debt': float(max_safe_debt),
            'financial_health_score': FinancialHealthAnalyzer._calculate_health_score(
                savings_rate, 
                months_of_emergency_fund,
                monthly_surplus
            ),
            'recommendations': FinancialHealthAnalyzer._generate_recommendations(
                savings_rate,
                months_of_emergency_fund,
                monthly_surplus,
                financial_runway
            )
        }
        
        if years_to_goal:
            metrics['years_to_savings_goal'] = float(years_to_goal)
        
        return metrics
    
    @staticmethod
    def _calculate_health_score(savings_rate: float, emergency_months: float, surplus: float) -> Dict:
        """
        Calculate composite financial health score (0-100)
        """
        score = 0
        breakdown = {}
        
        # Savings rate component (0-30 points)
        if savings_rate >= 30:
            score += 30
            breakdown['savings_rate'] = 30
        elif savings_rate >= 20:
            score += 25
            breakdown['savings_rate'] = 25
        elif savings_rate >= 10:
            score += 20
            breakdown['savings_rate'] = 20
        elif savings_rate >= 0:
            score += 10
            breakdown['savings_rate'] = 10
        
        # Emergency fund component (0-30 points)
        if emergency_months >= 6:
            score += 30
            breakdown['emergency_fund'] = 30
        elif emergency_months >= 5:
            score += 25
            breakdown['emergency_fund'] = 25
        elif emergency_months >= 3:
            score += 20
            breakdown['emergency_fund'] = 20
        elif emergency_months >= 1:
            score += 10
            breakdown['emergency_fund'] = 10
        
        # Surplus component (0-40 points)
        if surplus > 0:
            score += 40
            breakdown['positive_cashflow'] = 40
        else:
            breakdown['positive_cashflow'] = 0
        
        return {
            'overall_score': int(score),
            'rating': FinancialHealthAnalyzer._get_rating(score),
            'breakdown': breakdown
        }
    
    @staticmethod
    def _get_rating(score: int) -> str:
        """Get rating based on score"""
        if score >= 90:
            return 'Excellent 🌟'
        elif score >= 75:
            return 'Good ✅'
        elif score >= 50:
            return 'Fair ⚠️'
        else:
            return 'Poor 🔴'
    
    @staticmethod
    def _generate_recommendations(savings_rate: float, emergency_months: float, 
                                  surplus: float, financial_runway: float) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Emergency fund recommendations
        if emergency_months < 1:
            recommendations.append('🚨 CRITICAL: Build emergency fund with at least 1-2 months of expenses')
        elif emergency_months < 3:
            recommendations.append('⚠️ Priority: Increase emergency fund to 3 months of expenses')
        elif emergency_months < 6:
            recommendations.append('📈 Goal: Build 6-month emergency fund for stability')
        else:
            recommendations.append('✅ Emergency fund is healthy')
        
        # Savings recommendations
        if savings_rate <= 0:
            recommendations.append('🔴 URGENT: Reduce expenses or increase income - currently building debt!')
        elif savings_rate < 10:
            recommendations.append('💡 Increase savings rate to at least 10-15% of income')
        elif savings_rate < 20:
            recommendations.append('📊 Good progress - aim for 20%+ savings rate')
        else:
            recommendations.append('🎯 Excellent savings rate - focus on investment optimization')
        
        # Debt capacity
        if surplus > 0:
            recommendations.append(f'💰 You can safely invest ₹{surplus * 12:,.0f}/year or borrow up to ₹{surplus * 60:,.0f}')
        
        return recommendations[:4]  # Return top 4 recommendations


class PortfolioOptimizer:
    """Modern Portfolio Theory (MPT) implementation"""
    
    def __init__(self):
        # Asset classes with expected returns and volatility (for Indian market context)
        self.asset_profiles = {
            'Equity (Large Cap)': {'return': 0.12, 'volatility': 0.15},
            'Equity (Mid Cap)': {'return': 0.14, 'volatility': 0.22},
            'Equity (Small Cap)': {'return': 0.16, 'volatility': 0.28},
            'Government Bonds': {'return': 0.06, 'volatility': 0.04},
            'Corporate Bonds': {'return': 0.08, 'volatility': 0.06},
            'Gold': {'return': 0.08, 'volatility': 0.12},
            'Real Estate': {'return': 0.10, 'volatility': 0.10},
            'Cryptocurrency': {'return': 0.20, 'volatility': 0.50},
            'Cash/Savings': {'return': 0.04, 'volatility': 0.00}
        }
    
    def generate_allocation(self, monthly_surplus: float, risk_profile: str = 'moderate', 
                           age: int = 30, months_to_retirement: int = 420) -> Dict:
        """
        Generate optimal portfolio allocation based on risk profile
        Args:
            monthly_surplus: Available monthly investment amount
            risk_profile: 'conservative', 'moderate', 'aggressive'
            age: Current age
            months_to_retirement: Months until retirement
        Returns:
            Recommended portfolio allocation and strategy
        """
        
        # Define allocation templates based on risk profile
        allocations = {
            'conservative': {
                'Government Bonds': 0.40,
                'Corporate Bonds': 0.20,
                'Equity (Large Cap)': 0.20,
                'Gold': 0.10,
                'Cash/Savings': 0.10
            },
            'moderate': {
                'Equity (Large Cap)': 0.40,
                'Equity (Mid Cap)': 0.15,
                'Government Bonds': 0.15,
                'Corporate Bonds': 0.10,
                'Gold': 0.10,
                'Real Estate': 0.05,
                'Cash/Savings': 0.05
            },
            'aggressive': {
                'Equity (Large Cap)': 0.30,
                'Equity (Mid Cap)': 0.25,
                'Equity (Small Cap)': 0.15,
                'Gold': 0.10,
                'Real Estate': 0.10,
                'Cryptocurrency': 0.05,
                'Corporate Bonds': 0.05
            }
        }
        
        if risk_profile not in allocations:
            risk_profile = 'moderate'
        
        allocation = allocations[risk_profile]
        
        # Calculate portfolio metrics
        portfolio_return = sum(allocation.get(asset, 0) * self.asset_profiles[asset]['return'] 
                             for asset in self.asset_profiles)
        portfolio_volatility = np.sqrt(sum(allocation.get(asset, 0)**2 * 
                                          self.asset_profiles[asset]['volatility']**2 
                                          for asset in self.asset_profiles))
        
        # Allocation breakdown
        investment_breakdown = {}
        annual_investment = monthly_surplus * 12
        for asset, percentage in allocation.items():
            investment_breakdown[asset] = {
                'allocation_percent': percentage * 100,
                'monthly_amount': monthly_surplus * percentage,
                'annual_amount': annual_investment * percentage
            }
        
        # Projection to retirement
        years_to_retirement = months_to_retirement / 12
        projected_value = (monthly_surplus * 12) * 12 * (((1 + portfolio_return)**years_to_retirement - 1) / portfolio_return) if portfolio_return > 0 else monthly_surplus * 12 * years_to_retirement
        
        return {
            'status': 'success',
            'risk_profile': risk_profile,
            'allocation': investment_breakdown,
            'expected_annual_return_percent': portfolio_return * 100,
            'portfolio_volatility_percent': portfolio_volatility * 100,
            'sharpe_ratio': (portfolio_return - 0.04) / portfolio_volatility if portfolio_volatility > 0 else 0,
            'monthly_investment': float(monthly_surplus),
            'annual_investment': float(annual_investment),
            'projected_value_at_retirement': float(projected_value),
            'years_to_retirement': float(years_to_retirement),
            'diversification_score': len([k for k, v in investment_breakdown.items() if v['monthly_amount'] > 0])
        }
    
    def rebalance_portfolio(self, current_portfolio: Dict[str, float], 
                           target_allocation: Dict[str, float],
                           total_value: float) -> Dict:
        """
        Calculate rebalancing adjustments to match target allocation
        Args:
            current_portfolio: Current holdings by asset {asset: percentage}
            target_allocation: Target allocation {asset: percentage}
            total_value: Total portfolio value
        Returns:
            Rebalancing actions needed
        """
        rebalancing_plan = {}
        
        for asset in target_allocation:
            current_pct = current_portfolio.get(asset, 0)
            target_pct = target_allocation[asset]
            difference = target_pct - current_pct
            
            if abs(difference) > 0.05:  # Only rebalance if >5% difference
                action = 'BUY' if difference > 0 else 'SELL'
                amount = abs(difference) * total_value
                
                rebalancing_plan[asset] = {
                    'action': action,
                    'current_percent': current_pct * 100,
                    'target_percent': target_pct * 100,
                    'amount': float(amount),
                    'priority': 'High' if abs(difference) > 0.10 else 'Medium'
                }
        
        return {
            'status': 'success',
            'rebalancing_needed': len(rebalancing_plan) > 0,
            'actions': rebalancing_plan,
            'total_to_invest': float(sum(v['amount'] for v in rebalancing_plan.values() if v['action'] == 'BUY'))
        }


class FutureValueCalculator:
    """Calculate future value of investments with various compounding methods"""
    
    @staticmethod
    def calculate_compound_growth(principal: float, annual_rate: float, 
                                  years: int, compounding_periods: int = 12) -> Dict:
        """
        Calculate compound growth of investment
        Args:
            principal: Initial investment
            annual_rate: Annual return rate (as decimal, e.g., 0.12 for 12%)
            years: Investment period in years
            compounding_periods: Periods per year (12=monthly, 4=quarterly, 1=annual)
        Returns:
            Future value and growth breakdown
        """
        rate_per_period = annual_rate / compounding_periods
        periods = years * compounding_periods
        
        future_value = principal * (1 + rate_per_period) ** periods
        total_interest = future_value - principal
        
        return {
            'status': 'success',
            'principal': float(principal),
            'annual_rate_percent': annual_rate * 100,
            'years': years,
            'future_value': float(future_value),
            'total_interest': float(total_interest),
            'interest_earned_percent': (total_interest / principal) * 100 if principal > 0 else 0,
            'effective_annual_rate': (future_value ** (1/years) - 1) * 100 if years > 0 else 0
        }
    
    @staticmethod
    def calculate_sip_returns(monthly_investment: float, annual_return: float, 
                             years: int) -> Dict:
        """
        Calculate returns from Systematic Investment Plan (SIP)
        Args:
            monthly_investment: Monthly investment amount
            annual_return: Annual return rate
            years: Investment period
        Returns:
            SIP value and returns breakdown
        """
        monthly_rate = annual_return / 12
        months = years * 12
        
        # Future value of annuity formula
        fv = monthly_investment * (((1 + monthly_rate) ** months - 1) / monthly_rate) * (1 + monthly_rate)
        total_invested = monthly_investment * months
        total_returns = fv - total_invested
        
        return {
            'status': 'success',
            'monthly_investment': float(monthly_investment),
            'annual_return_percent': annual_return * 100,
            'years': years,
            'total_invested': float(total_invested),
            'future_value': float(fv),
            'total_returns': float(total_returns),
            'return_on_investment_percent': (total_returns / total_invested) * 100 if total_invested > 0 else 0,
            'maturity_amount': float(fv)
        }
    
    @staticmethod
    def retirement_planner(current_age: int, retirement_age: int, 
                          annual_expenses: float, inflation_rate: float = 0.06) -> Dict:
        """
        Plan for retirement based on current age and lifestyle
        Args:
            current_age: Current age in years
            retirement_age: Target retirement age
            annual_expenses: Expected annual expenses
            inflation_rate: Expected inflation rate
        Returns:
            Retirement planning data
        """
        years_to_retirement = retirement_age - current_age
        
        if years_to_retirement <= 0:
            return {'error': 'Retirement age must be greater than current age'}
        
        # Estimate ages - simplified to 30 years post-retirement
        years_in_retirement = 30
        
        # Calculate expenses at retirement (adjusted for inflation)
        expenses_at_retirement = annual_expenses * (1 + inflation_rate) ** years_to_retirement
        
        # Total needed for retirement (simplified: annual expense * years in retirement, adjusted)
        total_needed = 0
        for year in range(years_in_retirement):
            year_expense = expenses_at_retirement * (1 + inflation_rate) ** year
            total_needed += year_expense
        
        # Using 4% rule for withdrawal rate
        corpus_needed_4pct = expenses_at_retirement / 0.04
        
        return {
            'status': 'success',
            'current_age': current_age,
            'retirement_age': retirement_age,
            'years_to_retirement': years_to_retirement,
            'current_annual_expense': float(annual_expenses),
            'projected_annual_expense_at_retirement': float(expenses_at_retirement),
            'total_corpus_needed_4pct_rule': float(corpus_needed_4pct),
            'total_corpus_needed_for_30yrs': float(total_needed),
            'yearly_inflation_rate_percent': inflation_rate * 100,
            'recommendation': f'Accumulate ₹{corpus_needed_4pct:,.0f} by age {retirement_age} using 4% withdrawal rule'
        }
