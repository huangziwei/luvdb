////////////////////////////////
// Spoiler and citation hacks //
////////////////////////////////

window.addEventListener("DOMContentLoaded", (event) => {
    // spoiler hack
    document.querySelectorAll('a[href$="/spoiler"], a[href$="/s"]').forEach((a) => {
        a.addEventListener("click", (e) => {
            e.preventDefault();
            if (a.classList.contains("revealed")) {
                a.classList.remove("revealed");
            } else {
                a.classList.add("revealed");
            }
        });
    });

    // citation hack
    document.querySelectorAll('a[href$="/citation"], a[href$="/c"]').forEach((a) => {
        // Create a new 'cite' element
        const cite = document.createElement("cite");
        cite.textContent = a.textContent;

        // Replace the 'a' element with the 'cite' element
        a.parentNode.replaceChild(cite, a);
    });

    // citation hack continue: Get all cite elements
    var cites = document.getElementsByTagName("cite");

    // Loop through each cite element
    for (var i = 0; i < cites.length; i++) {
        // Get the previous element
        var previousElement = cites[i].parentElement;
        if (previousElement) {
            // Calculate the difference in their vertical positions
            var offset = previousElement.getBoundingClientRect().top - cites[i].getBoundingClientRect().top;

            // Apply a translateY transform to align the cite with the previous element
            cites[i].style.transform = "translateY(" + offset + "px)";
        }
    }

    function updateIframeHeight() {
        var iframes = document.querySelectorAll("iframe");

        iframes.forEach(function (iframe) {
            var originalWidth = iframe.getAttribute("width");
            var originalHeight = iframe.getAttribute("height");

            if (originalWidth && originalHeight) {
                var aspectRatio = originalHeight / originalWidth;
                var currentWidth = iframe.clientWidth;
                var newHeight = currentWidth * aspectRatio;
                iframe.style.height = newHeight + "px";
            }
        });
    }

    // Update the iframe height when the page is loaded
    updateIframeHeight();

    // Update the iframe height when the window is resized
    window.addEventListener("resize", updateIframeHeight);
});

//////////////////////////////////////
// Autocomplete @ and # in textarea //
//////////////////////////////////////

document.addEventListener("DOMContentLoaded", function () {
    let usernames = [];
    let tags = [];
    let lastDropdownTriggerPos = -1;
    let dataFetched = false; // Flag to track if data has been fetched

    const textInputs = Array.from(document.querySelectorAll('[id="text-input"]'));
    textInputs.forEach((textInput) => {
        if (textInput !== null) {
            // Event listener for click to fetch data
            textInput.addEventListener("click", function () {
                if (!dataFetched) {
                    // Fetch usernames
                    fetch("/get_followed_usernames/")
                        .then((response) => response.json())
                        .then((data) => {
                            usernames = data.usernames_with_display_names;
                        });

                    // Fetch tags
                    fetch("/get_user_tags/")
                        .then((response) => response.json())
                        .then((data) => {
                            tags = data.tags;
                        });

                    dataFetched = true; // Update the flag
                }
            });

            textInput.addEventListener("keyup", function (e) {
                const value = textInput.value;
                let lastSymbol = null;
                let lastPos = -1;

                // Check for '@' and '#'
                const lastAt = value.lastIndexOf("@");
                const lastHash = value.lastIndexOf("#");

                if (lastAt > lastHash) {
                    lastSymbol = "@";
                    lastPos = lastAt;
                } else if (lastHash > lastAt) {
                    lastSymbol = "#";
                    lastPos = lastHash;
                }

                // Update lastDropdownTriggerPos when a dropdown is shown
                if (lastPos !== -1) {
                    lastDropdownTriggerPos = lastPos;
                }

                // Check the current last @ or # in the text
                const currentLastAt = textInput.value.lastIndexOf("@");
                const currentLastHash = textInput.value.lastIndexOf("#");
                const currentLastPos = Math.max(currentLastAt, currentLastHash);

                // Remove dropdown if the last trigger symbol is different from the current last symbol
                if (lastDropdownTriggerPos == currentLastPos) {
                    const existingDropdown = document.getElementById("autocomplete-dropdown");
                    if (existingDropdown) {
                        existingDropdown.remove();
                    }
                    lastDropdownTriggerPos = -1; // Reset the last dropdown trigger position
                }

                const filter = value.slice(lastPos + 1).toLowerCase();
                let filteredItems = [];

                if (lastSymbol === "@") {
                    filteredItems = usernames.filter(
                        (user) =>
                            user.username.toLowerCase().startsWith(filter) ||
                            (user.display_name && user.display_name.toLowerCase().startsWith(filter))
                    );
                } else if (lastSymbol === "#") {
                    filteredItems = tags.filter((tag) => tag.toLowerCase().startsWith(filter));
                }

                showDropdown(filteredItems, filter, lastPos + 1, lastSymbol, textInput); // Pass the position of the last symbol
            });

            textInput.addEventListener("keydown", function (e) {
                let lastSymbol = null;
                const value = textInput.value;
                const lastAt = value.lastIndexOf("@");
                const lastHash = value.lastIndexOf("#");
                const dropdown = document.getElementById("autocomplete-dropdown");

                if (lastAt > lastHash) {
                    lastSymbol = "@";
                } else if (lastHash > lastAt) {
                    lastSymbol = "#";
                }

                if (e.key === "ArrowDown") {
                    currentSelection++;
                    highlightSelection();
                } else if (e.key === "ArrowUp") {
                    currentSelection--;
                    highlightSelection();
                } else if (e.key === "Enter") {
                    if (dropdown && lastSymbol) {
                        // Only prevent default if dropdown is visible and a symbol is present
                        e.preventDefault();
                        selectItem(lastSymbol, textInput);
                    }
                    // If dropdown is not visible or no symbol, the default "Enter" behavior will occur, creating a line break.
                }
            });
        }
    });
});

