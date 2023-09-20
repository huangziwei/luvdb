window.addEventListener('DOMContentLoaded', (event) => {
    // admonition hack
    document.querySelectorAll('.admonition.hide .admonition-title').forEach(titleElement => {
        titleElement.addEventListener('click', () => {
            titleElement.nextElementSibling.style.display = titleElement.nextElementSibling.style.display === 'none' ? 'block' : 'none';
        });
    });

    // spoiler hack
    document.querySelectorAll('a[href$="/spoiler"], a[href$="/s"]').forEach(a => {
        a.addEventListener('click', (e) => {
            e.preventDefault();
            if (a.classList.contains('revealed')) {
                a.classList.remove('revealed');
            } else {
                a.classList.add('revealed');
            }
        });
    });

    // citation hack
    document.querySelectorAll('a[href$="/citation"], a[href$="/c"]').forEach(a => {
        // Create a new 'cite' element
        const cite = document.createElement('cite');
        cite.textContent = a.textContent;
        
        // Replace the 'a' element with the 'cite' element
        a.parentNode.replaceChild(cite, a);
    });

    // citation hack continue: Get all cite elements
    var cites = document.getElementsByTagName('cite');

    // Loop through each cite element
    for (var i = 0; i < cites.length; i++) {
        // Get the previous element
        var previousElement = cites[i].parentElement;
        if (previousElement) {
            // Calculate the difference in their vertical positions
            var offset = previousElement.getBoundingClientRect().top - cites[i].getBoundingClientRect().top;
            
            // Apply a translateY transform to align the cite with the previous element
            cites[i].style.transform = 'translateY(' + offset + 'px)';
        }
    }

    function updateIframeHeight() {
        var iframes = document.querySelectorAll('iframe');
      
        iframes.forEach(function (iframe) {
          var originalWidth = iframe.getAttribute('width');
          var originalHeight = iframe.getAttribute('height');
          
          if (originalWidth && originalHeight) {
            var aspectRatio = originalHeight / originalWidth;
            var currentWidth = iframe.clientWidth;
            var newHeight = currentWidth * aspectRatio;
            iframe.style.height = newHeight + 'px';
          }
        });
      }
      
      // Update the iframe height when the page is loaded
      updateIframeHeight();
      
      // Update the iframe height when the window is resized
      window.addEventListener('resize', updateIframeHeight);

    // // dark mode toggle
    // document.getElementById('btnSwitch').addEventListener('click',()=>{
    //     if (document.documentElement.getAttribute('data-bs-theme') == 'dark') {
    //         document.documentElement.setAttribute('data-bs-theme','light')
    //     }
    //     else {
    //         document.documentElement.setAttribute('data-bs-theme','dark')
    //     }
    // })
    

    // // Function to resize images
    // function resizeImages(imgElements) {
    //     for (let img of imgElements) {
    //         img.style.maxWidth = "100%";
    //         img.style.height = "auto";
    //     }
    // }

    // // Resize images inside <p> tags
    // const markdownImages = document.querySelectorAll('p img');
    // resizeImages(markdownImages);
});

document.addEventListener("DOMContentLoaded", function() {
    let usernames = [];
    let tags = [];

    // Fetch usernames
    fetch("/get_followed_usernames/")
    .then(response => response.json())
    .then(data => {
        usernames = data.usernames;
    });

    // Fetch tags
    fetch("/get_user_tags/")
    .then(response => response.json())
    .then(data => {
        tags = data.tags;
    });

    const textInput = document.getElementById("text-input");

    textInput.addEventListener("keyup", function(e) {
        const value = textInput.value;
        let lastSymbol = null;
        let lastPos = -1;

        // Check for '@' and '#'
        const lastAt = value.lastIndexOf('@');
        const lastHash = value.lastIndexOf('#');

        if (lastAt > lastHash) {
            lastSymbol = '@';
            lastPos = lastAt;
        } else if (lastHash > lastAt) {
            lastSymbol = '#';
            lastPos = lastHash;
        }

        // Remove dropdown if last symbol is removed
        if (lastPos === -1) {
            const existingDropdown = document.getElementById("autocomplete-dropdown");
            if (existingDropdown) {
                existingDropdown.remove();
            }
            return;
        }

        const filter = value.slice(lastPos + 1).toLowerCase();
        let filteredItems = [];

        if (lastSymbol === '@') {
            filteredItems = usernames.filter(username => username.toLowerCase().startsWith(filter));
        } else if (lastSymbol === '#') {
            filteredItems = tags.filter(tag => tag.toLowerCase().startsWith(filter));
        }

        showDropdown(filteredItems, filter, lastPos + 1, lastSymbol); // Pass the position of the last symbol
    });
    

    textInput.addEventListener("keydown", function(e) {
        let lastSymbol = null;
        const value = textInput.value;
        const lastAt = value.lastIndexOf('@');
        const lastHash = value.lastIndexOf('#');
        const dropdown = document.getElementById("autocomplete-dropdown");
    
        if (lastAt > lastHash) {
            lastSymbol = '@';
        } else if (lastHash > lastAt) {
            lastSymbol = '#';
        }
    
        if (e.key === "ArrowDown") {
            currentSelection++;
            highlightSelection();
        } else if (e.key === "ArrowUp") {
            currentSelection--;
            highlightSelection();
        } else if (e.key === "Enter") {
            if (dropdown && lastSymbol) {  // Only prevent default if dropdown is visible and a symbol is present
                e.preventDefault();
                selectItem(lastSymbol);
            }
            // If dropdown is not visible or no symbol, the default "Enter" behavior will occur, creating a line break.
        }
    });
    
    
});

