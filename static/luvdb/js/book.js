document.addEventListener("DOMContentLoaded", function() {
    // Initially hide all formset rows except the first one
    var formsetRows = document.querySelectorAll('#book-role-formset .row');
    formsetRows.forEach(function(row, index) {
        // Get all select fields within the row
        var selects = row.querySelectorAll('select');

        // Check if any select field has a selected option
        var hasSelectedOption = Array.from(selects).some(function(select) {
            return select.selectedOptions.length > 0 && select.selectedOptions[0].value != '';
        });

        // Hide the row only if it's not the first one and if no select field has a selected option
        if (index > 0 && !hasSelectedOption) {
            row.style.visibility = 'hidden';
            row.style.height = '0';
        }
    });

    // Add a button to the end of each row
    formsetRows.forEach(function(row) {
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
        button.className = 'btn btn-sm btn-light add-book-role';

        innerDiv.appendChild(label);
        innerDiv.appendChild(button);
        buttonDiv.appendChild(innerDiv);
        row.appendChild(buttonDiv);
    });

    // When the button is clicked, reveal the next hidden row and hide the add links
    document.querySelectorAll('.add-book-role').forEach(function(addButton) {
        addButton.addEventListener('click', function() {
            // Define the current row before removing the button
            var currentRow = this.parentElement.parentElement.parentElement;
            
            var nextHiddenRow = this.parentElement.parentElement.parentElement.nextElementSibling;
            if (nextHiddenRow) {
                nextHiddenRow.style.visibility = 'visible';
                nextHiddenRow.style.height = 'auto';
            }
            // Remove the button from the current row
            this.parentElement.parentElement.remove();

            // Hide the add links in the current row
            var addLinks = currentRow.querySelectorAll('a.text-secondary');
            addLinks.forEach(function(link) {
                link.style.display = 'none';
            });
        });
    });

    // New code for BookWork formset:
    var formsetRows = document.querySelectorAll('#book-work-formset .row');
    formsetRows.forEach(function(row, index) {
        // Get all select fields within the row
        var selects = row.querySelectorAll('select');

        // Check if any select field has a selected option
        var hasSelectedOption = Array.from(selects).some(function(select) {
            return select.selectedOptions.length > 0 && select.selectedOptions[0].value != '';
        });

        // Hide the row only if it's not the first one and if no select field has a selected option
        if (index > 0 && !hasSelectedOption) {
            row.style.visibility = 'hidden';
            row.style.height = '0';
        }
    });

    formsetRows.forEach(function(row) {
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
        button.className = 'btn btn-sm btn-light add-book-work';

        innerDiv.appendChild(label);
        innerDiv.appendChild(button);
        buttonDiv.appendChild(innerDiv);
        row.appendChild(buttonDiv);
    });

    document.querySelectorAll('.add-book-work').forEach(function(addButton) {
        addButton.addEventListener('click', function() {
            var currentRow = this.parentElement.parentElement.parentElement;
            var nextHiddenRow = this.parentElement.parentElement.parentElement.nextElementSibling;
            if (nextHiddenRow) {
                nextHiddenRow.style.visibility = 'visible';
                nextHiddenRow.style.height = 'auto';
            }
            this.parentElement.parentElement.remove();
            var addLinks = currentRow.querySelectorAll('a.text-secondary');
            addLinks.forEach(function(link) {
                link.style.display = 'none';
            });
        });
    });
});

$(document).ready(function() {
    $('select').removeClass('form-select');
});