// Declare currentSelection at the top of your script
let currentSelection = -1;

function getCaretCoordinates(element, upToChar) {
    const text = element.value.substring(0, upToChar);
    const mirrorDiv = document.createElement("div");
    const computed = window.getComputedStyle(element);
    const lineHeight = parseFloat(computed.lineHeight);

    // Set up the mirror div's styles to match the textarea
    mirrorDiv.style.width = computed.width;
    mirrorDiv.style.height = computed.height;
    mirrorDiv.style.font = computed.font;
    mirrorDiv.style.whiteSpace = "pre-wrap";
    mirrorDiv.style.wordWrap = "break-word";
    mirrorDiv.style.padding = computed.padding;
    mirrorDiv.style.border = computed.border;
    mirrorDiv.style.visibility = "hidden";
    mirrorDiv.style.position = "absolute";
    mirrorDiv.style.zIndex = "-9999";
    mirrorDiv.textContent = text;

    document.body.appendChild(mirrorDiv);

    const span = document.createElement("span");
    span.textContent = element.value.substring(upToChar) || "."; // Use '.' as a placeholder for empty space
    mirrorDiv.appendChild(span);

    const coordinates = {
        x: span.offsetLeft,
        y: span.offsetTop,
    };

    document.body.removeChild(mirrorDiv);

    return coordinates;
}

let lastScrollTop = 0; // Variable to store the last scroll position

function highlightSelection() {
    const dropdown = document.getElementById("autocomplete-dropdown");
    if (!dropdown) return;

    const options = dropdown.querySelectorAll("div");
    if (options.length === 0) return;

    const isDarkMode = document.documentElement.getAttribute("data-bs-theme") === "dark";

    // Reset all options to default background
    options.forEach((option) => {
        if (isDarkMode) {
            option.classList.add("bg-dark");
            option.classList.remove("bg-light"); // Remove this if you don't use bg-light in light mode
        } else {
            option.classList.remove("bg-dark");
            option.classList.add("bg-light"); // Add this if you use bg-light in light mode
        }
    });

    // Adjust current selection within bounds
    if (currentSelection < 0) {
        currentSelection = 0;
    } else if (currentSelection >= options.length) {
        currentSelection = options.length - 1;
    }

    // Highlight the current selection
    const selectedOption = options[currentSelection];
    selectedOption.style.color = "rgb(13, 110, 253)";
    selectedOption.style.paddingLeft = "5px";

    // Scroll the dropdown to make the selected option visible
    const optionHeight = selectedOption.offsetHeight;
    const scrollTop = dropdown.scrollTop;
    const scrollBottom = scrollTop + dropdown.clientHeight;

    if (selectedOption.offsetTop < scrollTop) {
        dropdown.scrollTop = selectedOption.offsetTop;
    } else if (selectedOption.offsetTop + optionHeight > scrollBottom) {
        dropdown.scrollTop = selectedOption.offsetTop + optionHeight - dropdown.clientHeight;
    }

    lastScrollTop = dropdown.scrollTop; // Store the last scroll position
}

