document.addEventListener('DOMContentLoaded', function() {
    var filterButtons = document.querySelectorAll('.activity-filter');
    filterButtons.forEach(function(button) {
        button.addEventListener('click', function(event) {
            event.preventDefault();  // Prevent the default action
            // Remove the 'selected' class from all buttons
            filterButtons.forEach(function(btn) {
                btn.classList.remove('selected');
            });
            // Add the 'selected' class to the clicked button
            this.classList.add('selected');

            var filter = this.getAttribute('data-filter');
            filterActivities(filter);
        });
    });
});

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
