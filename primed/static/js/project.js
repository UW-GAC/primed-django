/* Project specific Javascript goes here. */

// Handle paste event for text inputs with maxlength.
const checkPasteLength = (e) => {
	var paste = (e.clipboardData || window.clipboardData).getData("text");
	maxlength = e.target.getAttribute("maxlength");
  if (paste.length > maxlength) {
    alert("String longer than allowed maximum length of " + maxlength + " characters:\n" + paste)
    e.preventDefault()
    e.stopPropagation()
  }
}

var textInputs = $('form').find("input[maxlength]")
// textInputs.on("paste", checkPasteLength);
for(var i = 0; i < textInputs.length; i++){
  // Console: print the clicked <p> element
  textInputs[i].addEventListener("paste", checkPasteLength);
}