// Call this function after any operation that might reset the dropdown scroll position
function restoreScrollPosition() {
    const dropdown = document.getElementById("autocomplete-dropdown");
    if (dropdown) {
        dropdown.scrollTop = lastScrollTop;
    }
}

function selectItem(symbol, textInput) {
    const dropdown = document.getElementById("autocomplete-dropdown");
    if (!dropdown) return;

    const options = dropdown.querySelectorAll("div");
    if (currentSelection >= 0 && currentSelection < options.length) {
        const selectedItem = options[currentSelection].username
            ? options[currentSelection].username
            : options[currentSelection].innerText;

        const value = textInput.value;
        const lastSymbolPos = value.lastIndexOf(symbol);
        textInput.value = value.slice(0, lastSymbolPos) + symbol + selectedItem + " ";
        dropdown.remove();
        currentSelection = -1;
    }
}

function showDropdown(items, typedLetters = "", lastPos, lastSymbol, textInput) {
    if (items.length === 0) return;
    // Remove existing dropdown if any
    const existingDropdown = document.getElementById("autocomplete-dropdown");
    if (existingDropdown) {
        existingDropdown.remove();
    }

    // Create dropdown
    const dropdown = document.createElement("div");
    dropdown.id = "autocomplete-dropdown";
    dropdown.style.position = "absolute";
    const isDarkMode = document.documentElement.getAttribute("data-bs-theme") === "dark";
    if (isDarkMode) {
        dropdown.classList.add("bg-dark");
        dropdown.classList.remove("bg-light"); // Remove this if you don't use bg-light in light mode
    } else {
        dropdown.classList.remove("bg-dark");
        dropdown.classList.add("bg-light"); // Add this if you use bg-light in light mode
    }
    // Get textarea element and its position
    // const textInput = document.getElementById("text-input");
    const textAreaRect = textInput.getBoundingClientRect();
    const { x, y } = getCaretCoordinates(textInput, lastPos); // Pass the position of the last '@' symbol

    // Get line height from computed styles
    const computed = window.getComputedStyle(textInput);
    const lineHeight = parseFloat(computed.lineHeight);

    // Position dropdown
    dropdown.style.left = `${textAreaRect.left + x + window.scrollX}px`;
    dropdown.style.top = `${textAreaRect.top + y + lineHeight + window.scrollY}px`;

    items.forEach((item, index) => {
        const option = document.createElement("div");
        let displayText;
        if (lastSymbol === "@") {
            displayText = item.display_name ? `${item.display_name} (${item.username})` : item.username;
            option.username = item.username;
        } else if (lastSymbol === "#") {
            displayText = item; // Assuming 'item' is a string for tags
        }

        option.innerText = displayText;
        option.style.height = "25px"; // Set the height for each item
        if (index === currentSelection) {
            option.style.color = "rgb(13, 110, 253)"; // Updated background color
            option.style.paddingLeft = "5px"; // Added padding
        } else {
            option.style.color = ""; // Reset background
            option.style.paddingLeft = "5px"; // Reset padding
        }
        option.addEventListener("click", function () {
            const selectedUsername = this.username || this.innerText;
            textInput.value = textInput.value.slice(0, lastPos) + selectedUsername + " ";
            dropdown.remove();
        });
        dropdown.appendChild(option);
    });

    document.body.appendChild(dropdown);
    restoreScrollPosition(); // Restore the last scroll position
}

//////////////////////
// Dark Mode Button //
//////////////////////

