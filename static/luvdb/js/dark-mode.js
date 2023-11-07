document.addEventListener("DOMContentLoaded", function () {
    const toggleButton = document.getElementById("darkModeToggle");
    toggleButton.style.display = "inline-block";

    const htmlElement = document.documentElement;
    const bgLightElements = document.querySelectorAll(".bg-light");
    const bgWhiteElements = document.querySelectorAll(".bg-white");
    const bioElements = document.querySelectorAll(".bio");
    const stickyNoteElements = document.querySelectorAll(".sticky-note");
    const faIcons = document.querySelectorAll(".fa-icon path");
    const metaThemeColor = document.querySelector("meta[name=theme-color]");

    // Load saved theme from localStorage
    const savedTheme = localStorage.getItem("theme") || getSystemPreferredTheme();
    applyTheme(savedTheme);

    toggleButton.addEventListener("click", function () {
        const currentTheme = htmlElement.getAttribute("data-bs-theme") === "dark" ? "dark" : "light";
        const newTheme = currentTheme === "light" ? "dark" : "light";
        applyTheme(newTheme);
        localStorage.setItem("theme", newTheme);
    });

    function applyTheme(theme) {
        if (theme === "dark") {
            htmlElement.setAttribute("data-bs-theme", "dark");
            metaThemeColor.setAttribute("content", "#2B3035");

            bgLightElements.forEach((el) => el.classList.add("bg-dark-highlight"));
            // bgWhiteElements.forEach(el => el.classList.replace('bg-white', 'bg-dark'));
            bioElements.forEach((el) => (el.style.backgroundColor = "#2B3035")); // Dark mode compatible color for bio
            faIcons.forEach((el) => el.setAttribute("fill", "#ccc")); // Dark mode color for FontAwesome icons
            stickyNoteElements.forEach((el) => el.classList.add("bg-dark"));
        } else {
            htmlElement.removeAttribute("data-bs-theme");
            bgLightElements.forEach((el) => el.classList.remove("bg-dark-highlight"));
            metaThemeColor.setAttribute("content", "#F6F7F9");
            // bgWhiteElements.forEach(el => el.classList.replace('bg-dark', "bg-white"));
            bioElements.forEach((el) => (el.style.backgroundColor = "#e5ebef")); // Original color for bio
            faIcons.forEach((el) => el.setAttribute("fill", "#6C757D")); // Original color for FontAwesome icons
            stickyNoteElements.forEach((el) => el.classList.remove("bg-dark"));
        }
    }

    function getSystemPreferredTheme() {
        if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
            return "dark";
        }
        return "light";
    }
});
