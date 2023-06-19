// Select all footnote references in the main text
var refs = document.querySelectorAll('.footnote-ref');

// Loop through all references
for (var i = 0; i < refs.length; i++) {
    // Get the id of the corresponding footnote
    var footnoteId = refs[i].getAttribute('href').slice(4);

    // Select the corresponding footnote
    var footnoteP = document.querySelector('.footnote ol li p a[href="#fnref:' + footnoteId + '"]').parentElement.cloneNode(true);

    // Create a new span element
    var footnoteSpan = document.createElement('span');

    // Copy the class and content from the p to the span
    footnoteSpan.className = footnoteP.className;
    footnoteSpan.innerHTML = footnoteP.innerHTML;

    footnoteSpan.setAttribute('class', "popupnote");
    refs[i].setAttribute('class', 'popupnote-parent');

    // Append the footnote to the footnote reference
    refs[i].appendChild(footnoteSpan);
}


$(window).on('resize scroll', function() {
    var leftColumn = $('.left-column').offset();
    var citeWidth = $('cite').outerWidth();
    $('cite').css({
        position: 'absolute',
        top: leftColumn.top,
        left: leftColumn.left - citeWidth
    });
}).trigger('resize'); // Trigger resize to position cite on page load