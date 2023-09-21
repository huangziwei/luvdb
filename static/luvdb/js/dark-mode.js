document.addEventListener('DOMContentLoaded', function() {
    const toggleButton = document.getElementById('darkModeToggle');
    const htmlElement = document.documentElement;
    const bgLightElements = document.querySelectorAll('.bg-light');
    const bgWhiteElements = document.querySelectorAll('.bg-white');
    const btnLightElements = document.querySelectorAll('.btn-light');
    const bioElements = document.querySelectorAll('.bio');
    const stickyNoteElements = document.querySelectorAll('.sticky-note');
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
            bgWhiteElements.forEach(el => el.classList.replace('bg-white', 'bg-dark'));
            btnLightElements.forEach(el => el.classList.replace('btn-light', 'btn-dark-highlight'));
            bioElements.forEach(el => el.style.backgroundColor = '#333'); // Dark mode compatible color for bio
            faIcons.forEach(el => el.setAttribute('fill', '#ccc')); // Dark mode color for FontAwesome icons
            stickyNoteElements.forEach(el => el.classList.add('bg-dark'));
        } else {
            htmlElement.removeAttribute('data-bs-theme');
            bgLightElements.forEach(el => el.classList.remove('bg-dark-highlight'));
            bgWhiteElements.forEach(el => el.classList.replace('bg-dark', "bg-white"));
            btnLightElements.forEach(el => el.classList.replace('btn-dark-highlight', 'btn-light'));
            bioElements.forEach(el => el.style.backgroundColor = '#fff6ed'); // Original color for bio
            faIcons.forEach(el => el.setAttribute('fill', '#6C757D')); // Original color for FontAwesome icons
            stickyNoteElements.forEach(el => el.classList.remove('bg-dark'));

        }
    }
});