document.addEventListener("DOMContentLoaded", function () {
    const toggleButton = document.getElementById("darkModeToggle");
    toggleButton.style.display = "inline-block";

    const htmlElement = document.documentElement;
    const bgLightElements = document.querySelectorAll(".bg-light");
    const stickyNoteElements = document.querySelectorAll(".sticky-note");
    const faIcons = document.querySelectorAll(".fa-icon path");
    const metaThemeColor = document.querySelector("meta[name=theme-color]");
    console.log(metaThemeColor);
    const pygmentsCss = document.getElementById("pygments-css");

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
            faIcons.forEach((el) => el.setAttribute("fill", "#ccc")); // Dark mode color for FontAwesome icons
            stickyNoteElements.forEach((el) => el.classList.add("bg-dark"));
            pygmentsCss.href = pygmentsCssDark; // Use the variable defined in the template
        } else {
            htmlElement.removeAttribute("data-bs-theme");
            bgLightElements.forEach((el) => el.classList.remove("bg-dark-highlight"));
            metaThemeColor.setAttribute("content", "#ECEEEE");
            faIcons.forEach((el) => el.setAttribute("fill", "#6C757D")); // Original color for FontAwesome icons
            stickyNoteElements.forEach((el) => el.classList.remove("bg-dark"));
            pygmentsCss.href = pygmentsCssLight; // Use the variable defined in the template
        }
    }

    function getSystemPreferredTheme() {
        if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
            return "dark";
        }
        return "light";
    }
});

////////////////////
// Popup Footnote //
////////////////////

// Select all footnote references in the main text
var refs = document.querySelectorAll(".footnote-ref");

// Loop through all references
refs.forEach(function (ref) {
    // Get the id of the corresponding footnote
    var footnoteId = ref.getAttribute("href").slice(1);

    // Select the corresponding footnote
    var footnoteLi = document.getElementById(footnoteId);
    if (!footnoteLi) return; // Skip if no matching footnote found

    var footnoteSpan = document.createElement("span");
    footnoteSpan.className = "popupnote";
    ref.className = "popupnote-parent";

    // Clone and clean content from the li to the span
    var clonedFootnote = footnoteLi.cloneNode(true);
    var backref = clonedFootnote.querySelector(".footnote-backref");
    if (backref) backref.remove();

    footnoteSpan.innerHTML = clonedFootnote.innerHTML;

    // Append the footnote to the footnote reference
    ref.appendChild(footnoteSpan);
});

// Adjust popup position on mouseover
var popupParents = document.querySelectorAll(".popupnote-parent");
popupParents.forEach(function (parent) {
    parent.onmouseover = function () {
        var popup = this.querySelector(".popupnote");
        var rect = popup.getBoundingClientRect();

        if (rect.left < 0) {
            popup.style.left = "0";
            popup.style.transform = "translateX(0)";
        } else if (rect.right > window.innerWidth) {
            var overflowAmount = rect.right - window.innerWidth;
            popup.style.left = `calc(50% - ${overflowAmount}px)`;
        }
    };
});

// hack to make tab blocks work
window.onload = function () {
    const tabbedSets = document.getElementsByClassName("tabbed-set");
    for (let i = 0; i < tabbedSets.length; i++) {
        const tabbedSet = tabbedSets[i];
        tabbedSet.setAttribute("data-tabs", i + 1 + ":" + tabbedSet.getAttribute("data-tabs").split(":")[1]);

        const inputs = tabbedSet.getElementsByTagName("input");
        for (let j = 0, len = inputs.length; j < len; j++) {
            const input = inputs[j];
            input.name = "__tabbed_" + (i + 1);
            input.id += "_" + (i + 1);
            if (j === 0) {
                input.checked = true;
            }
        }

        const labels = tabbedSet.getElementsByTagName("label");
        for (let k = 0, len = labels.length; k < len; k++) {
            labels[k].htmlFor += "_" + (i + 1);
        }
    }
};

/////////////////
/// load time ///
/////////////////
window.addEventListener("load", (event) => {
    var loadTime = performance.now();
    document.getElementById("loadTime").textContent = Math.round(loadTime) / 1000 + "s";
});

/////////////////////
/// image preview ///
/////////////////////

document.addEventListener("DOMContentLoaded", function () {
    // Find the anchor tag
    var currentLink = document.querySelector(".input-group .form-control a");
    if (currentLink) {
        // Get the href attribute from the anchor tag
        var imageURL = currentLink.href;

        // Create a new image element
        var imgTag = document.createElement("img");
        imgTag.src = imageURL;
        imgTag.alt = "Cover Image";
        imgTag.style.maxWidth = "150px";
        imgTag.style.maxHeight = "150px";

        // Replace the anchor tag with the new image element
        var parentDiv = currentLink.parentElement;
        parentDiv.replaceChild(imgTag, currentLink);
    }
});

