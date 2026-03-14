    // Chatbot Knowledge Base
    const chatbotResponses = {
        'main features': {
            keywords: ['features', 'what can', 'what do', 'what does this', 'capabilities'],
            response: `
                📊 **ExpenseTracker AI** has amazing features:

                💰 **Expense Tracking** - Log all expenses instantly
                💵 **Income Management** - Track all income sources (Salary, Freelance, Business, etc.)
                📊 **Smart Analytics** - AI-powered spending analysis & predictions
                🤖 **AI Coach** - Get personalized financial advice
                📈 **Market Watch** - Real-time market data & stock tracking
                📱 **Dashboard** - Beautiful real-time financial overview
                🎁 **Achievements** - Gamified savings goals
                📊 **Calculators** - Investment & financial planning calculators
                
                All powered by advanced ML models (LSTM, ARIMA, Ensemble)!
            `
        },
        'add income': {
            keywords: ['add income', 'how to add', 'income', 'earn', 'salary', 'freelance'],
            response: `
                💰 **How to Add Income:**

                1️⃣ Click the "Add Income" button (You're already here!)
                2️⃣ Enter the **Amount** in rupees (₹)
                3️⃣ Select **Income Source**:
                   • 💼 Salary/Job
                   • 💻 Freelance/Consulting
                   • 🏢 Business Income
                   • 📈 Investment Returns
                   • 🎁 Bonus/Commission
                   • 🎉 Gift/Inheritance
                   • 📦 Other Sources

                4️⃣ (Optional) Add description for details
                5️⃣ Click "Add Income" button ✅

                Your income will be tracked and used for accurate financial insights!
            `
        },
        'edit delete': {
            keywords: ['delete', 'edit', 'mistake', 'change', 'update', 'fix', 'wrong', 'incorrect', 'undo'],
            response: `
                ✏️ **Edit & Delete Features:**

                **Made a mistake?** No problem! You can:

                🔄 **Edit** - Change amount, source, or details:
                   • Go to Dashboard
                   • Click "Edit" button on the transaction
                   • Update the information
                   • Click "Save Changes" ✅

                🗑️ **Delete** - Remove a transaction completely:
                   • Go to Dashboard
                   • Click "Delete" button on the transaction
                   • Confirmed! Entry removed instantly 🎉

                **Available for:**
                   • ✅ All Expenses
                   • ✅ All Income entries
                   • ✅ Quick one-click operations

                No penalties - Fix errors anytime!
            `
        },
        'ai coach': {
            keywords: ['ai coach', 'coach', 'advice', 'recommendation', 'financial'],
            response: `
                🤖 **AI Coach Feature:**

                The AI Coach provides:

                📊 **Smart Recommendations**
                   • Personalized expense reduction tips
                   • Spending pattern analysis
                   • Budget optimization strategies

                💡 **Financial Planning**
                   • Portfolio allocation suggestions
                   • Investment recommendations
                   • Risk assessment analysis

                🎯 **Goal Setting**
                   • Retirement planning calculations
                   • Savings targets
                   • Wealth building strategies

                📈 **Market Insights**
                   • Stock recommendations
                   • Market trend analysis
                   • Real-time price tracking

                Powered by LSTM Neural Networks for 70-85% accuracy!
            `
        },
        'investment': {
            keywords: ['investment', 'stock', 'portfolio', 'market', 'trading'],
            response: `
                📈 **Investment Tracking:**

                🔹 **Market Watch** - Real-time stock tracking
                   • 500+ Indian stocks
                   • Live price updates
                   • Watchlist creation
                   • Price alerts

                💼 **Portfolio Management**
                   • Modern Portfolio Theory (MPT)
                   • 9 asset classes (Stocks, Bonds, Gold, Real Estate, Crypto)
                   • Risk profiling
                   • Asset rebalancing

                📊 **Advanced Analysis**
                   • GARCH volatility modeling
                   • Value at Risk (VaR) calculations
                   • Stress testing
                   • Sensitivity analysis

                🎯 **Recommended Assets**
                   • Large Cap / Mid Cap / Small Cap stocks
                   • Government & Corporate bonds
                   • Gold & Real Estate
                   • Cryptocurrency

                Click "Market Watch" to start!
            `
        },
        'dashboard': {
            keywords: ['dashboard', 'overview', 'summary', 'expense', 'spending'],
            response: `
                📊 **Dashboard Features:**

                Your financial snapshot with:

                💰 **Balance Overview**
                   • Total income
                   • Total expenses
                   • Net savings
                   • Savings percentage

                📈 **Smart Charts**
                   • Expense breakdown by category
                   • Monthly spending trends
                   • Income sources visualization
                   • Financial health score

                🎯 **Quick Actions**
                   • Add new expense (fast)
                   • Add income (quick)
                   • View spend reports
                   • Check achievements

                🤖 **AI Insights**
                   • Next month spending prediction
                   • Financial health score (0-100)
                   • Risk assessment
                   • Personalized recommendations

                Everything updates in real-time!
            `
        },
        'calculator': {
            keywords: ['calculator', 'calculate', 'sip', 'retirement', 'future value', 'compound'],
            response: `
                📊 **Financial Calculators:**

                💰 **SIP Calculator**
                   • Calculate returns on Systematic Investment Plans
                   • Multiple scenarios (₹1000 to ₹1,00,000+)
                   • Historic data based returns
                   • 20+ year projections

                🏠 **Retirement Calculator**
                   • Plan your retirement corpus
                   • Inflation adjustments
                   • Life expectancy calculations
                   • Investment recommendations

                📈 **Compound Interest**
                   • See money grow over time
                   • Different investment durations
                   • Rate comparisons
                   • Goal tracking

                💡 **Tax Calculator**
                   • Income tax estimation
                   • Deduction planning
                   • Savings optimization

                Click "Calculators" to try them!
            `
        },
        'help': {
            keywords: ['help', 'support', 'how', 'stuck', 'problem'],
            response: `
                🆘 **Need Help?**

                Here's what you can ask me:
                
                ✨ Ask about **features** - What can the app do?
                💰 Ask about **adding income** - How to track earnings
                ✏️ Ask about **edit & delete** - Fix your mistakes
                🤖 Ask about **AI Coach** - Get smart recommendations
                📈 Ask about **investments** - Portfolio & market tracking
                📊 Ask about **dashboard** - Understand your finances
                🧮 Ask about **calculators** - Plan your future
                🎯 Ask about **achievements** - Gamified goals

                Or type your question naturally! I'll try to help! 😊
            `
        }
    };

    // Initialize Chatbot
    const chatbotToggle = document.getElementById('chatbot-toggle');
    const chatbotClose = document.getElementById('chatbot-close');
    const chatbotContainer = document.getElementById('chatbot-container');
    const chatbotMessages = document.getElementById('chatbot-messages');
    const suggestionsDiv = document.getElementById('suggestions');
    const chatbotInput = document.getElementById('chatbot-input');
    const chatbotSend = document.getElementById('chatbot-send');

    chatbotToggle.addEventListener('click', () => {
        chatbotContainer.classList.toggle('active');
        if (chatbotContainer.classList.contains('active')) {
            chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
        }
    });

    chatbotClose.addEventListener('click', () => {
        chatbotContainer.classList.remove('active');
    });

    chatbotSend.addEventListener('click', () => {
        sendMessage(chatbotInput.value);
    });

    chatbotInput.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
            event.preventDefault();
            sendMessage(chatbotInput.value);
        }
    });

    function escapeHtml(text) {
        return text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function formatBotMessage(text) {
        return escapeHtml(text).replace(/\n/g, '<br>');
    }

    async function sendMessage(userMessage) {
        const cleanMessage = (userMessage || '').trim();
        if (!cleanMessage) {
            return;
        }

        // Add user message
        const userDiv = document.createElement('div');
        userDiv.className = 'message user';
        userDiv.innerHTML = `<div class="message-content">${escapeHtml(cleanMessage)}</div>`;
        chatbotMessages.appendChild(userDiv);
        chatbotInput.value = '';
        
        // Hide suggestions
        suggestionsDiv.style.display = 'none';
        
        // Scroll to bottom
        chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
        
        // Temporary typing indicator
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'message bot';
        loadingDiv.innerHTML = `<div class="message-content">Typing...</div>`;
        chatbotMessages.appendChild(loadingDiv);
        chatbotMessages.scrollTop = chatbotMessages.scrollHeight;

        let responseText = '';

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': (document.querySelector("input[name='csrf_token']") || {}).value || ''
                },
                body: JSON.stringify({ message: cleanMessage })
            });

            const result = await response.json();
            if (response.ok && result.status === 'success' && result.message) {
                responseText = result.message;
            } else {
                responseText = getBotResponse(cleanMessage);
            }
        } catch (error) {
            responseText = getBotResponse(cleanMessage);
        }

        loadingDiv.remove();

        const botDiv = document.createElement('div');
        botDiv.className = 'message bot';
        botDiv.innerHTML = `<div class="message-content">${formatBotMessage(responseText)}</div>`;
        chatbotMessages.appendChild(botDiv);
        chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
    }

    function getBotResponse(userMessage) {
        const message = userMessage.toLowerCase();
        
        // Check each response category
        for (const [key, data] of Object.entries(chatbotResponses)) {
            for (const keyword of data.keywords) {
                if (message.includes(keyword)) {
                    return data.response;
                }
            }
        }
        
        // Default response
        return `
            😊 I understand you're asking about: "${userMessage}"
            
            Here are some topics I can help with:
            • 🎯 What are the main features?
            • 💰 How do I add income?
            • 🤖 Tell me about AI Coach
            • 📈 How do I track investments?
            • 📊 Explain the dashboard
            • 🧮 About financial calculators
            
            Feel free to ask! 💡
        `;
    }
