document.addEventListener('DOMContentLoaded', function() {
    // Remove the 'selected' class from all buttons
    const allButtons = document.querySelectorAll('.activity-filter');
    allButtons.forEach(button => button.classList.remove('selected'));

    // Check if there's a saved filter and apply it
    const savedFilter = localStorage.getItem('selectedFilter');

    if (savedFilter) {
        filterActivities(savedFilter);

        // Find the button that corresponds to the saved filter
        const savedButton = findButtonToHighlight(savedFilter);

        if (savedButton) {
            // If the saved button is a dropdown item, swap it with the main button
            if (savedButton.classList.contains('dropdown-item')) {
                const parentBtnGroup = savedButton.closest('.btn-group');
                const mainButton = parentBtnGroup.querySelector('.activity-filter:not(.dropdown-item)');
                swapButtonAttributes(savedButton, mainButton);
            }

            // Highlight the new main button
            const parentBtnGroup = savedButton.closest('.btn-group');
            const mainButton = parentBtnGroup ? parentBtnGroup.querySelector('.activity-filter:not(.dropdown-item)') : savedButton;
            mainButton.classList.add('selected');
        }
    } else {
        const allButton = document.querySelector('[data-filter="all"]');
        allButton.classList.add('selected'); // Re-add 'selected' to the "All" button if no saved filter
    }

    var filterButtons = document.querySelectorAll('.activity-filter');
    filterButtons.forEach(function(button) {
        button.addEventListener('click', function(event) {
            event.preventDefault();  // Prevent the default action

            // Remove the 'selected' class from all buttons
            filterButtons.forEach(function(btn) {
                btn.classList.remove('selected');
            });

            const filter = this.getAttribute('data-filter');

            // If the clicked button is a dropdown item, swap it with the main button
            if (this.classList.contains('dropdown-item')) {
                const parentBtnGroup = this.closest('.btn-group');
                const mainButton = parentBtnGroup.querySelector('.activity-filter:not(.dropdown-item)');
                swapButtonAttributes(this, mainButton);
            }

            // Add the 'selected' class to the new main button
            const parentBtnGroup = this.closest('.btn-group');
            const mainButton = parentBtnGroup ? parentBtnGroup.querySelector('.activity-filter:not(.dropdown-item)') : this;
            mainButton.classList.add('selected');

            // Save the current filter into local storage
            localStorage.setItem('selectedFilter', filter);

            filterActivities(filter);
        });
    });
});

function findButtonToHighlight(savedFilter) {
    const allButtons = document.querySelectorAll('.activity-filter');
    let savedButton = null;

    allButtons.forEach(function(button) {
        if (button.getAttribute('data-filter') === savedFilter) {
            savedButton = button;
        }
    });

    return savedButton;
}

function swapButtonAttributes(button1, button2) {
    const tempFilter = button1.getAttribute('data-filter');
    const tempText = button1.textContent || button1.innerText;

    button1.setAttribute('data-filter', button2.getAttribute('data-filter'));
    button1.textContent = button2.textContent || button2.innerText;

    button2.setAttribute('data-filter', tempFilter);
    button2.textContent = tempText;
}

function filterActivities(filter) {
    var activities = document.querySelectorAll('.activity-item');
    activities.forEach(function(activity) {
        var activityType = activity.getAttribute('data-activity-type');
        if (filter === 'all' || activityType === filter || (filter === 'check-in' && activityType.endsWith('check-in'))) {
            activity.style.display = 'block';
        } else {
            activity.style.display = 'none';
        }
    });
}
