document.addEventListener('DOMContentLoaded', function () {
    const unlockedAchievements = document.querySelectorAll('.achievement-card:not(.opacity-50)');
    unlockedAchievements.forEach((card, index) => {
        setTimeout(() => {
            card.style.animation = 'bounce 0.5s ease-out';
        }, index * 100);
    });
});
