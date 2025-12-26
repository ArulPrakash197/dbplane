async function loadparams() {
  res = await fetch("https://bhjjuemrkslhazblfxpe.supabase.co/rest/v1/facts", {
    headers: {
      apikey:
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJoamp1ZW1ya3NsaGF6YmxmeHBlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Mzk3MDA2NDYsImV4cCI6MjA1NTI3NjY0Nn0.J4TEhdwhN-oxtQQrc0lJZ6d7DG8fC2l0gwXw21AKVy0",
      authorization:
        " Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJoamp1ZW1ya3NsaGF6YmxmeHBlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Mzk3MDA2NDYsImV4cCI6MjA1NTI3NjY0Nn0.J4TEhdwhN-oxtQQrc0lJZ6d7DG8fC2l0gwXw21AKVy0",
    },
  });
  //console.log(res);
  data = await res.json();
  createFactlist(data);
}
loadparams();
let btn = document.querySelector(".share");
let forms = document.querySelector(".fact-form");
let formlist = document.querySelector(".fact-list");
formlist.innerHTML = "";
function createFactlist(dataArray) {
  //adding facts
  const htmlattr = dataArray.map(
    (fact) => `<li class="fact">
                  <p>${fact.text}</p>
                  <a class="source" href=${fact.source} target="_blank">More Info</a>
                  <span class="tag">${fact.category}</span></li>`
  );
  const html = htmlattr.join("");
  formlist.insertAdjacentHTML("afterbegin", html);
}
//addingcategory

//sharebutton
btn.addEventListener("click", function () {
  if (forms.classList.contains("fact-form")) {
    forms.classList.remove("fact-form");
    btn.textContent = "Close";
  } else {
    forms.classList.add("fact-form");
    btn.textContent = "Share";
  }
});

//console.dir(formlist);
const result = [1, 2, 3, 5].filter((el) => el > 1);
console.log(result);
