document.addEventListener("DOMContentLoaded", function() {

    function handleFormset(formsetId, buttonClass) {
        var formsetRows = document.querySelectorAll(formsetId + ' .form-wrapper');
        var lastVisibleRow = null;

        formsetRows.forEach(function(row, index) {
            var selects = row.querySelectorAll('select');
            var inputs = row.querySelectorAll('input[type="text"]');
            var hasSelectedOption = Array.from(selects).some(function(select) {
                return select.selectedOptions.length > 0 && select.selectedOptions[0].value != '';
            });
            var hasInputData = Array.from(inputs).some(function(input) {
                return input.value.trim() !== '';
            });

            var shouldHide = index > 0 && !hasSelectedOption && !hasInputData;

            if (formsetId === "#regionreleasedates") {
                shouldHide = index > 0 && !hasInputData;
            }

            if (shouldHide) {
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
        lastVisibleRow.lastElementChild.appendChild(buttonDiv);

        document.querySelector('.' + buttonClass).addEventListener('click', function() {
            var currentRow = this.parentElement.parentElement.parentElement.parentElement;
            var nextHiddenRow = currentRow.nextElementSibling;
            if (nextHiddenRow) {
                nextHiddenRow.style.visibility = 'visible';
                nextHiddenRow.style.height = 'auto';
                nextHiddenRow.classList.add('mb-3', 'p-2');

                // Add the "+" button to the next row
                var buttonDivClone = buttonDiv.cloneNode(true);
                nextHiddenRow.lastElementChild.appendChild(buttonDivClone);
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

    // Export the function for usage in other files
    window.handleFormset = handleFormset;
});
