// Select all footnote references in the main text
var refs = document.querySelectorAll('.footnote-ref');

// Loop through all references
for (var i = 0; i < refs.length; i++) {
    // Get the id of the corresponding footnote
    var footnoteId = refs[i].getAttribute('href').slice(4);

    // Select the corresponding footnote
    var footnote = document.querySelector('.footnote ol li p a[href="#fnref:' + footnoteId + '"]').parentElement.cloneNode(true);
    
    footnote.setAttribute('class', "popupnote");
    refs[i].setAttribute('class', 'popupnote-parent');

    // Append the footnote to the footnote reference
    refs[i].appendChild(footnote);
}
