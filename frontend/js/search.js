(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const examLabel = (value) => {
    const exam = CONFIG.cetExams.find((item) => item.value === value);
    return exam ? exam.label : value;
  };
  const showMessage = (message, type) => {
    const target = $("form-message");
    if (!target) return;
    target.textContent = message;
    target.className = "inline-message" + (type ? " " + type : "");
    target.hidden = !message;
  };
  const setUnavailable = (unavailable) => {
    const form = $("search-form");
    if (!form) return;
    ["cet_exam", "roll_no", "search-button"].forEach((id) => { if ($(id)) $(id).disabled = unavailable; });
    if (unavailable) {
      showMessage("Result data for all CET examinations has not been processed and published yet.", "");
    } else {
      showMessage("", "");
    }
  };

  async function loadActiveDatasets() {
    const select = $("cet_exam");
    if (!select) return [];
    select.innerHTML = '<option value="">Select an examination</option>';
    CONFIG.cetExams.forEach((exam) => {
      const option = document.createElement("option");
      option.value = exam.value;
      option.textContent = exam.label + " — data not available";
      option.disabled = true;
      select.appendChild(option);
    });
    try {
      const response = await fetch(CONFIG.apiBase + "/api/datasets/active");
      if (!response.ok) throw new Error("active datasets request failed");
      const active = await response.json();
      active.forEach((dataset) => {
        const option = Array.from(select.options).find((item) => item.value === dataset.cet_exam);
        if (option) {
          option.disabled = false;
          option.textContent = examLabel(dataset.cet_exam) + " — " + dataset.academic_year;
        }
      });
      const hasActive = active.length > 0;
      setUnavailable(!hasActive);
      return active;
    } catch (error) {
      setUnavailable(true);
      showMessage("Unable to connect right now. Check your connection and try again.", "error");
      return [];
    }
  }

  async function submitSearch(event) {
    event.preventDefault();
    const roll = $("roll_no").value.trim().toUpperCase();
    const exam = $("cet_exam").value;
    if (!/^[A-Z0-9-]{1,40}$/.test(roll) || !exam) {
      showMessage("Please enter a valid Roll Number and select an examination.", "error");
      return;
    }
    const button = $("search-button");
    button.disabled = true;
    button.textContent = "Searching…";
    showMessage("Searching…", "");
    try {
      const url = CONFIG.apiBase + "/api/search?roll_no=" + encodeURIComponent(roll) + "&cet_exam=" + encodeURIComponent(exam);
      const response = await fetch(url);
      const result = await response.json();
      if (result.status === "found") {
        sessionStorage.setItem("uhsr-search-" + roll + "-" + exam, JSON.stringify(result));
      }
      window.location.href = "result.html?roll_no=" + encodeURIComponent(roll) + "&cet_exam=" + encodeURIComponent(exam);
    } catch (error) {
      showMessage("Unable to connect right now. Check your connection and try again.", "error");
      button.disabled = false;
      button.textContent = "Search";
    }
  }

  function initHome() {
    if (!$("search-form")) return;
    loadActiveDatasets();
    $("search-form").addEventListener("submit", submitSearch);
  }

  function setText(id, value) { if ($(id)) $(id).textContent = value ?? "Not published"; }
  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[char]));
  }
  function renderResult(result, roll, exam) {
    const status = result.status;
    const message = $("result-message");
    if (status !== "found" || !result.data) {
      message.hidden = false;
      message.className = "inline-message " + (status === "error" ? "error" : "");
      message.textContent = result.message || (status === "not_found"
        ? "No candidate was found with this Roll Number in the selected CET 2026 dataset. Check the Roll Number and selected examination."
        : "Result data for this CET examination has not been processed and published yet.");
      $("result-content").hidden = true;
      return;
    }
    const data = result.data;
    const candidate = data.candidate || {};
    $("result-content").hidden = false;
    message.hidden = true;
    setText("result-exam", examLabel(exam));
    setText("result-roll", candidate.roll_number || roll);
    setText("result-name", candidate.name || "Not published");
    setText("result-score", candidate.cet_score ?? "Not published");
    setText("result-percentile", candidate.percentile ?? "Not published");
    setText("result-dob", candidate.dob || "Not published");
    setText("result-category", candidate.category || "Not published");
    setText("result-cet", examLabel(candidate.cet_exam || exam));
    setText("merit-position", data.merit_position);
    setText("total-candidates", data.total_candidates);
    setText("candidates-ahead", data.candidates_ahead);
    setText("dataset-version", data.dataset_version);
    setText("ranking-method", data.ranking_method || "See methodology");
    setText("calculated-at", data.calculated_at || "At lookup time");
    const disclaimer = $("ranking-disclaimer");
    if (data.ranking_disclaimer) {
      disclaimer.hidden = false;
      disclaimer.querySelector("p").textContent = data.ranking_disclaimer;
    }
    const criteria = $("criteria-list");
    if (criteria) {
      criteria.innerHTML = "";
      (data.criteria || ["Published source order or configured criteria"]).forEach((item) => {
        const li = document.createElement("li");
        li.textContent = item;
        criteria.appendChild(li);
      });
    }
    const report = $("generate-report");
    if (report) {
      report.addEventListener("click", async () => {
        report.disabled = true;
        report.textContent = "Generating…";
        try {
          const response = await fetch(CONFIG.apiBase + "/api/report?roll_no=" + encodeURIComponent(roll) + "&cet_exam=" + encodeURIComponent(exam));
          if (!response.ok) throw new Error("report failed");
          const blob = await response.blob();
          const url = URL.createObjectURL(blob);
          window.open(url, "_blank", "noopener");
          setTimeout(() => URL.revokeObjectURL(url), 10000);
        } catch (error) {
          message.hidden = false;
          message.className = "inline-message error";
          message.textContent = "The report could not be generated right now. Try again later.";
        } finally {
          report.disabled = false;
          report.textContent = "Generate My Rank Report";
        }
      }, { once: true });
    }
  }

  async function initResult() {
    if (!$("result-content")) return;
    const params = new URLSearchParams(window.location.search);
    const roll = (params.get("roll_no") || "").trim().toUpperCase();
    const exam = params.get("cet_exam") || "";
    let result;
    try { result = JSON.parse(sessionStorage.getItem("uhsr-search-" + roll + "-" + exam) || "null"); } catch (_) { result = null; }
    if (!result) {
      try {
        const response = await fetch(CONFIG.apiBase + "/api/search?roll_no=" + encodeURIComponent(roll) + "&cet_exam=" + encodeURIComponent(exam));
        result = await response.json();
      } catch (_) {
        result = { status: "error", message: "Unable to connect right now. Check your connection and try again." };
      }
    }
    renderResult(result || { status: "invalid" }, roll, exam);
  }

  document.addEventListener("DOMContentLoaded", () => { initHome(); initResult(); });
})();