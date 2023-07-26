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

    // Remove element with class 'footnote-backref' 
    var backref = footnoteSpan.getElementsByClassName('footnote-backref');
    if (backref[0]) {
        backref[0].remove();
    }

    // Append the footnote to the footnote reference
    refs[i].appendChild(footnoteSpan);
}


var popupParents = document.getElementsByClassName('popupnote-parent');

for (var i = 0; i < popupParents.length; i++) {
  popupParents[i].onmouseover = function() {
    var popup = this.getElementsByClassName('popupnote')[0];
    // Get bounding rectangle of the popup.
    var rect = popup.getBoundingClientRect();
    
    // If it's out of the left boundary of the viewport.
    if(rect.left < 0) {
      popup.style.left = '0';
      popup.style.transform = 'translateX(0)';
    }

    // If it's out of the right boundary of the viewport.
    else if(rect.right > window.innerWidth) {
      var overflowAmount = rect.right - window.innerWidth;
      popup.style.left = `calc(50% - ${overflowAmount}px)`;
    }
  }
}







