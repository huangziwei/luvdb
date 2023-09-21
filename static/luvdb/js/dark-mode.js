document.addEventListener('DOMContentLoaded', function() {
    const toggleButton = document.getElementById('darkModeToggle');
    const htmlElement = document.documentElement;
    const bgLightElements = document.querySelectorAll('.bg-light');
    const btnLightElements = document.querySelectorAll('.btn-light');
    const bioElements = document.querySelectorAll('.bio');
    const faIcons = document.querySelectorAll('.fa-icon path');

    // Load saved theme from localStorage
    const savedTheme = localStorage.getItem('theme');
    applyTheme(savedTheme);

    toggleButton.addEventListener('click', function() {
        const currentTheme = htmlElement.getAttribute('data-bs-theme') === 'dark' ? 'dark' : 'light';
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        applyTheme(newTheme);
        localStorage.setItem('theme', newTheme);
    });

    function applyTheme(theme) {
        if (theme === 'dark') {
            htmlElement.setAttribute('data-bs-theme', 'dark');
            bgLightElements.forEach(el => el.classList.add('bg-dark-highlight'));
            btnLightElements.forEach(el => el.classList.replace('btn-light', 'btn-dark'));
            bioElements.forEach(el => el.style.backgroundColor = '#333'); // Dark mode compatible color for bio
            faIcons.forEach(el => el.setAttribute('fill', '#ccc')); // Dark mode color for FontAwesome icons
        } else {
            htmlElement.removeAttribute('data-bs-theme');
            bgLightElements.forEach(el => el.classList.remove('bg-dark-highlight'));
            btnLightElements.forEach(el => el.classList.replace('btn-dark', 'btn-light'));
            bioElements.forEach(el => el.style.backgroundColor = '#fff6ed'); // Original color for bio
            faIcons.forEach(el => el.setAttribute('fill', '#000')); // Original color for FontAwesome icons
        }
    }
});
