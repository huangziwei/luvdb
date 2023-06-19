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
        console.log(previousElement);
        if (previousElement) {
            // Calculate the difference in their vertical positions
            var offset = previousElement.getBoundingClientRect().top - cites[i].getBoundingClientRect().top;
            
            // Apply a translateY transform to align the cite with the previous element
            cites[i].style.transform = 'translateY(' + offset + 'px)';
        }
    }

});