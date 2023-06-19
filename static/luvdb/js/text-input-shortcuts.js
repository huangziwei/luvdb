document.getElementById('text-input').addEventListener('keydown', function(e) {
    // inserting four spaces with Tab
    if (e.key == 'Tab') {
        e.preventDefault();
        var start = this.selectionStart;
        var end = this.selectionEnd;

        // Insert four spaces
        this.value = this.value.substring(0, start) +
            "    " + this.value.substring(end);

        // Put cursor at right position again
        this.selectionStart = this.selectionEnd = start + 4;
    }

    // submitting form with Ctrl+Enter (or Command+Enter on Mac)
    if ((e.ctrlKey || e.metaKey) && (e.key == 'Enter' || e.code == 'Enter')) {
        e.preventDefault();

        // Find closest form and submit
        let elem = e.target;
        while (elem) {
            if (elem.tagName === 'FORM') {
                elem.submit();
                break;
            }
            elem = elem.parentElement;
        }
    }

    // Move cursor one word left or right with Ctrl+Left Arrow / Right Arrow
    if ((e.ctrlKey || e.metaKey) && (e.key == 'ArrowLeft' || e.key == 'ArrowRight')) {
        e.preventDefault();
        // Determine direction
        var direction = (e.key == 'ArrowLeft') ? -1 : 1;
        // Split input value by space
        var words = this.value.split(' ');
        // Get current cursor position
        var position = this.selectionStart;
        // Determine number of characters to the next space
        var shift = (direction == -1)
            ? this.value.slice(0, position).lastIndexOf(' ')
            : this.value.slice(position).indexOf(' ');
        // If space was found
        if (shift !== -1) {
            // Calculate new position
            var newPosition = position + direction * shift;
            // Move cursor to the new position
            this.selectionStart = this.selectionEnd = newPosition;
        }
    }
});
