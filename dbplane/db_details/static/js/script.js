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
    if (el.title === "Show Mongo String") {
      el.title = "Hide Mongo String";
    } else if (el.title === "Show password") {
      el.title = "Hide password";
    }
  } else {
    input.type = "password";
    svg.innerHTML = iconOpen;
    if (el.title === "Hide Mongo String") {
      el.title = "Show Mongo String";
    } else if (el.title === "Hide password") {
      el.title = "Show password";
    }
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

  let lastQueryResult = null;
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

  // Persistent History
  let commandHistory = JSON.parse(localStorage.getItem("dbTerminalHistory")) || [];
  let historyIndex = commandHistory.length;
  let cachedTables = [];

  function saveHistory() {
    localStorage.setItem("dbTerminalHistory", JSON.stringify(commandHistory));
  }

  commandInput.focus();

  appendOutput("Connected successfully.");
  appendOutput(promptText);

  // Preload tables once (for autocomplete)
  preloadTables();

  // Auto-expand textarea
  commandInput.addEventListener("input", function () {
    this.style.height = "auto";
    this.style.height = this.scrollHeight + "px";
  });

  commandInput.addEventListener("keydown", function (e) {
    // Execute on Enter (Shift+Enter = new line)
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      executeCommand();
    }
    // History Up
    if (e.key === "ArrowUp") {
      if (historyIndex > 0) {
        historyIndex--;
        commandInput.value = commandHistory[historyIndex];
      }
      e.preventDefault();
    }
    // History Down
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
    // Autocomplete
    if (e.key === "Tab") {
      e.preventDefault();
      handleAutocomplete();
    }
  });

  // --------------------------------------------------
  // PRELOAD TABLES
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
    saveHistory();

    appendOutput(`%c${promptText}`, cmd);

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

    if (!cmd.endsWith(";") && !cmd.startsWith("\\")) {
      appendOutput("⚠️ Query should end with semicolon ;");
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
    const endTime = performance.now();
    const duration = ((endTime - startTime) / 1000).toFixed(3);

    if (data.output && typeof data.output === "object") {
    // 🔴 Backend returned error
    if (data.output.error) {
      appendOutput("ERROR: " + data.output.error);
    }
    // 🟢 Select query result
    else if (data.output.columns && data.output.rows) {
      lastQueryResult = data.output;
      appendTable(data.output);
      // Show row count
      if (data.output.rows.length > 0) {
        appendOutput(`(${data.output.rows.length} rows)`);
      }
    }
    // 🟡 Non-select success
    else if (data.output.message) {
      appendOutput(data.output.message);
    }
  } else {
    appendOutput(data.output);
  }
  }


  // --------------------------------------------------
  // OUTPUT HELPERS
  // --------------------------------------------------
  function appendOutput(text, command = null) {
    const line = document.createElement("div");
    if (command !== null) {
      line.innerHTML =
        `<span style="color:#00ff00">${text}</span> ${highlightSQL(command)}`;
    } else {
      line.innerHTML = highlightSQL(text);
    }

    outputDiv.appendChild(line);
    outputDiv.scrollTop = outputDiv.scrollHeight;
  }

  function highlightSQL(text) {
    const keywords = [
      "SELECT","INSERT","UPDATE","DELETE",
      "CREATE","DROP","FROM","WHERE",
      "TABLE","VALUES","INTO","SET",
      "ALTER","JOIN","LEFT","RIGHT",
      "INNER","OUTER","GROUP","BY","ORDER"
    ];

    let result = text;

    keywords.forEach(word => {
      const regex = new RegExp("\\b" + word + "\\b", "gi");
      result = result.replace(regex,
        `<span style="color:#00ffff;font-weight:bold">${word}</span>`
      );
    });

    return result;
  }

  function appendTable(result) {
    if (!result.columns || !result.rows) {
      appendOutput(JSON.stringify(result, null, 2));
      return;
    }

    const columns = result.columns
    const rows = result.rows

    const colWidths = columns.map((col, i) => {
    let max = col.length;
    rows.forEach(row => {
      max = Math.max(max, String(row[i]).length);
    });
    return max;
    });

    function formatRow(row) {
      return row.map((cell, i) =>
        String(cell).padEnd(colWidths[i])
      ).join(" | ");
    }

    const header = formatRow(columns);
    const separator = colWidths.map(w => "-".repeat(w)).join("-+-");
    const body = rows.map(row => formatRow(row)).join("\n");

    const tableBlock = document.createElement("pre");
    tableBlock.textContent = header + "\n" + separator + "\n" + body;

    outputDiv.appendChild(tableBlock);
    outputDiv.scrollTop = outputDiv.scrollHeight;
  }
});

window.showToast = function (message, type = 'success') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.textContent = message;

  container.appendChild(toast);

  setTimeout(() => {
    toast.remove();
  }, 3500);
};