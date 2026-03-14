import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import logging
from scipy import stats

logger = logging.getLogger(__name__)


class RiskAnalyzer:
    """Comprehensive risk analysis framework for personal finance"""
    
    @staticmethod
    def calculate_financial_risks(monthly_income: float, monthly_expenses: float,
                                  current_balance: float, fixed_obligations: float = 0,
                                  health_insurance_coverage: float = 0,
                                  life_insurance_coverage: float = 0) -> Dict:
        """
        Calculate multiple financial risk indicators
        Args:
            monthly_income: Monthly income
            monthly_expenses: Monthly expenses
            current_balance: Current savings
            fixed_obligations: Fixed monthly debt (EMI, loans, etc.)
            health_insurance_coverage: Health insurance amount covered
            life_insurance_coverage: Life insurance coverage amount
        Returns:
            Comprehensive risk analysis
        """
        
        risks = {
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'risk_metrics': {},
            'risk_alerts': [],
            'mitigation_strategies': []
        }
        
        # 1. Income Risk (Volatility in income)
        income_stability = RiskAnalyzer._assess_income_stability(monthly_income)
        risks['risk_metrics']['income_stability'] = income_stability
        
        # 2. Liquidity Risk
        liquidity_ratio = current_balance / (monthly_expenses * 3) if monthly_expenses > 0 else 0
        liquidity_risk = RiskAnalyzer._calculate_liquidity_risk(liquidity_ratio)
        risks['risk_metrics']['liquidity_risk'] = liquidity_risk
        
        if liquidity_ratio < 1:
            risks['risk_alerts'].append({
                'type': 'CRITICAL',
                'title': 'Low Liquidity',
                'description': f'Current balance covers only {liquidity_ratio:.1%} of 3 months expenses',
                'severity': 'High'
            })
        
        # 3. Debt Burden Risk
        if monthly_income > 0:
            debt_to_income = (fixed_obligations / monthly_income) * 100
        else:
            debt_to_income = 0
        
        debt_risk = RiskAnalyzer._assess_debt_risk(debt_to_income)
        risks['risk_metrics']['debt_to_income_ratio'] = {
            'percentage': float(debt_to_income),
            'risk_level': debt_risk['risk_level'],
            'assessment': debt_risk['assessment']
        }
        
        if debt_to_income > 40:
            risks['risk_alerts'].append({
                'type': 'WARNING',
                'title': 'High Debt Burden',
                'description': f'Debt obligations are {debt_to_income:.1f}% of income',
                'severity': 'High'
            })
        
        # 4. Insurance Gap Risk
        insurance_gap = RiskAnalyzer._assess_insurance_gap(
            monthly_income, monthly_expenses, 
            health_insurance_coverage, life_insurance_coverage
        )
        risks['risk_metrics']['insurance_gap'] = insurance_gap
        
        if insurance_gap['health_gap'] > 50000:
            risks['risk_alerts'].append({
                'type': 'WARNING',
                'title': 'Inadequate Health Insurance',
                'description': f'Health insurance gap: ₹{insurance_gap["health_gap"]:,.0f}',
                'severity': 'Medium'
            })
        
        # 5. Income Volatility Risk
        volatility_risk = {
            'assessment': 'Moderate - typical salaried income',
            'risk_level': 'LOW' if income_stability['stability_score'] > 75 else 'MEDIUM'
        }
        risks['risk_metrics']['income_volatility'] = volatility_risk
        
        # Generate mitigation strategies
        risks['mitigation_strategies'] = RiskAnalyzer._generate_risk_mitigation_strategies(
            risks, monthly_income, monthly_expenses, current_balance
        )
        
        # Overall Risk Score (0-100)
        risks['overall_risk_score'] = RiskAnalyzer._calculate_overall_risk_score(risks)
        risks['risk_rating'] = RiskAnalyzer._get_risk_rating(risks['overall_risk_score'])
        
        return risks
    
    @staticmethod
    def _assess_income_stability(monthly_income: float) -> Dict:
        """Assess income stability"""
        # Simplified assessment - in real scenario would use historical income data
        return {
            'score': 85,  # Baseline assumption
            'stability_score': 85,
            'assessment': 'Stable salaried income assumed',
            'volatility_level': 'LOW'
        }
    
    @staticmethod
    def _calculate_liquidity_risk(liquidity_ratio: float) -> Dict:
        """Calculate liquidity risk based on cash ratio"""
        if liquidity_ratio >= 1:
            risk_level = 'LOW'
            assessment = 'Excellent liquidity position'
            score = 20
        elif liquidity_ratio >= 0.5:
            risk_level = 'MEDIUM'
            assessment = 'Adequate liquid reserves'
            score = 50
        elif liquidity_ratio >= 0.25:
            risk_level = 'HIGH'
            assessment = 'Low liquidity - vulnerable to emergencies'
            score = 75
        else:
            risk_level = 'CRITICAL'
            assessment = 'Critically low liquidity - immediate action needed'
            score = 95
        
        return {
            'liquidity_ratio': float(liquidity_ratio),
            'risk_level': risk_level,
            'assessment': assessment,
            'risk_score': score
        }
    
    @staticmethod
    def _assess_debt_risk(debt_to_income_percent: float) -> Dict:
        """Assess debt burden risk"""
        if debt_to_income_percent <= 20:
            risk_level = 'LOW'
            assessment = 'Healthy debt levels'
        elif debt_to_income_percent <= 30:
            risk_level = 'LOW-MEDIUM'
            assessment = 'Acceptable debt levels'
        elif debt_to_income_percent <= 40:
            risk_level = 'MEDIUM'
            assessment = 'Moderate debt burden'
        elif debt_to_income_percent <= 50:
            risk_level = 'HIGH'
            assessment = 'High debt burden - limit further borrowing'
        else:
            risk_level = 'CRITICAL'
            assessment = 'Excessive debt - prioritize repayment'
        
        return {
            'risk_level': risk_level,
            'assessment': assessment
        }
    
    @staticmethod
    def _assess_insurance_gap(monthly_income: float, monthly_expenses: float,
                             health_coverage: float, life_coverage: float) -> Dict:
        """Assess insurance coverage gaps"""
        
        # Health insurance benchmark: 5x annual expenses
        recommended_health = monthly_expenses * 12 * 5
        health_gap = max(0, recommended_health - health_coverage)
        
        # Life insurance: 10-15x annual income
        recommended_life = monthly_income * 12 * 10
        life_gap = max(0, recommended_life - life_coverage)
        
        return {
            'health_insurance_gap': float(health_gap),
            'recommended_health_coverage': float(recommended_health),
            'current_health_coverage': float(health_coverage),
            'life_insurance_gap': float(life_gap),
            'recommended_life_coverage': float(recommended_life),
            'current_life_coverage': float(life_coverage),
            'coverage_status': 'Inadequate' if (health_gap > 0 or life_gap > 0) else 'Adequate'
        }
    
    @staticmethod
    def _generate_risk_mitigation_strategies(risks: Dict, monthly_income: float, 
                                           monthly_expenses: float, current_balance: float) -> List[Dict]:
        """Generate personalized risk mitigation strategies"""
        strategies = []
        
        # Liquidity risk mitigation
        if risks['risk_metrics']['liquidity_risk']['risk_level'] in ['MEDIUM', 'HIGH', 'CRITICAL']:
            strategies.append({
                'priority': 'CRITICAL',
                'category': 'Liquidity',
                'action': 'Build Emergency Fund',
                'target': f'₹{monthly_expenses * 6:,.0f}',
                'timeline': '6-12 months',
                'details': 'Save 3-6 months of expenses for emergencies'
            })
        
        # Debt risk mitigation
        if risks['risk_metrics']['debt_to_income_ratio']['percentage'] > 30:
            strategies.append({
                'priority': 'HIGH',
                'category': 'Debt Management',
                'action': 'Accelerate Debt Repayment',
                'target': 'Reduce DTI ratio to <30%',
                'timeline': '12-24 months',
                'details': 'Allocate 10-15% of income to debt reduction'
            })
        
        # Insurance gap mitigation
        health_gap = risks['risk_metrics']['insurance_gap'].get('health_insurance_gap', 0)
        if health_gap > 0:
            strategies.append({
                'priority': 'HIGH',
                'category': 'Insurance',
                'action': 'Increase Health Coverage',
                'target': f'₹{health_gap:,.0f} additional coverage',
                'timeline': 'Immediately',
                'details': 'Purchase healthcare insurance to protect against medical emergencies'
            })
        
        # Income diversification
        if risks['risk_metrics']['income_volatility']['risk_level'] == 'MEDIUM':
            strategies.append({
                'priority': 'MEDIUM',
                'category': 'Income',
                'action': 'Diversify Income Sources',
                'target': 'Add 10-20% supplementary income',
                'timeline': '3-6 months',
                'details': 'Develop side income to reduce dependency on single source'
            })
        
        # Investment diversification
        strategies.append({
            'priority': 'MEDIUM',
            'category': 'Investment',
            'action': 'Diversify Portfolio',
            'target': 'Hold 5+ asset classes',
            'timeline': 'Ongoing',
            'details': 'Diversify across stocks, bonds, real estate, gold, and cash'
        })
        
        return strategies[:5]  # Return top 5 strategies
    
    @staticmethod
    def _calculate_overall_risk_score(risks: Dict) -> int:
        """Calculate composite risk score"""
        scores = []
        
        # Get individual risk scores
        scores.append(risks['risk_metrics']['liquidity_risk'].get('risk_score', 50))
        
        # Debt risk
        dti = risks['risk_metrics']['debt_to_income_ratio']['percentage']
        debt_score = min(95, max(10, dti * 2))
        scores.append(debt_score)
        
        # Insurance gap
        gap_score = 30 if risks['risk_metrics']['insurance_gap']['coverage_status'] == 'Adequate' else 60
        scores.append(gap_score)
        
        # Income volatility
        vol_score = 25 if risks['risk_metrics']['income_volatility']['risk_level'] == 'LOW' else 55
        scores.append(vol_score)
        
        # Average weighted score
        overall_score = int(np.mean(scores))
        return min(100, max(10, overall_score))
    
    @staticmethod
    def _get_risk_rating(risk_score: int) -> str:
        """Get risk rating based on score"""
        if risk_score < 25:
            return 'Very Low Risk 🟢'
        elif risk_score < 45:
            return 'Low Risk 🟢'
        elif risk_score < 60:
            return 'Moderate Risk 🟡'
        elif risk_score < 75:
            return 'High Risk 🔴'
        else:
            return 'Very High Risk 🔴'


