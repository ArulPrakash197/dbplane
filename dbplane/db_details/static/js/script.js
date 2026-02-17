// --------------------------------------------------
// PANEL ACTIVE SWITCH
// --------------------------------------------------
const items = document.querySelectorAll('.panel-item');
items.forEach(item => {
  item.addEventListener('click', function () {
    const currentActive = document.querySelector('.panel-item.active');
    if (currentActive) {
      currentActive.classList.remove('active');
    }
    this.classList.add('active');
  });
});


// --------------------------------------------------
// PASSWORD EYE TOGGLE
// --------------------------------------------------
const iconOpen = `<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle>`;
const iconClosed = `<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.06M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line>`;

window.togglePassword = function (el) {
  const wrapper = el.closest('div');
  if (!wrapper) return;

  const input = wrapper.querySelector('input[type="password"], input[type="text"]');
  const svg = el.querySelector('svg');

  if (!input || !svg) return;

  if (input.type === "password") {
    input.type = "text";
    svg.innerHTML = iconClosed;
  } else {
    input.type = "password";
    svg.innerHTML = iconOpen;
  }
};


// --------------------------------------------------
// DELETE MODAL
// --------------------------------------------------
const overlay = document.getElementById('modalOverlay');
const modal = document.getElementById('deleteModal');
const deleteForm = document.getElementById('deleteForm');

function openModal(deleteUrl) {
  deleteForm.action = deleteUrl;
  overlay.classList.add('makeitvisible');
  modal.classList.add('makeitvisible');
}

function closeModal() {
  overlay.classList.remove('makeitvisible');
  modal.classList.remove('makeitvisible');
}

function openDeleteModal(deleteUrl) {
  openModal(deleteUrl);
}

function confirmDelete() {
  deleteForm.submit();
}


// --------------------------------------------------
// CSRF HELPER (GLOBAL)
// --------------------------------------------------
function getCSRFToken() {
  const name = "csrftoken";
  const cookies = document.cookie.split(";");

  for (let cookie of cookies) {
    cookie = cookie.trim();
    if (cookie.startsWith(name + "=")) {
      return cookie.substring(name.length + 1);
    }
  }
  return "";
}


// --------------------------------------------------
// TERMINAL OPEN (WITH CONNECTION VALIDATION)
// --------------------------------------------------
async function openTerminal(dbType, index) {

  const response = await fetch("/db/terminal/connect/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCSRFToken()
    },
    body: JSON.stringify({
      db_type: dbType,
      index: index
    })
  });

  const data = await response.json();

  if (data.success) {
    window.open(
      `/db/${dbType}/terminal/?index=${index}`,
      "_blank",
      "width=1000,height=650,resizable=yes,scrollbars=yes"
    );
  } else {
    alert("Connection failed:\n" + data.error);
  }
}


// --------------------------------------------------
// TERMINAL LOGIC
// --------------------------------------------------
document.addEventListener("DOMContentLoaded", function () {

  const wrapper = document.getElementById("db-terminal-wrapper");
  if (!wrapper) return; // Only run on terminal page

  const outputDiv = document.getElementById("db-terminal-output");
  const commandInput = document.getElementById("db-terminal-command");
  const promptSpan = document.getElementById("db-terminal-prompt");
  const loadingDiv = document.getElementById("db-terminal-loading");

  const dbType = wrapper.getAttribute("data-db-type");
  const index = wrapper.getAttribute("data-index");

  const promptText = dbType + "=#";
  promptSpan.textContent = promptText;

  let commandHistory = [];
  let historyIndex = -1;
  let cachedTables = [];

  commandInput.focus();

  appendOutput("Connected successfully.");
  appendOutput(promptText);

  // Preload tables once (for autocomplete)
  preloadTables();

  commandInput.addEventListener("keydown", function (e) {

    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      executeCommand();
    }

    if (e.key === "ArrowUp") {
      if (historyIndex > 0) {
        historyIndex--;
        commandInput.value = commandHistory[historyIndex];
      }
      e.preventDefault();
    }

    if (e.key === "ArrowDown") {
      if (historyIndex < commandHistory.length - 1) {
        historyIndex++;
        commandInput.value = commandHistory[historyIndex];
      } else {
        commandInput.value = "";
        historyIndex = commandHistory.length;
      }
      e.preventDefault();
    }

    if (e.key === "Tab") {
      e.preventDefault();
      handleAutocomplete();
    }
  });


  // --------------------------------------------------
  // PRELOAD TABLES (ONLY ONCE)
  // --------------------------------------------------
  async function preloadTables() {
    const response = await fetch("/db/terminal/autocomplete/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCSRFToken()
      },
      body: JSON.stringify({
        db_type: dbType,
        index: index
      })
    });

    const data = await response.json();
    if (data.tables) {
      cachedTables = data.tables;
    }
  }


  // --------------------------------------------------
  // AUTOCOMPLETE
  // --------------------------------------------------
  function handleAutocomplete() {

    const input = commandInput.value;
    const words = input.split(" ");
    const lastWord = words[words.length - 1];

    const matches = cachedTables.filter(table =>
      table.startsWith(lastWord)
    );

    if (matches.length === 1) {
      words[words.length - 1] = matches[0];
      commandInput.value = words.join(" ");
    } else if (matches.length > 1) {
      appendOutput(matches.join("    "));
    }
  }


  // --------------------------------------------------
  // EXECUTE COMMAND
  // --------------------------------------------------
  async function executeCommand() {

    const cmd = commandInput.value.trim();
    if (!cmd) return;

    commandHistory.push(cmd);
    historyIndex = commandHistory.length;

    appendOutput(promptText + " " + cmd);

    if (cmd === "\\clear") {
      outputDiv.innerHTML = "";
      commandInput.value = "";
      return;
    }

    if (cmd === "\\q") {
      appendOutput("Session terminated.");
      commandInput.disabled = true;
      return;
    }

    commandInput.value = "";
    loadingDiv.style.display = "block";

    const response = await fetch("/db/terminal/execute/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCSRFToken()
      },
      body: JSON.stringify({
        db_type: dbType,
        index: index,
        command: cmd
      })
    });

    const data = await response.json();
    loadingDiv.style.display = "none";

    if (typeof data.output === "object") {
      appendTable(data.output);
    } else {
      appendOutput(data.output);
    }
  }


  // --------------------------------------------------
  // OUTPUT HELPERS
  // --------------------------------------------------
  function appendOutput(text) {
    const line = document.createElement("div");
    line.textContent = text;
    outputDiv.appendChild(line);
    outputDiv.scrollTop = outputDiv.scrollHeight;
  }

  function appendTable(result) {
    if (!result.columns || !result.rows) {
      appendOutput(JSON.stringify(result, null, 2));
      return;
    }

    let table = document.createElement("pre");

    let colLine = result.columns.join(" | ");
    let separator = "-".repeat(colLine.length);
    let rows = result.rows.map(row => row.join(" | ")).join("\n");

    table.textContent = colLine + "\n" + separator + "\n" + rows;

    outputDiv.appendChild(table);
    outputDiv.scrollTop = outputDiv.scrollHeight;
  }

});
