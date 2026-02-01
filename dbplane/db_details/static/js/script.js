const items = document.querySelectorAll('.panel-item');
  items.forEach(item => {
    item.addEventListener('click', function() {
      const currentActive = document.querySelector('.panel-item.active');
      if (currentActive) {
        currentActive.classList.remove('active');
      }
      this.classList.add('active');
    });
  });
// For Pass Eye icons
const iconOpen = `<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle>`;
const iconClosed = `<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.06M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line>`;

window.togglePassword = function() {
  const input = document.getElementById("myInput");
  const svg = document.getElementById("eye-svg");

  if (input.type === "password") {
    input.type = "text";
    svg.innerHTML = iconClosed; // Swaps to eye-with-slash
  } else {
    input.type = "password";
    svg.innerHTML = iconOpen;   // Swaps back to normal eye
  }
};
//Password Eye Icon end here

const overlay = document.getElementById('modalOverlay');
const modal = document.getElementById('deleteModal');

function openModal() {
  overlay.classList.add('makeitvisible');
  modal.classList.add('makeitvisible');
}

function closeModal() {
  overlay.classList.remove('makeitvisible');
  modal.classList.remove('makeitvisible');
}

function confirmDelete() {
    //TODO: Implement the delete logic
    console.log("Deleted")
    closeModal();
}
function openPopup(url){
window.open(url,
        "Terminal",
        "width=900,height=900,top=500,left=100,resizable=yes,scrollbars=yes"
    );

}