class VaRCalculator:
    """Value at Risk (VaR) and Expected Shortfall calculations"""
    
    @staticmethod
    def calculate_portfolio_var(portfolio_values: np.ndarray, confidence_level: float = 0.95) -> Dict:
        """
        Calculate Value at Risk for portfolio based on historical returns
        Args:
            portfolio_values: Historical portfolio value series
            confidence_level: Confidence level (0.95 = 95%)
        Returns:
            VaR metrics
        """
        if len(portfolio_values) < 10:
            return {'error': 'Need at least 10 historical values'}
        
        # Calculate returns
        returns = np.diff(portfolio_values) / portfolio_values[:-1]
        
        # VaR using historical method
        var_percentile = (1 - confidence_level) * 100
        var = np.percentile(returns, var_percentile)
        
        # Expected Shortfall (CVaR)
        es = returns[returns <= var].mean() if any(returns <= var) else var
        
        return {
            'status': 'success',
            'confidence_level': confidence_level * 100,
            'value_at_risk': float(var),
            'expected_shortfall': float(es),
            'interpretation': f'There is a {confidence_level*100:.0f}% chance monthly loss won\'t exceed {abs(var)*100:.2f}%',
            'worst_case_scenario': f'Worst 5% scenario: {min(returns)*100:.2f}% loss'
        }
    
    @staticmethod
    def stress_test_portfolio(current_balance: float, asset_allocation: Dict[str, float],
                             stress_scenarios: List[str] = None) -> Dict:
        """
        Stress test portfolio against market scenarios
        Args:
            current_balance: Current portfolio value
            asset_allocation: Asset allocation percentages
            stress_scenarios: Custom scenarios or use defaults
        Returns:
            Stress test results for various scenarios
        """
        
        # Default stress scenarios
        if stress_scenarios is None:
            stress_scenarios = ['market_crash', 'stagflation', 'recession', 'currency_weakness']
        
        # Impact on different assets in each scenario
        scenario_impacts = {
            'market_crash': {
                'Equity (Large Cap)': -0.30,
                'Equity (Mid Cap)': -0.40,
                'Equity (Small Cap)': -0.50,
                'Gold': +0.15,
                'Government Bonds': +0.10,
                'Corporate Bonds': -0.15,
                'Real Estate': -0.20,
                'Cryptocurrency': -0.60,
                'Cash/Savings': 0.00
            },
            'stagflation': {
                'Equity (Large Cap)': -0.10,
                'Equity (Mid Cap)': -0.20,
                'Equity (Small Cap)': -0.25,
                'Gold': +0.20,
                'Government Bonds': -0.15,
                'Corporate Bonds': -0.10,
                'Real Estate': +0.10,
                'Cryptocurrency': -0.30,
                'Cash/Savings': 0.00
            },
            'recession': {
                'Equity (Large Cap)': -0.25,
                'Equity (Mid Cap)': -0.35,
                'Equity (Small Cap)': -0.45,
                'Gold': +0.10,
                'Government Bonds': +0.15,
                'Corporate Bonds': -0.20,
                'Real Estate': -0.25,
                'Cryptocurrency': -0.50,
                'Cash/Savings': 0.00
            },
            'currency_weakness': {
                'Equity (Large Cap)': -0.05,
                'Equity (Mid Cap)': -0.10,
                'Equity (Small Cap)': -0.15,
                'Gold': +0.05,
                'Government Bonds': +0.05,
                'Corporate Bonds': -0.05,
                'Real Estate': +0.08,
                'Cryptocurrency': +0.10,
                'Cash/Savings': 0.00
            }
        }
        
        results = {
            'status': 'success',
            'current_portfolio_value': float(current_balance),
            'stress_test_results': {}
        }
        
        for scenario in stress_scenarios:
            if scenario not in scenario_impacts:
                continue
            
            scenario_impact = scenario_impacts[scenario]
            portfolio_change = 0
            
            for asset, allocation_pct in asset_allocation.items():
                if asset in scenario_impact:
                    portfolio_change += allocation_pct * scenario_impact[asset]
            
            new_value = current_balance * (1 + portfolio_change)
            loss = current_balance - new_value
            
            results['stress_test_results'][scenario.replace('_', ' ').title()] = {
                'portfolio_change_percent': portfolio_change * 100,
                'new_portfolio_value': float(new_value),
                'loss_amount': float(loss),
                'recovery_estimate': f'{abs(portfolio_change) * 12:.0f} months' if portfolio_change < 0 else 'N/A'
            }
        
        return results


