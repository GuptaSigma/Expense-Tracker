document.addEventListener('DOMContentLoaded', function () {
    let seconds = 300; // 5 minutes
    const countdownEl = document.getElementById('countdown');
    if (!countdownEl) return;

    setInterval(() => {
        seconds--;
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        countdownEl.textContent = `${mins}:${secs.toString().padStart(2, '0')}`;

        if (seconds <= 0) {
            location.reload();
        }
    }, 1000);
});
