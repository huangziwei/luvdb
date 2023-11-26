document.addEventListener("DOMContentLoaded", function () {
    // Event delegation for toggle buttons
    document.body.addEventListener("click", function (event) {
        if (event.target.classList.contains("toggle-button")) {
            toggleSections(event.target);
        }
    });

    // Initial setup based on URL parameters
    setupInitialView();

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

    // Focus on text input if required
    focusTextInput();
});

function focusTextInput() {
    const urlParams = new URLSearchParams(window.location.search);
    var intervalId = setInterval(function () {
        if (urlParams.has("reply") && urlParams.get("reply") === "true") {
            var replyInput = document.querySelector("#comments-section #text-input");
            if (replyInput && replyInput.offsetParent !== null) {
                replyInput.focus();
                clearInterval(intervalId);
            }
        } else if (urlParams.has("repost") && urlParams.get("repost") === "true") {
            var repostInput = document.querySelector("#reposts-section #text-input");
            if (repostInput && repostInput.offsetParent !== null) {
                repostInput.focus();
                clearInterval(intervalId);
            }
        }
    }, 100);
}
