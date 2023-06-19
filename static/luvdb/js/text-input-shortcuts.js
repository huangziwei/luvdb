document.getElementById('text-input').addEventListener('keydown', function(e) {
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

    // Add new shortcut for submitting form with Ctrl+Enter (or Command+Enter on Mac)
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
});