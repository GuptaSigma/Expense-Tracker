from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Expense, Income, Watchlist, CategoryBudget
from app.ml_model import SpendingPredictor, BudgetOptimizer
from app.market_data import get_market_data, get_investment_advice, search_stocks, get_stock_price, get_all_sectors
from app.local_chatbot import LocalAIChatbot
from app.gemini_chatbot import GeminiChatbot
from app.openrouter_advisor import OpenRouterAdvisor
from flask import current_app
from datetime import datetime, timedelta
import json
import logging

logger = logging.getLogger(__name__)

main = Blueprint('main', __name__)
predictor = SpendingPredictor()
optimizer = BudgetOptimizer()

BUDGET_PERCENTAGES = {
    'Food': 16.67,
    'Transport': 10,
    'Entertainment': 6.67,
    'Shopping': 13.33,
    'Bills': 16.67,
    'Health': 10,
    'Education': 20,
    'Other': 6.67
}


def ensure_category_budget_table():
    CategoryBudget.__table__.create(bind=db.engine, checkfirst=True)


def get_budget_base_amount(total_income):
    return round(total_income if total_income > 0 else 30000, 2)


def get_default_budgets(total_income):
    budget_base = get_budget_base_amount(total_income)
    return {
        category: round(budget_base * (percentage / 100), 2)
        for category, percentage in BUDGET_PERCENTAGES.items()
    }


def get_custom_budget_map(user_id):
    custom_budget_rows = CategoryBudget.query.filter_by(user_id=user_id).all()
    return {row.category: float(row.amount) for row in custom_budget_rows if row.amount > 0}


def get_effective_budgets(user_id, total_income):
    default_budgets = get_default_budgets(total_income)
    custom_budgets = get_custom_budget_map(user_id)
    effective_budgets = {
        category: round(custom_budgets.get(category, default_limit), 2)
        for category, default_limit in default_budgets.items()
    }
    return default_budgets, custom_budgets, effective_budgets


def upsert_category_budget(user_id, category, amount):
    existing_budget = CategoryBudget.query.filter_by(user_id=user_id, category=category).first()
    if existing_budget:
        existing_budget.amount = amount
    else:
        db.session.add(CategoryBudget(user_id=user_id, category=category, amount=amount))
    return existing_budget

# Initialize Gemini Chatbot for chatbox (with OpenRouter + local fallback)
def get_chatbot():
    """Get or create Gemini chatbot instance with fallbacks"""
    if not hasattr(get_chatbot, 'instance'):
        gemini_key = current_app.config.get('GEMINI_API_KEY')
        gemini_model = current_app.config.get('GEMINI_MODEL', 'gemini-2.0-flash')
        openrouter_key = current_app.config.get('OPENROUTER_API_KEY')
        openrouter_model = current_app.config.get('OPENROUTER_MODEL', 'openai/gpt-4o-mini')
        
        # Try Gemini first, with OpenRouter as fallback
        get_chatbot.instance = GeminiChatbot(
            gemini_key=gemini_key,
            openrouter_key=openrouter_key,
            gemini_model=gemini_model,
            openrouter_model=openrouter_model
        )
    return get_chatbot.instance

# Initialize OpenRouter Advisor for investment suggestions
def get_openrouter_advisor():
    """Get or create OpenRouter advisor instance"""
    if not hasattr(get_openrouter_advisor, 'instance'):
        api_key = current_app.config.get('OPENROUTER_API_KEY')
        model = current_app.config.get('OPENROUTER_MODEL', 'openai/gpt-4o-mini')
        if api_key:
            get_openrouter_advisor.instance = OpenRouterAdvisor(api_key, model)
        else:
            get_openrouter_advisor.instance = None
    return get_openrouter_advisor.instance

@main.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('home.html')

