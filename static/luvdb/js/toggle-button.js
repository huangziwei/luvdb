var buttons = document.getElementsByClassName("toggle-button");

for (var i = 0; i < buttons.length; i++) {
    buttons[i].addEventListener("click", function () {
        // Hide all sections and make all buttons secondary
        for (var j = 0; j < buttons.length; j++) {
            var sectionId = buttons[j].id.replace("show-", "") + "-section";
            document.getElementById(sectionId).style.display = "none";
            buttons[j].classList.remove("btn-primary");
            buttons[j].classList.add("btn-secondary");
        }

        // Show the clicked section and make the button primary
        var sectionId = this.id.replace("show-", "") + "-section";
        document.getElementById(sectionId).style.display = "block";
        this.classList.remove("btn-secondary");
        this.classList.add("btn-primary");
    });
}

function focusTextInput() {
    const urlParams = new URLSearchParams(window.location.search);

    var intervalId = setInterval(function () {
        if (urlParams.has("reply") && urlParams.get("reply") == "true") {
            var replyInput = document.getElementById("text-input");
            if (replyInput) {
                replyInput.focus();
                clearInterval(intervalId); // Clear the interval once the element is found
            }
        }

        if (urlParams.has("repost") && urlParams.get("repost") == "true") {
            var repostInput = document.getElementById("text-input");
            if (repostInput) {
                repostInput.focus();
                clearInterval(intervalId); // Clear the interval once the element is found
            }
        }
    }, 100); // Check every 100ms
}

window.onload = function () {
    // Grab all toggle-buttons
    var buttons = document.getElementsByClassName("toggle-button");

    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has("repost") && urlParams.get("repost") == "true") {
        // Hide all sections and make all buttons secondary
        for (var j = 0; j < buttons.length; j++) {
            var sectionId = buttons[j].id.replace("show-", "") + "-section";
            document.getElementById(sectionId).style.display = "none";
            buttons[j].classList.remove("btn-primary");
            buttons[j].classList.add("btn-secondary");
        }

        // Show the reposts-section and make the button primary
        document.getElementById("reposts-section").style.display = "block";
        // Assuming you have a button with id 'show-reposts'
        var button = document.getElementById("show-reposts");
        button.classList.remove("btn-secondary");
        button.classList.add("btn-primary");
    }

    // Use setTimeout to delay the focus execution
    setTimeout(focusTextInput, 200); // Adjust the delay as needed
};