// Declare currentSelection at the top of your script
let currentSelection = -1;

function getCaretCoordinates(element, upToChar) {
    const text = element.value.substring(0, upToChar);
    const mirrorDiv = document.createElement('div');
    const computed = window.getComputedStyle(element);
    const lineHeight = parseFloat(computed.lineHeight);

    // Set up the mirror div's styles to match the textarea
    mirrorDiv.style.width = computed.width;
    mirrorDiv.style.height = computed.height;
    mirrorDiv.style.font = computed.font;
    mirrorDiv.style.whiteSpace = 'pre-wrap';
    mirrorDiv.style.wordWrap = 'break-word';
    mirrorDiv.style.padding = computed.padding;
    mirrorDiv.style.border = computed.border;
    mirrorDiv.style.visibility = 'hidden';
    mirrorDiv.style.position = 'absolute';
    mirrorDiv.style.zIndex = '-9999';
    mirrorDiv.textContent = text;

    document.body.appendChild(mirrorDiv);

    const span = document.createElement('span');
    span.textContent = element.value.substring(upToChar) || '.';  // Use '.' as a placeholder for empty space
    mirrorDiv.appendChild(span);

    const coordinates = {
        x: span.offsetLeft,
        y: span.offsetTop
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

    // Reset all options to default background
    options.forEach(option => {
        option.style.backgroundColor = "white";
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

function selectItem(symbol) {
    const dropdown = document.getElementById("autocomplete-dropdown");
    if (!dropdown) return;

    const options = dropdown.querySelectorAll("div");
    if (currentSelection >= 0 && currentSelection < options.length) {
        const selectedItem = options[currentSelection].innerText;
        const textInput = document.getElementById("text-input");
        const value = textInput.value;
        const lastSymbolPos = value.lastIndexOf(symbol);
        textInput.value = value.slice(0, lastSymbolPos) + symbol + selectedItem + ' ';
        dropdown.remove();
        console.log("removed dropdown");
        currentSelection = -1;
    }
}

function showDropdown(items, typedLetters = "", lastPos, lastSymbol) {
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

    // Get textarea element and its position
    const textInput = document.getElementById("text-input");
    const textAreaRect = textInput.getBoundingClientRect();
    const { x, y } = getCaretCoordinates(textInput, lastPos); // Pass the position of the last '@' symbol

    // Get line height from computed styles
    const computed = window.getComputedStyle(textInput);
    const lineHeight = parseFloat(computed.lineHeight);
    
    // Position dropdown
    dropdown.style.left = `${textAreaRect.left + x}px`;
    dropdown.style.top = `${textAreaRect.top + y + lineHeight}px`;

    items.forEach((item, index) => {
        const option = document.createElement("div");
        option.innerText = item;
        option.style.height = "25px"; // Set the height for each item
        if (index === currentSelection) {
            option.style.color = "rgb(13, 110, 253)"; // Updated background color
            option.style.paddingLeft = "5px"; // Added padding
        } else {
            option.style.color = ""; // Reset background
            option.style.paddingLeft = "5px"; // Reset padding
        }
        option.addEventListener("click", function() {
            // Append selected username to textarea
            textInput.value += item + " ";
            dropdown.remove();
        });
        dropdown.appendChild(option);
    });

    document.body.appendChild(dropdown);
    restoreScrollPosition(); // Restore the last scroll position
}

