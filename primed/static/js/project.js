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


// Button to copy to the clipboard.
const copyButtonLabel = "Copy Code";

// use a class selector if available
let blocks = document.querySelectorAll("pre");

blocks.forEach((block) => {
  // only add button if browser supports Clipboard API
  if (navigator.clipboard) {
    let button = document.createElement("button");

    button.innerText = copyButtonLabel;
    block.appendChild(button);

    button.addEventListener("click", async () => {
      await copyCode(block);
    });
  }
});

async function copyCode(block) {
  let code = block.querySelector("code");
  let text = code.innerText;

  await navigator.clipboard.writeText(text);
}
