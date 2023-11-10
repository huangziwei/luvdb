document.addEventListener("DOMContentLoaded", function () {
    function handleFormset(formsetId, buttonClass) {
        var formsetRows = document.querySelectorAll(formsetId + " .form-wrapper");
        var lastVisibleRow = null;

        formsetRows.forEach(function (row, index) {
            var inputs = row.querySelectorAll('input[type="text"]');
            var hasInputData = Array.from(inputs).some(function (input) {
                return input.value.trim() !== "";
            });

            var instanceSelect = row.querySelector('select[name$="instance"]');
            var hasInstanceSelected =
                instanceSelect &&
                instanceSelect.selectedOptions.length > 0 &&
                instanceSelect.selectedOptions[0].value != "";

            var trackSelect = row.querySelector('select[name$="track"]');
            var hasTrackSelected =
                trackSelect &&
                trackSelect.selectedOptions.length > 0 &&
                trackSelect.selectedOptions[0].value != "";

            var creatorSelect = row.querySelector('select[name$="creator"]');
            var hasCreatorSelected =
                creatorSelect &&
                creatorSelect.selectedOptions.length > 0 &&
                creatorSelect.selectedOptions[0].value != "";

            var shouldHide = index > 0 && !hasCreatorSelected && !hasInputData;

            if (formsetId === "#regionreleasedates") {
                shouldHide = index > 0 && !hasInputData;
            }

            if (formsetId === "#release-track-formset") {
                shouldHide = index > 0 && !hasTrackSelected;
            }

            if (formsetId === "#book-instance-formset" || formsetId === "#issue-instance-formset") {
                shouldHide = index > 0 && !hasInstanceSelected;
            }

            if (shouldHide) {
                row.style.visibility = "hidden";
                row.style.height = "0";
                row.classList.add("bg-light");
            } else {
                lastVisibleRow = row;
                row.classList.add("bg-light", "p-2", "mb-3");
            }
        });

        // Add the "+" button to the last visible row only
        var buttonDiv = document.createElement("div");
        buttonDiv.className = "col-md-1 mb-3";
        var innerDiv = document.createElement("div");
        innerDiv.className = "mb-1";
        var label = document.createElement("label");
        label.className = "form-label";
        label.textContent = "Add";
        var button = document.createElement("button");
        button.type = "button";
        button.textContent = "+";
        button.className = "btn btn-sm btn-outline-secondary " + buttonClass;

        innerDiv.appendChild(label);
        innerDiv.appendChild(button);
        buttonDiv.appendChild(innerDiv);
        lastVisibleRow.lastElementChild.appendChild(buttonDiv);

        document.querySelector("." + buttonClass).addEventListener("click", function () {
            var currentRow = this.parentElement.parentElement.parentElement.parentElement;
            var nextHiddenRow = currentRow.nextElementSibling;
            if (nextHiddenRow) {
                nextHiddenRow.style.visibility = "visible";
                nextHiddenRow.style.height = "auto";
                nextHiddenRow.classList.add("mb-3", "p-2");

                // Add the "+" button to the next row
                var buttonDivClone = buttonDiv.cloneNode(true);
                nextHiddenRow.lastElementChild.appendChild(buttonDivClone);
                var addButton = buttonDivClone.querySelector("button");
                addButton.addEventListener("click", arguments.callee);
            }

            // Remove the "+" button from the current row
            this.parentElement.parentElement.remove();

            // Hide the add links in the current row
            var addLinks = currentRow.querySelectorAll("a.text-secondary");
            addLinks.forEach(function (link) {
                link.style.display = "none";
            });
        });
    }

    // Export the function for usage in other files
    window.handleFormset = handleFormset;
});
