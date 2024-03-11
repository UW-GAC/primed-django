/* Project specific Javascript goes here. */

// Handle paste event for text inputs with maxlength.
const checkPasteLength = (e) => {
	var paste = (event.clipboardData || window.clipboardData).getData("text");
	maxlength = e.target.getAttribute("maxlength");
  if (maxlength <= paste.length) {
    alert("String longer than allowed maximum length of " + maxlength + " characters:\n" + paste)
    e.preventDefault()
    e.stopPropagation()
  }
}

var textInputs = $('form').find("input[maxlength]")
textInputs.on("paste", checkPasteLength);
