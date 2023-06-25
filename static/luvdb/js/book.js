document.addEventListener("DOMContentLoaded", function() {
    
    function handleFormset(formsetId, buttonClass) {
        var formsetRows = document.querySelectorAll(formsetId + ' .form-wrapper');
        var lastVisibleRow = null;

        formsetRows.forEach(function(row, index) {
            var selects = row.querySelectorAll('select');
            var hasSelectedOption = Array.from(selects).some(function(select) {
                return select.selectedOptions.length > 0 && select.selectedOptions[0].value != '';
            });

            if (index > 0 && !hasSelectedOption) {
                row.style.visibility = 'hidden';
                row.style.height = '0';
                row.classList.add('bg-light');
            } else {
                lastVisibleRow = row;
                row.classList.add('bg-light', 'p-2', 'mb-3');
            }
            
        });

        // Add the "+" button to the last visible row only
        var buttonDiv = document.createElement('div');
        buttonDiv.className = 'col-md-1 mb-5';
        var innerDiv = document.createElement('div');
        innerDiv.className = 'mb-1';
        var label = document.createElement('label');
        label.className = 'form-label';
        label.textContent = 'Add';
        var button = document.createElement('button');
        button.type = 'button';
        button.textContent = '+';
        button.className = 'btn btn-sm btn-outline-secondary ' + buttonClass;

        innerDiv.appendChild(label);
        innerDiv.appendChild(button);
        buttonDiv.appendChild(innerDiv);
        lastVisibleRow.lastElementChild.appendChild(buttonDiv);  // Change this line

        document.querySelector('.' + buttonClass).addEventListener('click', function() {
            var currentRow = this.parentElement.parentElement.parentElement.parentElement;  // Change this line
            var nextHiddenRow = this.parentElement.parentElement.parentElement.parentElement.nextElementSibling;  // Change this line
            if (nextHiddenRow) {
                nextHiddenRow.style.visibility = 'visible';
                nextHiddenRow.style.height = 'auto';
                nextHiddenRow.classList.add('mb-3', 'p-2');

                // Add the "+" button to the next row
                var buttonDivClone = buttonDiv.cloneNode(true);
                nextHiddenRow.lastElementChild.appendChild(buttonDivClone);  // Change this line
                var addButton = buttonDivClone.querySelector('button');
                addButton.addEventListener('click', arguments.callee);
            }

            // Remove the "+" button from the current row
            this.parentElement.parentElement.remove();

            // Hide the add links in the current row
            var addLinks = currentRow.querySelectorAll('a.text-secondary');
            addLinks.forEach(function(link) {
                link.style.display = 'none';
            });
        });
    }

    // Call the function for book-role-formset and book-work-formset
    handleFormset('#book-role-formset', 'add-book-role');
    handleFormset('#book-work-formset', 'add-book-work');
    handleFormset('#book-edition-formset', 'add-book-edition');
});

// $(document).ready(function() {
//     $('select').removeClass('form-select');
// });

$(document).ready(function() {
    $('select').on('select2:open', function (e) {
        $('span.select2-selection--single').removeClass('form-select');
    });
});