////////////////////
/// Image upload ///
////////////////////

document.addEventListener("DOMContentLoaded", function () {
    const uploadArea = document.getElementById("upload-area");
    const photoUpload = document.getElementById("photo-upload");
    const textInput = document.getElementById("text-input");
    const photoUploadSection = document.getElementById("photoUploadSection");
    const imageIconButton = document.getElementById("image-upload-button");

    let dragCounter = 0;

    if (uploadArea && photoUpload) {
        // Trigger the file input click when clicking the upload area
        uploadArea.addEventListener("click", function () {
            photoUpload.click();
        });

        // Handle file selection from the file input
        photoUpload.addEventListener("change", function () {
            uploadFiles(this.files);
        });

        // Handle drag and drop over the upload area
        uploadArea.addEventListener("dragover", function (event) {
            event.preventDefault();
            event.stopPropagation();
            photoUploadSection.classList.add("border-primary");
        });

        uploadArea.addEventListener("dragleave", function (event) {
            event.preventDefault();
            event.stopPropagation();
            photoUploadSection.classList.remove("border-primary");
        });

        uploadArea.addEventListener("drop", function (event) {
            event.preventDefault();
            event.stopPropagation();
            photoUploadSection.classList.remove("border-primary");
            uploadFiles(event.dataTransfer.files);
        });
    }

    // Handle drag events on the document to track drag count accurately
    if (photoUploadSection) {
        document.addEventListener("dragenter", function (event) {
            event.preventDefault();
            event.stopPropagation();
            dragCounter++;
            if (dragCounter === 1) {
                photoUploadSection.classList.add("show-upload-area");
            }
        });

        document.addEventListener("dragleave", function (event) {
            event.preventDefault();
            event.stopPropagation();
            dragCounter--;
            if (dragCounter === 0) {
                photoUploadSection.classList.remove("show-upload-area");
            }
        });

        document.addEventListener("drop", function (event) {
            event.preventDefault();
            event.stopPropagation();
            dragCounter = 0;
            photoUploadSection.classList.remove("show-upload-area");
        });

        // Hide the upload area when clicking outside of it
        document.addEventListener("click", function (event) {
            if (!photoUploadSection.contains(event.target) && !imageIconButton.contains(event.target)) {
                photoUploadSection.classList.remove("show-upload-area");
                dragCounter = 0; // Reset the drag counter
            }
        });
    }

    // Open the file input dialog when clicking the image icon button
    if (imageIconButton) {
        imageIconButton.addEventListener("click", function () {
            photoUpload.click();
        });
    }

    function uploadFiles(files) {
        const formData = new FormData();
        for (let i = 0; i < files.length; i++) {
            formData.append("photos", files[i]);
        }
        formData.append("csrfmiddlewaretoken", getCsrfToken());

        const xhr = new XMLHttpRequest();
        xhr.open("POST", "/upload_photos/", true);
        xhr.onload = function () {
            if (xhr.status === 200) {
                const response = JSON.parse(xhr.responseText);
                if (response.photo_ids) {
                    insertMarkdown(response.photo_ids);
                    response.photo_ids.forEach((photo_id) => {
                        showNotification(`Image ${photo_id} uploaded successfully`);
                    });
                }
                photoUploadSection.classList.remove("show-upload-area"); // Hide the upload area after upload
                dragCounter = 0; // Reset the drag counter
            } else {
                alert("An error occurred while uploading the photos.");
            }
        };
        xhr.send(formData);
    }

    function insertMarkdown(photo_ids) {
        const textarea = document.querySelector('textarea[name="content"]');
        if (textarea) {
            const currentContent = textarea.value;
            const markdown = photo_ids.map((id) => `![](${id})`).join("\n");
            textarea.value = currentContent + "\n" + markdown;
        }
    }

    function getCsrfToken() {
        return document.querySelector("[name=csrfmiddlewaretoken]").value;
    }

    function showNotification(message) {
        const notificationContainer = document.getElementById("notification-container");
        const notification = document.createElement("div");
        notification.className = "notification-popup";
        notification.textContent = message;
        notificationContainer.appendChild(notification);

        setTimeout(() => {
            notificationContainer.removeChild(notification);
        }, 3000); // Show each notification for 3 seconds
    }
});
