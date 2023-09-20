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

    fetch("/get_followed_usernames/")
    .then(response => response.json())
    .then(data => {
        usernames = data.usernames;
    });

    const textInput = document.getElementById("text-input");

    textInput.addEventListener("keyup", function(e) {
        const value = textInput.value;
        const lastAt = value.lastIndexOf('@');
        
        // Remove dropdown if "@" is removed
        if (lastAt === -1) {
            const existingDropdown = document.getElementById("autocomplete-dropdown");
            if (existingDropdown) {
                existingDropdown.remove();
            }
            return; // Exit the function
        }

        const filter = value.slice(lastAt + 1).toLowerCase();
        const filteredUsernames = usernames.filter(username => username.toLowerCase().startsWith(filter));
        showDropdown(filteredUsernames, filter, lastAt + 1); // Pass the position of the last '@' symbol
    });
    

    textInput.addEventListener("keydown", function(e) {
        if (e.key === "ArrowDown") {
            currentSelection++;
            highlightSelection();
        } else if (e.key === "ArrowUp") {
            currentSelection--;
            highlightSelection();
        } else if (e.key === "Enter") {
            e.preventDefault();
            selectUsername();
        }
    });
});

// Declare currentSelection at the top of your script
let currentSelection = -1;

function getCaretCoordinates(element, upToChar) {
    const { selectionStart } = element;
    const { offsetWidth, scrollHeight } = element;
    const computed = window.getComputedStyle(element);
    const lineHeight = parseFloat(computed.lineHeight);
    const paddingLeft = parseFloat(computed.paddingLeft);
    const paddingTop = parseFloat(computed.paddingTop);

    const lines = element.value.substring(0, upToChar).split("\n").length;
    const charactersInLine = element.value.substring(0, upToChar).split("\n")[lines - 1].length;

    const x = paddingLeft + (charactersInLine * offsetWidth / element.cols);
    const y = paddingTop + ((lines - 1) * lineHeight);

    return { x, y };
}

function highlightSelection() {
    const options = document.querySelectorAll("#autocomplete-dropdown div");
    options.forEach((option, index) => {
        if (index === currentSelection) {
            option.style.color = "rgb(13, 110, 253)"; // Highlight background
        } else {
            option.style.backgroundColor = ""; // Reset background
        }
    });
}


function selectUsername() {
    const options = document.querySelectorAll("#autocomplete-dropdown div");
    if (currentSelection >= 0 && currentSelection < options.length) {
        const selectedUsername = options[currentSelection].innerText;
        const textInput = document.getElementById("text-input");
        const value = textInput.value;
        const lastAt = value.lastIndexOf('@');
        textInput.value = value.slice(0, lastAt) + '@' + selectedUsername + ' ';
        document.getElementById("autocomplete-dropdown").remove();
        currentSelection = -1;
    }
}

function showDropdown(items, typedLetters = "", lastAtPosition) {
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
    const { x, y } = getCaretCoordinates(textInput, lastAtPosition); // Pass the position of the last '@' symbol

    // Get line height from computed styles
    const computed = window.getComputedStyle(textInput);
    const lineHeight = parseFloat(computed.lineHeight);
    
    // Position dropdown
    dropdown.style.left = `${textAreaRect.left + x}px`;
    dropdown.style.top = `${textAreaRect.top + y + lineHeight}px`;

    items.forEach((item, index) => {
        const option = document.createElement("div");
        option.innerText = item;
        if (index === currentSelection) {
            option.style.color = "rgb(13, 110, 253)"; // Updated background color
            option.style.padding = "0"; // Added padding
        } else {
            option.style.backgroundColor = ""; // Reset background
            option.style.padding = "0"; // Reset padding
        }
        option.addEventListener("click", function() {
            // Append selected username to textarea
            textInput.value += item + " ";
            dropdown.remove();
        });
        dropdown.appendChild(option);
    });

    document.body.appendChild(dropdown);
}

