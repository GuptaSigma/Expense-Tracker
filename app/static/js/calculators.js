// SIP Calculator
function calculateSIP() {
    const monthly = parseFloat(document.getElementById('sip-amount').value);
    const rate = parseFloat(document.getElementById('sip-rate').value);
    const years = parseFloat(document.getElementById('sip-years').value);

    const months = years * 12;
    const monthlyRate = rate / 12 / 100;

    const maturityAmount = monthly * ((Math.pow(1 + monthlyRate, months) - 1) / monthlyRate) * (1 + monthlyRate);
    const invested = monthly * months;
    const returns = maturityAmount - invested;

    document.getElementById('sip-result').classList.remove('hidden');
    document.getElementById('sip-total').textContent = '₹' + maturityAmount.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    document.getElementById('sip-invested').textContent = '₹' + invested.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    document.getElementById('sip-returns').textContent = '₹' + returns.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',');

    showToast('SIP calculation completed successfully!', 'success');
}

// EMI Calculator
function calculateEMI() {
    const principal = parseFloat(document.getElementById('emi-principal').value);
    const rate = parseFloat(document.getElementById('emi-rate').value);
    const years = parseFloat(document.getElementById('emi-years').value);

    const monthlyRate = rate / 12 / 100;
    const months = years * 12;

    const emi = principal * monthlyRate * Math.pow(1 + monthlyRate, months) / (Math.pow(1 + monthlyRate, months) - 1);
    const totalPayment = emi * months;
    const totalInterest = totalPayment - principal;

    document.getElementById('emi-result').classList.remove('hidden');
    document.getElementById('emi-amount').textContent = '₹' + emi.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    document.getElementById('emi-total').textContent = '₹' + totalPayment.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    document.getElementById('emi-interest').textContent = '₹' + totalInterest.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',');

    showToast('EMI calculation completed successfully!', 'success');
}

// Compound Interest Calculator
function calculateCI() {
    const principal = parseFloat(document.getElementById('ci-principal').value);
    const rate = parseFloat(document.getElementById('ci-rate').value);
    const years = parseFloat(document.getElementById('ci-years').value);

    const amount = principal * Math.pow((1 + rate / 100), years);
    const interest = amount - principal;

    document.getElementById('ci-result').classList.remove('hidden');
    document.getElementById('ci-total').textContent = '₹' + amount.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    document.getElementById('ci-invested').textContent = '₹' + principal.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    document.getElementById('ci-interest').textContent = '₹' + interest.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',');

    showToast('Compound interest calculated successfully!', 'success');
}

// Tax Calculator (New Regime - FY 2025-26)
function calculateTax() {
    const income = parseFloat(document.getElementById('tax-income').value);
    let tax = 0;

    if (income <= 300000) {
        tax = 0;
    } else if (income <= 600000) {
        tax = (income - 300000) * 0.05;
    } else if (income <= 900000) {
        tax = 15000 + (income - 600000) * 0.10;
    } else if (income <= 1200000) {
        tax = 45000 + (income - 900000) * 0.15;
    } else if (income <= 1500000) {
        tax = 90000 + (income - 1200000) * 0.20;
    } else {
        tax = 150000 + (income - 1500000) * 0.30;
    }

    const netIncome = income - tax;
    const effectiveRate = (tax / income * 100).toFixed(2);

    document.getElementById('tax-result').classList.remove('hidden');
    document.getElementById('tax-amount').textContent = '₹' + tax.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    document.getElementById('tax-net').textContent = '₹' + netIncome.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    document.getElementById('tax-rate').textContent = effectiveRate + '%';

    showToast('Tax calculation completed successfully!', 'success');
}

// Retirement Calculator
function calculateRetirement() {
    const currentAge = parseFloat(document.getElementById('ret-age').value);
    const retireAge = parseFloat(document.getElementById('ret-retire-age').value);
    const monthlySavings = parseFloat(document.getElementById('ret-savings').value);
    const returnRate = parseFloat(document.getElementById('ret-return').value);

    const years = retireAge - currentAge;
    const months = years * 12;
    const monthlyRate = returnRate / 12 / 100;

    const corpus = monthlySavings * ((Math.pow(1 + monthlyRate, months) - 1) / monthlyRate) * (1 + monthlyRate);
    const invested = monthlySavings * months;
    const returns = corpus - invested;

    document.getElementById('ret-result').classList.remove('hidden');
    document.getElementById('ret-corpus').textContent = '₹' + corpus.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    document.getElementById('ret-invested').textContent = '₹' + invested.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    document.getElementById('ret-returns').textContent = '₹' + returns.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',');

    showToast('Retirement planning calculated successfully!', 'success');
}