@main.route('/dashboard')
@login_required
def dashboard():
    ensure_category_budget_table()

    # Get user's recent expenses
    recent_expenses_query = Expense.query.filter_by(user_id=current_user.id)\
        .order_by(Expense.date.desc()).limit(10).all()
    
    # Serialize expenses for JSON
    recent_expenses = recent_expenses_query
    recent_expenses_json = [{
        'date': expense.date.strftime('%Y-%m-%d'),
        'category': expense.category,
        'description': expense.description or '',
        'amount': float(expense.amount)
    } for expense in recent_expenses_query]
    
    # Calculate totals
    total_expense = db.session.query(db.func.sum(Expense.amount))\
        .filter_by(user_id=current_user.id).scalar() or 0
    
    total_income = db.session.query(db.func.sum(Income.amount))\
        .filter_by(user_id=current_user.id).scalar() or 0
    
    # Category breakdown
    categories = db.session.query(Expense.category, db.func.sum(Expense.amount))\
        .filter_by(user_id=current_user.id)\
        .group_by(Expense.category).all()
    
    # Prepare data for charts
    category_labels = [c[0] for c in categories]
    category_data = [float(c[1]) for c in categories]
    
    default_budgets, custom_budgets, effective_budgets = get_effective_budgets(
        current_user.id,
        total_income
    )
    
    # Calculate budget progress for each category
    budget_progress = []
    alerts = []  # Store alerts for categories
    for category, default_limit in default_budgets.items():
        budget_limit = effective_budgets[category]
        spent = db.session.query(db.func.sum(Expense.amount))\
            .filter_by(user_id=current_user.id, category=category).scalar() or 0
        percentage = (spent / budget_limit * 100) if budget_limit > 0 else 0
        
        # Determine status color based on 70% yellow and 85% red thresholds
        if percentage < 70:
            status = 'safe'
            color = 'green'
        elif percentage < 85:
            status = 'caution'
            color = 'yellow'
            # Add yellow alert
            alerts.append({
                'type': 'warning',
                'category': category,
                'percentage': percentage,
                'spent': float(spent),
                'limit': budget_limit,
                'message': f'{category} spending reached {percentage:.1f}% of budget'
            })
        else:
            status = 'danger'
            color = 'red'
            # Add red alert
            alerts.append({
                'type': 'critical',
                'category': category,
                'percentage': percentage,
                'spent': float(spent),
                'limit': budget_limit,
                'message': f'{category} exceeded {percentage:.1f}% of budget!'
            })
        
        budget_progress.append({
            'category': category,
            'spent': float(spent),
            'limit': budget_limit,
            'default_limit': default_limit,
            'is_custom': category in custom_budgets,
            'percentage': min(percentage, 100),
            'status': status,
            'color': color,
            'remaining': max(budget_limit - spent, 0)
        })
    
    # AI Predictions (with error handling)
    try:
        predictions = predictor.predict_next_month(current_user.id)
    except Exception as e:
        print(f"Predictions Error: {str(e)}")
        predictions = {
            'next_month_expense': 0,
            'savings_potential': 0,
            'trend': 'stable'
        }
    
    try:
        insights = optimizer.generate_insights(current_user.id)
    except Exception as e:
        print(f"Insights Error: {str(e)}")
        insights = []
    
    try:
        ai_suggestions = optimizer.get_ai_suggestions(current_user.id)
    except Exception as e:
        print(f"AI Suggestions Error: {str(e)}")
        ai_suggestions = []
    
    # Advanced Charts Data
    # 1. Daily expense trend (last 30 days)
    thirty_days_ago = datetime.now() - timedelta(days=29)  # Include today
    
    daily_expenses_query = db.session.query(
        db.func.date(Expense.date).label('day'),
        db.func.sum(Expense.amount).label('total')
    ).filter(
        Expense.user_id == current_user.id,
        Expense.date >= thirty_days_ago
    ).group_by(db.func.date(Expense.date)).all()
    
    # Fill in missing days with 0
    expense_trend_labels = []
    expense_trend_data = []
    daily_expenses_dict = {str(d.day): float(d.total) for d in daily_expenses_query}
    
    for i in range(30):
        day_date = (datetime.now() - timedelta(days=29-i))
        day_str = day_date.strftime('%Y-%m-%d')
        expense_trend_labels.append(day_date.strftime('%b %d'))
        expense_trend_data.append(daily_expenses_dict.get(day_str, 0))
    
    # 2. Monthly comparison (last 6 months)
    monthly_data = []
    current_date = datetime.now()
    
    for i in range(5, -1, -1):  # From 5 months ago to current month
        # Calculate month start properly
        year = current_date.year
        month = current_date.month - i
        
        # Handle year rollback
        while month <= 0:
            month += 12
            year -= 1
        
        month_start = datetime(year, month, 1)
        
        # Calculate next month start
        next_month = month + 1
        next_year = year
        if next_month > 12:
            next_month = 1
            next_year += 1
        month_end = datetime(next_year, next_month, 1)
        
        month_expense = db.session.query(db.func.sum(Expense.amount))\
            .filter(
                Expense.user_id == current_user.id,
                Expense.date >= month_start,
                Expense.date < month_end
            ).scalar() or 0
        
        month_income = db.session.query(db.func.sum(Income.amount))\
            .filter(
                Income.user_id == current_user.id,
                Income.date >= month_start,
                Income.date < month_end
            ).scalar() or 0
        
        monthly_data.append({
            'month': month_start.strftime('%b %Y'),
            'income': float(month_income),
            'expense': float(month_expense)
        })
    
    monthly_labels = [m['month'] for m in monthly_data]
    monthly_income_data = [m['income'] for m in monthly_data]
    monthly_expense_data = [m['expense'] for m in monthly_data]
    
    # Get user's watchlist (latest 10)
    user_watchlist = Watchlist.query.filter_by(user_id=current_user.id)\
        .order_by(Watchlist.added_date.desc()).limit(10).all()
    
    return render_template('dashboard.html',
                         recent_expenses=recent_expenses,
                         recent_expenses_json=recent_expenses_json,
                         total_expense=total_expense,
                         total_income=total_income,
                         balance=total_income - total_expense,
                         category_labels=category_labels,
                         category_data=category_data,
                         budget_progress=budget_progress,
                         alerts=alerts,
                         expense_trend_labels=expense_trend_labels,
                         expense_trend_data=expense_trend_data,
                         monthly_labels=monthly_labels,
                         monthly_income_data=monthly_income_data,
                         monthly_expense_data=monthly_expense_data,
                         predictions=predictions,
                         insights=insights,
                         ai_suggestions=ai_suggestions,
                         user_watchlist=user_watchlist)


