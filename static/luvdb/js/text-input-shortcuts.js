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

    // first diable browser back navigation with Ctrl+Z (or Command+Z on Mac) in the text-input field
    // then add undo delete with Ctrl+Z (or Command+Z on Mac) in the text-input field
    if ((e.ctrlKey || e.metaKey) && (e.key == 'z' || e.code == 'KeyZ')) {
        e.preventDefault();
        if (e.shiftKey) {
            document.execCommand('redo', false);
        } else {
            document.execCommand('undo', false);
        }
    }

    // add redo delete with Ctrl+Shift+Z (or Command+Shift+Z on Mac) in the text-input field
    if ((e.ctrlKey || e.metaKey) && (e.shiftKey) && (e.key == 'z' || e.code == 'KeyZ')) {
        e.preventDefault();
        document.execCommand('redo', false);
    }

});