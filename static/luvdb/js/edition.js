document.addEventListener("DOMContentLoaded", function() {

    function handleFormset(formsetId, buttonClass) {
        var formsetRows = document.querySelectorAll(formsetId + ' .row');
        var lastVisibleRow = null;

        formsetRows.forEach(function(row, index) {
            var selects = row.querySelectorAll('select');
            var hasSelectedOption = Array.from(selects).some(function(select) {
                return select.selectedOptions.length > 0 && select.selectedOptions[0].value != '';
            });

            if (index > 0 && !hasSelectedOption) {
                row.style.visibility = 'hidden';
                row.style.height = '0';
            } else {
                lastVisibleRow = row;
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
        button.className = 'btn btn-sm btn-light ' + buttonClass;

        innerDiv.appendChild(label);
        innerDiv.appendChild(button);
        buttonDiv.appendChild(innerDiv);
        lastVisibleRow.appendChild(buttonDiv);

        document.querySelector('.' + buttonClass).addEventListener('click', function() {
            var currentRow = this.parentElement.parentElement.parentElement;
            var nextHiddenRow = this.parentElement.parentElement.parentElement.nextElementSibling;
            if (nextHiddenRow) {
                nextHiddenRow.style.visibility = 'visible';
                nextHiddenRow.style.height = 'auto';

                // Add the "+" button to the next row
                var buttonDivClone = buttonDiv.cloneNode(true);
                nextHiddenRow.appendChild(buttonDivClone);
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

    // Call the function for edition-role-formset
    handleFormset('#edition-role-formset', 'add-edition-role');
    handleFormset('#edition-work-formset', 'add-edition-work');
});

$(document).ready(function() {
    $('select').removeClass('form-select');
});