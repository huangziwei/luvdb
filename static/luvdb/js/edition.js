document.addEventListener("DOMContentLoaded", function() {
    // Initially hide all formset rows except the first one
    var formsetRows = document.querySelectorAll('#edition-role-formset .row');
    formsetRows.forEach(function(row, index) {
        if (index > 0) {
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
        button.className = 'btn btn-sm btn-light add-edition-role';

        innerDiv.appendChild(label);
        innerDiv.appendChild(button);
        buttonDiv.appendChild(innerDiv);
        row.appendChild(buttonDiv);
    });

    // When the button is clicked, reveal the next hidden row and hide the add links
    document.querySelectorAll('.add-edition-role').forEach(function(addButton) {
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
});

$(document).ready(function() {
    $('select').removeClass('form-select');
});