@main.route('/budget/update', methods=['POST'])
@login_required
def update_category_budget():
    ensure_category_budget_table()

    category = (request.form.get('category') or '').strip()
    action = (request.form.get('action') or 'save').strip().lower()

    if category not in BUDGET_PERCENTAGES:
        flash('Invalid category selected.', 'error')
        return redirect(url_for('main.dashboard'))

    total_income = db.session.query(db.func.sum(Income.amount))\
        .filter_by(user_id=current_user.id).scalar() or 0
    default_budgets, custom_budgets, effective_budgets = get_effective_budgets(
        current_user.id,
        total_income
    )
    existing_budget = CategoryBudget.query.filter_by(user_id=current_user.id, category=category).first()

    if action == 'reset':
        if category != 'Other':
            current_amount = effective_budgets[category]
            reset_amount = default_budgets[category]
            other_amount = effective_budgets['Other']
            adjusted_other_amount = round(other_amount - (reset_amount - current_amount), 2)

            if adjusted_other_amount < 0:
                flash('Other budget cannot go below 0. Reduce this category amount first.', 'error')
                return redirect(url_for('main.dashboard'))

            upsert_category_budget(current_user.id, 'Other', adjusted_other_amount)

        if existing_budget:
            db.session.delete(existing_budget)
            db.session.commit()
            flash(f'{category} budget reset to auto value.', 'success')
        else:
            flash(f'{category} budget is already using auto value.', 'info')
        return redirect(url_for('main.dashboard'))

    amount_text = (request.form.get('amount') or '').strip()
    try:
        amount = float(amount_text)
    except ValueError:
        flash('Please enter a valid budget amount.', 'error')
        return redirect(url_for('main.dashboard'))

    if amount <= 0:
        flash('Budget amount must be greater than 0.', 'error')
        return redirect(url_for('main.dashboard'))

    amount = round(amount, 2)

    if category != 'Other':
        current_amount = effective_budgets[category]
        other_amount = effective_budgets['Other']
        adjusted_other_amount = round(other_amount - (amount - current_amount), 2)

        if adjusted_other_amount < 0:
            flash('Other budget cannot go below 0. Enter a smaller amount for this category.', 'error')
            return redirect(url_for('main.dashboard'))

        upsert_category_budget(current_user.id, 'Other', adjusted_other_amount)

    if existing_budget:
        existing_budget.amount = amount
    else:
        db.session.add(CategoryBudget(user_id=current_user.id, category=category, amount=amount))

    db.session.commit()

    if category == 'Other':
        flash(f'{category} budget updated to Rs {amount:.0f}.', 'success')
    else:
        flash(
            f'{category} budget updated to Rs {amount:.0f}. Other adjusted to Rs {effective_budgets["Other"] - (amount - effective_budgets[category]):.0f}.',
            'success'
        )
    return redirect(url_for('main.dashboard'))

