
function setMode(mode) {
    const modeInput = document.getElementById('modeInput');
    const form = document.getElementById('genForm');
    if (modeInput.value !== mode) {
        modeInput.value = mode;
        if (form) {
            form.submit();
        }
    }
}
function copyPassword() {
    const input = document.getElementById("generatedPassword");
    if (!input) return;
    input.select();
    input.setSelectionRange(0, 99999);
    document.execCommand("copy");
    window.getSelection().removeAllRanges();
    input.blur();
    const msg = document.getElementById("copyMsg");
    if (msg) {
        msg.classList.add("show");
        setTimeout(() => msg.classList.remove("show"), 1200);
    }
}
document.addEventListener("DOMContentLoaded", function() {
    const passwordInput = document.getElementById("generatedPassword");
    const timerBar = document.getElementById("timerBar");
    const expiryNote = document.getElementById("expiryNote");

    if (passwordInput && timerBar) {
        let timeLeft = 5; // Seconds before clearing
        const totalTime = 30;

        const countdown = setInterval(() => {
            timeLeft--;

            // Update the bar width percentage
            const widthPercent = (timeLeft / totalTime) * 100;
            timerBar.style.width = widthPercent + "%";

            // Change color to red when running low (last 5 seconds)
            if (timeLeft <= 5) {
                timerBar.style.backgroundColor = "#ff4d4d";
            }

            if (timeLeft <= 0) {
                clearInterval(countdown);
                passwordInput.value = "* * * *"; // Clear the text
                passwordInput.style.color = "#ccc";
                passwordInput.style.font = "'Courier New', monospace";
                expiryNote.style.display = "block"; // Show "Expired" note

                // Optional: Disable the copy button
               // document.querySelector(".copy-icon").style.pointerEvents = "none";
                document.querySelector(".copy-icon").style.display = "none";
                document.querySelector(".copy-icon").style.opacity = "0.3";
            }
        }, 1000);
    }
});