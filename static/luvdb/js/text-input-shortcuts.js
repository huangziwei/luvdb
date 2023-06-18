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
});