@main.route('/add_expense', methods=['GET', 'POST'])
@login_required
def add_expense():
    if request.method == 'POST':
        expense = Expense(
            amount=float(request.form.get('amount')),
            category=request.form.get('category'),
            description=request.form.get('description'),
            user_id=current_user.id
        )
        db.session.add(expense)
        db.session.commit()
        
        flash('Expense added successfully!')
        
        return redirect(url_for('main.dashboard'))
    
    return render_template('add_expense.html')

@main.route('/add_income', methods=['GET', 'POST'])
@login_required
def add_income():
    if request.method == 'POST':
        income = Income(
            amount=float(request.form.get('amount')),
            source=request.form.get('source'),
            description=request.form.get('description', ''),
            user_id=current_user.id
        )
        db.session.add(income)
        db.session.commit()
        flash('Income added successfully!', 'success')
        return redirect(url_for('main.dashboard'))
    
    return render_template('add_income.html')

# ============= DELETE ROUTES =============
@main.route('/delete_expense/<int:expense_id>', methods=['POST'])
@login_required
def delete_expense(expense_id):
    """Delete an expense entry"""
    expense = Expense.query.filter_by(id=expense_id, user_id=current_user.id).first()
    if not expense:
        flash('Expense not found!', 'error')
    else:
        db.session.delete(expense)
        db.session.commit()
        flash(f'Expense of ₹{expense.amount} deleted successfully!', 'success')
    return redirect(url_for('main.dashboard'))

@main.route('/delete_income/<int:income_id>', methods=['POST'])
@login_required
def delete_income(income_id):
    """Delete an income entry"""
    income = Income.query.filter_by(id=income_id, user_id=current_user.id).first()
    if not income:
        flash('Income not found!', 'error')
    else:
        db.session.delete(income)
        db.session.commit()
        flash(f'Income of ₹{income.amount} deleted successfully!', 'success')
    return redirect(url_for('main.dashboard'))

# ============= EDIT ROUTES =============
@main.route('/edit_expense/<int:expense_id>', methods=['GET', 'POST'])
@login_required
def edit_expense(expense_id):
    """Edit existing expense"""
    expense = Expense.query.filter_by(id=expense_id, user_id=current_user.id).first()
    if not expense:
        flash('Expense not found!', 'error')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        expense.amount = float(request.form.get('amount'))
        expense.category = request.form.get('category')
        expense.description = request.form.get('description')
        db.session.commit()
        flash('Expense updated successfully!', 'success')
        return redirect(url_for('main.dashboard'))
    
    return render_template('edit_expense.html', expense=expense)