class SensitivityAnalyzer:
    """Sensitivity analysis for financial plans"""
    
    @staticmethod
    def sensitivity_to_returns(initial_investment: float, annual_contribution: float,
                              years: int, base_return_rate: float = 0.10) -> Dict:
        """
        Analyze portfolio sensitivity to different return rates
        Args:
            initial_investment: Starting amount
            annual_contribution: Annual investment amount
            years: Investment period
            base_return_rate: Base return assumption
        Returns:
            Sensitivity analysis showing outcomes at various return rates
        """
        
        return_rates = [0.06, 0.08, 0.10, 0.12, 0.14, 0.16]
        results = {
            'status': 'success',
            'sensitivity_analysis': {}
        }
        
        for rate in return_rates:
            fv = initial_investment
            for year in range(years):
                fv = fv * (1 + rate) + annual_contribution
            
            total_invested = initial_investment + (annual_contribution * years)
            returns_earned = fv - total_invested
            
            results['sensitivity_analysis'][f'{rate*100:.0f}%'] = {
                'future_value': float(fv),
                'total_returns': float(returns_earned),
                'roi_percent': (returns_earned / total_invested) * 100 if total_invested > 0 else 0
            }
        
        return results
    
    @staticmethod
    def sensitivity_to_inflation(annual_expense: float, inflation_rate: float, years: int) -> Dict:
        """
        Show impact of inflation on required corpus
        Args:
            annual_expense: Current annual expense
            inflation_rate: Expected inflation rate
            years: Years until retirement
        Returns:
            Inflation impact on required retirement corpus
        """
        
        inflation_rates = [0.04, 0.05, 0.06, 0.07, 0.08]
        results = {
            'status': 'success',
            'current_annual_expense': float(annual_expense),
            'years_until_retirement': years,
            'inflation_impact': {}
        }
        
        for rate in inflation_rates:
            future_expense = annual_expense * ((1 + rate) ** years)
            corpus_needed = future_expense / 0.04  # 4% rule
            
            results['inflation_impact'][f'{rate*100:.0f}%'] = {
                'future_annual_expense': float(future_expense),
                'corpus_needed_4pct_rule': float(corpus_needed),
                'corpus_increase_vs_today': float(corpus_needed - (annual_expense / 0.04))
            }
        
        return results
