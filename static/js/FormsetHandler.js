function initFormset(formsetId, formsetContainerId) {
    let formIndex = $(`#${formsetContainerId} .form-wrapper`).length;
    let originalForm = $(`#${formsetContainerId} .form-wrapper:last`).clone();
    let totalFormsId = `id_${formsetContainerId}-TOTAL_FORMS`;
    let totalForms = $(`#${totalFormsId}`); // Selects the specific TOTAL_FORMS input for this formset

    $(`#${formsetId}`).click(function () {
        let newForm = originalForm.clone();

        newForm.find("input, select, textarea, label, div").each(function () {
            updateElementIndex(this, formIndex);
        });

        newForm.find('input[type="text"], textarea').val("");
        newForm.find("select").prop("selectedIndex", 0);

        newForm.find('input[type="file"]').val("");
        newForm.find(".existing-cover img").remove();

        $(`#${formsetContainerId}`).append(newForm);
        totalForms.val(parseInt(totalForms.val()) + 1);
        formIndex++;
    });
}

function updateElementIndex(element, index) {
    let idRegex = new RegExp("-(\\d+)-");
    let replacement = "-" + index + "-";

    if (element.id) {
        element.id = element.id.replace(idRegex, replacement);
    }
    if (element.name) {
        element.name = element.name.replace(idRegex, replacement);
    }
    if (element.htmlFor) {
        element.htmlFor = element.htmlFor.replace(idRegex, replacement);
    }
}
