// Smooth transition for elements on scroll
document.addEventListener("DOMContentLoaded", function() {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('opacity-100', 'translate-y-0');
                entry.target.classList.remove('opacity-0', 'translate-y-10');
            }
        });
    });

    document.querySelectorAll('.p-8').forEach((el) => {
        el.classList.add('opacity-0', 'translate-y-10', 'transition', 'duration-700');
        observer.observe(el);
    });
});