@main.route('/edit_income/<int:income_id>', methods=['GET', 'POST'])
@login_required
def edit_income(income_id):
    """Edit existing income"""
    income = Income.query.filter_by(id=income_id, user_id=current_user.id).first()
    if not income:
        flash('Income not found!', 'error')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        income.amount = float(request.form.get('amount'))
        income.source = request.form.get('source')
        income.description = request.form.get('description', '')
        db.session.commit()
        flash('Income updated successfully!', 'success')
        return redirect(url_for('main.dashboard'))
    
    return render_template('edit_income.html', income=income)

@main.route('/api/expense_data')
@login_required
def expense_data():
    # For AJAX calls to update charts
    last_7_days = datetime.now() - timedelta(days=7)
    daily_expenses = db.session.query(
        db.func.date(Expense.date), 
        db.func.sum(Expense.amount)
    ).filter(
        Expense.user_id == current_user.id,
        Expense.date >= last_7_days
    ).group_by(db.func.date(Expense.date)).all()
    
    return jsonify({
        'dates': [str(d[0]) for d in daily_expenses],
        'amounts': [float(d[1]) for d in daily_expenses]
    })

@main.route('/market')
@login_required
def market_watch():
    """Real-time market data and investment opportunities"""
    market_data = get_market_data()
    # Primary live signal is crypto feed (CoinGecko). Gold may still be cached if metal API key is invalid.
    market_live = market_data.get('crypto', {}).get('status') == 'success'
    
    # Get user's balance and spending
    total_income = db.session.query(db.func.sum(Income.amount))\
        .filter_by(user_id=current_user.id).scalar() or 0
    total_expense = db.session.query(db.func.sum(Expense.amount))\
        .filter_by(user_id=current_user.id).scalar() or 0
    user_balance = total_income - total_expense
    
    # Get investment recommendations
    spending_data = db.session.query(
        Expense.category,
        db.func.sum(Expense.amount).label('total')
    ).filter_by(user_id=current_user.id).group_by(Expense.category).all()
    
    spending_dict = {'monthly_expenses': [c[1] for c in spending_data]}
    recommendations = get_investment_advice(user_balance, spending_dict)
    
    # Get investment coaching
    investment_coach = optimizer.get_investment_coach(
        current_user.id,
        user_balance,
        total_income,
        total_expense
    )
    
    return render_template('market_watch.html',
                         market_data=market_data,
                         market_live=market_live,
                         recommendations=recommendations,
                         investment_coach=investment_coach,
                         user_balance=user_balance)

