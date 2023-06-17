var buttons = document.getElementsByClassName('toggle-button');

for (var i = 0; i < buttons.length; i++) {
    buttons[i].addEventListener('click', function() {
        // Hide all sections and make all buttons secondary
        for (var j = 0; j < buttons.length; j++) {
            var sectionId = buttons[j].id.replace('show-', '') + '-section';
            document.getElementById(sectionId).style.display = 'none';
            buttons[j].classList.remove('btn-primary');
            buttons[j].classList.add('btn-secondary');
        }

        // Show the clicked section and make the button primary
        var sectionId = this.id.replace('show-', '') + '-section';
        document.getElementById(sectionId).style.display = 'block';
        this.classList.remove('btn-secondary');
        this.classList.add('btn-primary');
    });
}