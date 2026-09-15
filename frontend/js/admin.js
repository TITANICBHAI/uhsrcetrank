(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const secret = () => sessionStorage.getItem("admin_secret") || "";
  const message = (text, error) => {
    const node = $("admin-message");
    if (!node) return;
    node.hidden = !text; node.textContent = text; node.className = "inline-message" + (error ? " error" : "");
  };
  async function adminFetch(path, options) {
    const headers = Object.assign({}, options && options.headers, { "X-Admin-Secret": secret() });
    const response = await fetch(CONFIG.apiBase + path, Object.assign({}, options, { headers }));
    if (response.status === 401) {
      sessionStorage.removeItem("admin_secret");
      message("Authentication failed. Enter the admin secret again.", true);
    }
    return response;
  }
  async function loadDatasets() {
    const response = await adminFetch("/admin/datasets");
    if (!response.ok) return;
    const datasets = await response.json();
    const body = $("datasets-body");
    body.innerHTML = "";
    datasets.forEach((dataset) => {
      const row = document.createElement("tr");
      row.innerHTML = "<td>" + dataset.id + "</td><td>" + dataset.cet_exam + "</td><td>" + dataset.version + "</td><td>" + dataset.candidate_count + "</td><td>" + (dataset.is_published ? "Published" : "Unpublished") + "</td><td><div class=\"admin-actions\"><button data-validation=\"" + dataset.id + "\">View validation</button>" + (dataset.is_published ? "<button data-unpublish=\"" + dataset.id + "\">Unpublish</button>" : "<button data-publish=\"" + dataset.id + "\">Publish</button><button data-delete=\"" + dataset.id + "\">Delete</button>") + "</div></td>";
      body.appendChild(row);
    });
  }
  document.addEventListener("click", async (event) => {
    const target = event.target;
    if (target.dataset.validation) {
      const response = await adminFetch("/admin/datasets/" + target.dataset.validation + "/validation");
      $("validation-output").textContent = JSON.stringify(await response.json(), null, 2);
    }
    for (const action of ["publish", "unpublish", "delete"]) {
      if (target.dataset[action]) {
        const method = action === "delete" ? "DELETE" : "POST";
        const response = await adminFetch("/admin/datasets/" + target.dataset[action] + (action === "publish" ? "/publish" : action === "unpublish" ? "/unpublish" : ""), { method });
        if (!response.ok) message("That action could not be completed.", true);
        await loadDatasets();
      }
    }
  });
  document.addEventListener("DOMContentLoaded", () => {
    if (!$("admin-form")) return;
    $("admin-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      sessionStorage.setItem("admin_secret", $("admin-secret").value);
      const form = new FormData(event.target);
      const response = await adminFetch("/admin/datasets/import", { method: "POST", body: form });
      if (response.ok) { message("Dataset imported as unpublished. Review validation before publishing."); event.target.reset(); await loadDatasets(); }
      else message("Import failed. Review the file and credentials.", true);
    });
    loadDatasets();
  });
})();