@main.route('/api/market_data')
@login_required
def api_market_data():
    """API endpoint for real-time market updates"""
    try:
        market_data = get_market_data()
        return jsonify({
            'status': 'success',
            'data': market_data
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@main.route('/investment-coach')
@login_required
def investment_coach():
    """AI-powered investment coaching page"""
    total_income = db.session.query(db.func.sum(Income.amount))\
        .filter_by(user_id=current_user.id).scalar() or 0
    total_expense = db.session.query(db.func.sum(Expense.amount))\
        .filter_by(user_id=current_user.id).scalar() or 0
    user_balance = total_income - total_expense
    
    # Get investment coaching
    coaching = optimizer.get_investment_coach(
        current_user.id,
        user_balance,
        total_income,
        total_expense
    )
    
    # Get market data for context
    market_data = get_market_data()
    
    return render_template('investment_coach.html',
                         coaching=coaching,
                         market_data=market_data,
                         user_balance=user_balance,
                         monthly_income=total_income,
                         monthly_expense=total_expense)


@main.route('/stock-search')
@login_required
def stock_search():
    """Stock search page"""
    query = request.args.get('q', '').strip()
    sector_filter = request.args.get('sector', '')
    
    results = []
    sectors = get_all_sectors()
    
    if query:
        results = search_stocks(query)
    elif sector_filter:
        # Reuse unified stock search so sector data uses same live/fallback logic
        results = [
            s for s in search_stocks(sector_filter, limit=25)
            if s['sector'].lower() == sector_filter.lower()
        ]
    
    # Get user's watchlist
    user_watchlist = Watchlist.query.filter_by(user_id=current_user.id).all()
    watchlist_symbols = [w.symbol for w in user_watchlist]
    
    return render_template('stock_search.html',
                         results=results,
                         sectors=sectors,
                         query=query,
                         sector_filter=sector_filter,
                         watchlist_symbols=watchlist_symbols)


@main.route('/api/stock-search')
@login_required
def api_stock_search():
    """API endpoint for stock search with JSON response"""
    query = request.args.get('q', '').strip()
    if not query or len(query) < 1:
        return jsonify([])
    
    results = search_stocks(query, limit=15)
    return jsonify(results)


@main.route('/watchlist/add/<symbol>', methods=['POST'])
@login_required
def add_to_watchlist(symbol):
    """Add stock to user's watchlist"""
    symbol = symbol.upper()
    stock = get_stock_price(symbol)
    
    if not stock:
        flash('Stock not found!', 'danger')
        return redirect(request.referrer or url_for('main.stock_search'))
    
    # Check if already in watchlist
    existing = Watchlist.query.filter_by(
        user_id=current_user.id,
        symbol=symbol
    ).first()
    
    if existing:
        flash(f'{symbol} is already in your watchlist!', 'info')
    else:
        watchlist_item = Watchlist(
            user_id=current_user.id,
            symbol=symbol,
            name=stock['name'],
            sector=stock['sector']
        )
        db.session.add(watchlist_item)
        db.session.commit()
        flash(f'{symbol} added to your watchlist!', 'success')
    
    return redirect(request.referrer or url_for('main.stock_search'))


@main.route('/watchlist/remove/<symbol>', methods=['POST'])
@login_required
def remove_from_watchlist(symbol):
    """Remove stock from user's watchlist"""
    watchlist_item = Watchlist.query.filter_by(
        user_id=current_user.id,
        symbol=symbol.upper()
    ).first()
    
    if watchlist_item:
        db.session.delete(watchlist_item)
        db.session.commit()
        flash(f'{symbol} removed from your watchlist!', 'success')
    else:
        flash('Stock not found in watchlist!', 'danger')
    
    return redirect(request.referrer or url_for('main.watchlist'))


@main.route('/watchlist')
@login_required
def watchlist():
    """View user's stock watchlist with current prices"""
    user_watchlist = Watchlist.query.filter_by(user_id=current_user.id)\
        .order_by(Watchlist.added_date.desc()).all()
    
    # Get current prices for all watched stocks
    watchlist_data = []
    for item in user_watchlist:
        stock = get_stock_price(item.symbol)
        if stock:
            watchlist_data.append(stock)
    
    return render_template('watchlist.html', watchlist=watchlist_data)


@main.route('/api/watchlist')
@login_required
def api_watchlist():
    """API endpoint for watchlist data"""
    user_watchlist = Watchlist.query.filter_by(user_id=current_user.id).all()
    
    watchlist_data = []
    for item in user_watchlist:
        stock = get_stock_price(item.symbol)
        if stock:
            watchlist_data.append(stock)
    
    return jsonify(watchlist_data)


@main.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    """AI Fin-Buddy Chat API Endpoint - Uses Gemini API"""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({'status': 'error', 'message': 'Empty message'}), 400
        
        # Prepare user context
        total_income = db.session.query(db.func.sum(Income.amount))\
            .filter_by(user_id=current_user.id).scalar() or 0
        total_expense = db.session.query(db.func.sum(Expense.amount))\
            .filter_by(user_id=current_user.id).scalar() or 0
        user_balance = total_income - total_expense
        
        # Get spending by category
        spending_data = db.session.query(
            Expense.category,
            db.func.sum(Expense.amount).label('total')
        ).filter_by(user_id=current_user.id).group_by(Expense.category).all()
        
        expenses = {c[0]: c[1] for c in spending_data}
        
        # Get market data
        market_data = get_market_data()
        
        # Prepare context for chatbot
        user_context = {
            'username': current_user.username,
            'balance': user_balance,
            'market_data': {
                'gold_price': market_data['gold']['gold_price_24k'],
                'bitcoin_price': market_data['crypto']['bitcoin']['price'],
                'ethereum_price': market_data['crypto']['ethereum']['price'],
                'nifty_50': market_data['indices']['nifty_50']['price'],
                'sp500': market_data['indices']['sp500']['price'],
            },
            'expenses': expenses,
        }
        
        # Get chatbot (Gemini with local fallback)
        chatbot = get_chatbot()
        ai_response = chatbot.chat(user_message, user_context)
        
        return jsonify({
            'status': 'success',
            'message': ai_response,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Chat API error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Oops! Kuch error aaya. Dobara try karein! 🤖'
        }), 500

@main.route('/api/investment-advice', methods=['GET'])
@login_required
def api_investment_advice():
    """Get investment advice from OpenRouter API"""
    try:
        # Prepare user context
        total_income = db.session.query(db.func.sum(Income.amount))\
            .filter_by(user_id=current_user.id).scalar() or 0
        total_expense = db.session.query(db.func.sum(Expense.amount))\
            .filter_by(user_id=current_user.id).scalar() or 0
        user_balance = total_income - total_expense
        
        # Get spending by category
        spending_data = db.session.query(
            Expense.category,
            db.func.sum(Expense.amount).label('total')
        ).filter_by(user_id=current_user.id).group_by(Expense.category).all()
        
        expenses = {c[0]: c[1] for c in spending_data}
        
        # Get market data
        market_data = get_market_data()
        
        # Prepare context
        user_context = {
            'username': current_user.username,
            'balance': user_balance,
            'market_data': {
                'gold_price': market_data['gold']['gold_price_24k'],
                'bitcoin_price': market_data['crypto']['bitcoin']['price'],
                'ethereum_price': market_data['crypto']['ethereum']['price'],
                'nifty_50': market_data['indices']['nifty_50']['price'],
                'sp500': market_data['indices']['sp500']['price'],
            },
            'expenses': expenses,
        }
        
        # Get OpenRouter advisor
        advisor = get_openrouter_advisor()
        
        if advisor:
            advice = advisor.get_investment_advice(user_context)
        else:
            # Fallback if no OpenRouter key
            from app.local_chatbot import LocalAIChatbot
            local_bot = LocalAIChatbot()
            advice = local_bot.chat("Mujhe investment advice de", user_context)
        
        return jsonify({
            'status': 'success',
            'advice': advice,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Investment advice error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Investment advice fetch failed. Try again!'
        }), 500

@main.route('/calculators')
@login_required
def calculators():
    """Financial Calculators Page"""
    return render_template('calculators.html')

@main.route('/achievements')
@login_required
def achievements():
    """User Achievements and Gamification Page"""
    # Calculate user stats
    total_income = db.session.query(db.func.sum(Income.amount))\
        .filter_by(user_id=current_user.id).scalar() or 0
    total_expense = db.session.query(db.func.sum(Expense.amount))\
        .filter_by(user_id=current_user.id).scalar() or 0
    user_balance = total_income - total_expense
    
    # Count transactions
    income_count = Income.query.filter_by(user_id=current_user.id).count()
    expense_count = Expense.query.filter_by(user_id=current_user.id).count()
    watchlist_count = Watchlist.query.filter_by(user_id=current_user.id).count()
    
    # Calculate savings rate
    savings_rate = 0
    if total_income > 0:
        savings_rate = ((total_income - total_expense) / total_income) * 100
    
    # Calculate streak (simplified - days with transactions)
    from datetime import datetime, timedelta
    today = datetime.now().date()
    streak = 0
    current_date = today
    
    # Check for continuous days with transactions
    for i in range(30):  # Check last 30 days
        has_transaction = (
            Expense.query.filter(
                Expense.user_id == current_user.id,
                db.func.date(Expense.date) == current_date
            ).first() is not None or
            Income.query.filter(
                Income.user_id == current_user.id,
                db.func.date(Income.date) == current_date
            ).first() is not None
        )
        
        if has_transaction:
            streak += 1
            current_date = current_date - timedelta(days=1)
        else:
            break
    
    # Calculate level based on total transactions
    total_transactions = income_count + expense_count
    level = 1 + (total_transactions // 10)  # Level up every 10 transactions
    next_level_transactions = (level * 10)
    level_progress = ((total_transactions % 10) / 10) * 100
    
    # Define achievements
    achievements_list = [
        {
            'id': 'first_income',
            'name': 'First Steps',
            'description': 'Log your first income',
            'icon': 'bi-currency-rupee',
            'color': 'from-green-500 to-emerald-600',
            'unlocked': income_count >= 1,
            'progress': min(100, (income_count / 1) * 100)
        },
        {
            'id': 'first_expense',
            'name': 'Spender',
            'description': 'Track your first expense',
            'icon': 'bi-cash-coin',
            'color': 'from-red-500 to-pink-600',
            'unlocked': expense_count >= 1,
            'progress': min(100, (expense_count / 1) * 100)
        },
        {
            'id': 'ten_transactions',
            'name': 'Getting Started',
            'description': 'Complete 10 transactions',
            'icon': 'bi-graph-up',
            'color': 'from-blue-500 to-indigo-600',
            'unlocked': total_transactions >= 10,
            'progress': min(100, (total_transactions / 10) * 100)
        },
        {
            'id': 'fifty_transactions',
            'name': 'Dedicated Tracker',
            'description': 'Complete 50 transactions',
            'icon': 'bi-trophy',
            'color': 'from-purple-500 to-pink-600',
            'unlocked': total_transactions >= 50,
            'progress': min(100, (total_transactions / 50) * 100)
        },
        {
            'id': 'positive_balance',
            'name': 'Profit Maker',
            'description': 'Maintain positive balance',
            'icon': 'bi-piggy-bank',
            'color': 'from-green-500 to-teal-600',
            'unlocked': user_balance > 0,
            'progress': 100 if user_balance > 0 else 0
        },
        {
            'id': 'high_saver',
            'name': 'High Saver',
            'description': 'Achieve 50%+ savings rate',
            'icon': 'bi-gem',
            'color': 'from-amber-500 to-orange-600',
            'unlocked': savings_rate >= 50,
            'progress': min(100, (savings_rate / 50) * 100)
        },
        {
            'id': 'market_watcher',
            'name': 'Market Watcher',
            'description': 'Add 5 stocks to watchlist',
            'icon': 'bi-star-fill',
            'color': 'from-yellow-500 to-amber-600',
            'unlocked': watchlist_count >= 5,
            'progress': min(100, (watchlist_count / 5) * 100)
        },
        {
            'id': 'seven_day_streak',
            'name': 'Consistent Tracker',
            'description': 'Maintain 7-day logging streak',
            'icon': 'bi-fire',
            'color': 'from-orange-500 to-red-600',
            'unlocked': streak >= 7,
            'progress': min(100, (streak / 7) * 100)
        }
    ]
    
    # Count unlocked achievements
    unlocked_count = sum(1 for a in achievements_list if a['unlocked'])
    
    return render_template('achievements.html',
                         level=level,
                         level_progress=level_progress,
                         next_level_transactions=next_level_transactions,
                         total_transactions=total_transactions,
                         streak=streak,
                         achievements=achievements_list,
                         unlocked_count=unlocked_count,
                         user_balance=user_balance,
                         savings_rate=savings_rate)
