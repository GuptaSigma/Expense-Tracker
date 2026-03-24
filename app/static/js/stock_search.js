function searchStocks() {
    const searchInput = document.getElementById('stockSearch');
    if (!searchInput) return;

    const query = searchInput.value || '';
    const searchUrl = searchInput.dataset.searchUrl || '/stock-search';
    if (query.trim()) {
        window.location.href = `${searchUrl}?q=${encodeURIComponent(query)}`;
    }
}

document.addEventListener('DOMContentLoaded', function () {
    const searchInput = document.getElementById('stockSearch');
    if (!searchInput) return;

    searchInput.addEventListener('keypress', function (e) {
        if (e.key === 'Enter') {
            searchStocks();
        }
    });

    searchInput.focus();
});
