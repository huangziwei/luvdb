document.addEventListener("DOMContentLoaded", function () {
    // Event delegation for toggle buttons
    document.body.addEventListener("click", function (event) {
        if (event.target.classList.contains("toggle-button")) {
            updateURLAndReload(event.target);
        }
    });

    // Initial setup based on URL parameters
    setupInitialView();

    // Function to update the URL and reload the page
    function updateURLAndReload(button) {
        const sectionType = button.id.replace("show-", "");
        const url = new URL(window.location.href);

        // Remove other section parameters
        if (sectionType === "comments") {
            url.searchParams.delete("repost");
            url.searchParams.set("reply", "true");
        } else if (sectionType === "reposts") {
            url.searchParams.delete("reply");
            url.searchParams.set("repost", "true");
        }

        window.location.href = url.toString();
    }

    // Function to setup initial view based on URL parameters
    function setupInitialView() {
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.has("repost") && urlParams.get("repost") === "true") {
            var repostButton = document.getElementById("show-reposts");
            if (repostButton) {
                toggleSections(repostButton);
            }
        } else if (urlParams.has("reply") && urlParams.get("reply") === "true") {
            var commentsButton = document.getElementById("show-comments");
            if (commentsButton) {
                toggleSections(commentsButton);
            }
        }
    }

    // Function to toggle sections
    function toggleSections(button) {
        var buttons = document.getElementsByClassName("toggle-button");
        for (var j = 0; j < buttons.length; j++) {
            var sectionId = buttons[j].id.replace("show-", "") + "-section";
            var section = document.getElementById(sectionId);
            if (section) {
                section.style.display = "none";
                buttons[j].classList.remove("btn-primary");
                buttons[j].classList.add("btn-secondary");
            }
        }

        var sectionId = button.id.replace("show-", "") + "-section";
        var section = document.getElementById(sectionId);
        if (section) {
            section.style.display = "block";
            button.classList.remove("btn-secondary");
            button.classList.add("btn-primary");
        }
    }

    // Focus on text input if required
    focusTextInput();
});

function focusTextInput() {
    const urlParams = new URLSearchParams(window.location.search);
    var intervalId = setInterval(function () {
        if (urlParams.get("focus") === "true") {
            var replyInput = document.querySelector("#comments-section #text-input");
            var repostInput = document.querySelector("#reposts-section #text-input");

            if (replyInput && replyInput.offsetParent !== null) {
                replyInput.focus();
                clearInterval(intervalId);
            } else if (repostInput && repostInput.offsetParent !== null) {
                repostInput.focus();
                clearInterval(intervalId);
            }
        }
    }, 100);
}
