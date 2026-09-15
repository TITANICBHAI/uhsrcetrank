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
  const staticData = window.UHSR_STATIC_DATA || null;
  const staticIndex = staticData
    ? new Map(staticData.candidates.map((candidate) => [candidate.r, candidate]))
    : null;
  const staticRanked = staticData
    ? staticData.candidates.slice().sort((left, right) => {
      return left.m - right.m || left.r.localeCompare(right.r);
    })
    : [];
  const staticExamAvailable = (exam) => Boolean(
    staticData && staticData.available_exams.includes(exam)
  );
  const staticDisplayName = () => staticData?.dataset.display_name || "Combined UG Result";
  const staticRankingMethod = () => "Percentage descending, marks descending, younger DOB first; exact ties share competition positions.";
  const staticCandidate = (row, exam, own) => ({
    roll_number: row.r,
    name: own ? row.n : abbreviatedName(row.n),
    cet_score: row.s,
    percentile: row.p,
    dob: own ? row.d : undefined,
    category: own ? (row.g || null) : undefined,
    cet_exam: exam,
  });
  const staticResult = (roll, exam) => {
    if (!staticExamAvailable(exam)) {
      return {
        status: "unavailable",
        message: "Static data is available only for the combined UG result: B.Sc Nursing, BPT, and Paramedical.",
      };
    }
    const row = staticIndex.get(roll);
    if (!row) {
      return {
        status: "not_found",
        message: "No candidate was found with this Roll Number in the combined UG result.",
      };
    }
    const position = row.m;
    return {
      status: "found",
      data: {
        candidate: staticCandidate(row, exam, true),
        merit_position: position,
        total_candidates: staticData.dataset.candidate_count,
        candidates_ahead: position - 1,
        dataset_version: staticData.dataset.version,
        ranking_mode: staticData.dataset.ranking_mode,
        ranking_method: staticRankingMethod(),
        calculated_at: "Static GitHub Pages dataset",
        criteria: [
          "Source Percentage descending",
          "Marks descending",
          "Younger date of birth first",
          "Exact ties share competition positions",
        ],
        ranking_disclaimer: staticData.dataset.ranking_disclaimer,
      },
    };
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
    if (staticData) {
      const active = staticData.available_exams.map((cetExam) => ({
        cet_exam: cetExam,
        academic_year: staticData.dataset.academic_year,
      }));
      active.forEach((dataset) => {
        const option = Array.from(select.options).find((item) => item.value === dataset.cet_exam);
        if (option) {
          option.disabled = false;
          option.textContent = examLabel(dataset.cet_exam) + " — " + dataset.academic_year;
        }
      });
      select.value = staticExamAvailable("bsc-nursing")
        ? "bsc-nursing"
        : (active[0]?.cet_exam || "");
      setUnavailable(false);
      return active;
    }
    try {
      const response = await fetch(CONFIG.apiBase + "/api/datasets/active");
      if (response.status === 404) {
        setUnavailable(true);
        return [];
      }
      if (!response.ok) throw new Error("active datasets request failed");
      const active = await response.json();
      active.forEach((dataset) => {
        const option = Array.from(select.options).find((item) => item.value === dataset.cet_exam);
        if (option) {
          option.disabled = false;
          option.textContent = examLabel(dataset.cet_exam) + " — " + dataset.academic_year;
        }
      });
      select.value = active.some((dataset) => dataset.cet_exam === "bsc-nursing")
        ? "bsc-nursing"
        : (active[0]?.cet_exam || "");
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
      if (staticData) {
        const result = staticResult(roll, exam);
        if (result.status === "found") {
          sessionStorage.setItem("uhsr-search-" + roll + "-" + exam, JSON.stringify(result));
        }
        window.location.href = "result.html?roll_no=" + encodeURIComponent(roll) + "&cet_exam=" + encodeURIComponent(exam);
        return;
      }
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
    setText("ranking-mode", data.ranking_mode || "Stored published result");
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
    loadCandidateWindows(exam, data.merit_position);
    const report = $("generate-report");
    if (report) {
      report.addEventListener("click", () => {
        report.disabled = true;
        report.textContent = "Preparing…";
        printReport(data, exam);
        report.disabled = false;
        report.textContent = "Print / Save My Rank Report";
      }, { once: true });
    }
  }

  function displayValue(value) {
    return value === null || value === undefined || value === "" ? "Not published" : String(value);
  }
  function abbreviatedName(name) {
    if (!name) return null;
    const parts = String(name).trim().split(/\s+/);
    if (parts.length === 1) return parts[0];
    return parts[0] + " " + parts.slice(1).map((part) => part.charAt(0) + ".").join(" ");
  }

  function tableRow(item) {
    const row = document.createElement("tr");
    if (item.is_self) row.className = "nearby-self";
    [item.position, item.roll_number, item.name || "Not published", item.cet_score ?? "Not published", item.percentile ?? "Not published"]
      .forEach((value) => {
        const cell = document.createElement("td");
        cell.textContent = displayValue(value);
        row.appendChild(cell);
      });
    return row;
  }

  function renderRows(targetId, items, emptyText) {
    const body = $(targetId);
    if (!body) return;
    body.innerHTML = "";
    if (!items.length) {
      const row = document.createElement("tr");
      row.innerHTML = '<td class="empty-table" colspan="5">' + emptyText + "</td>";
      body.appendChild(row);
      return;
    }
    items.forEach((item) => body.appendChild(tableRow(item)));
  }

  async function loadCandidateWindows(exam, position) {
    if (staticData) {
      loadStaticCandidateWindows(exam, position);
      return;
    }
    const nearbyMessage = $("nearby-message");
    try {
      const nearbyResponse = await fetch(CONFIG.apiBase + "/api/candidates/nearby?cet_exam=" + encodeURIComponent(exam) + "&position=" + encodeURIComponent(position));
      const nearby = await nearbyResponse.json();
      renderRows("nearby-body", nearby.items || [], "Nearby candidate data is not available.");
      if (nearbyMessage) nearbyMessage.hidden = true;
    } catch (_) {
      renderRows("nearby-body", [], "Nearby candidate data could not be loaded.");
      if (nearbyMessage) { nearbyMessage.hidden = false; nearbyMessage.textContent = "Nearby candidates could not be loaded right now."; }
    }
    const state = { page: 1, hasMore: false };
    const loadAbove = async () => {
      const aboveMessage = $("above-message");
      try {
        const response = await fetch(CONFIG.apiBase + "/api/candidates/above?cet_exam=" + encodeURIComponent(exam) + "&position=" + encodeURIComponent(position) + "&page=" + state.page + "&limit=20");
        const result = await response.json();
        renderRows("above-body", result.items || [], "There are no candidates ahead of this position.");
        state.hasMore = Boolean(result.has_more);
        setText("above-page", "Page " + state.page);
        setText("above-summary", (result.total_above ?? 0) + " candidates are ahead of this stored position.");
        $("above-previous").disabled = state.page <= 1;
        $("above-next").disabled = !state.hasMore;
        if (aboveMessage) aboveMessage.hidden = true;
      } catch (_) {
        renderRows("above-body", [], "Candidates above could not be loaded.");
        if (aboveMessage) { aboveMessage.hidden = false; aboveMessage.textContent = "Candidates above could not be loaded right now."; }
      }
    };
    if ($("above-previous")) $("above-previous").onclick = () => { if (state.page > 1) { state.page -= 1; loadAbove(); } };
    if ($("above-next")) $("above-next").onclick = () => { if (state.hasMore) { state.page += 1; loadAbove(); } };
    loadAbove();
  }

  function staticWindowItem(row, position, roll) {
    return {
      position: row.m,
      roll_number: row.r,
      name: abbreviatedName(row.n),
      cet_score: row.s,
      percentile: row.p,
      is_self: row.r === roll && row.m === position,
    };
  }

  function loadStaticCandidateWindows(exam, position) {
    const params = new URLSearchParams(window.location.search);
    const roll = (params.get("roll_no") || "").trim().toUpperCase();
    const nearby = staticRanked
      .filter((row) => row.m >= position - 3 && row.m <= position + 3)
      .slice(0, 25)
      .map((row) => staticWindowItem(row, position, roll));
    renderRows("nearby-body", nearby, "Nearby candidate data is not available.");
    const nearbyMessage = $("nearby-message");
    if (nearbyMessage) nearbyMessage.hidden = true;

    const above = staticRanked
      .filter((row) => row.m < position)
      .sort((left, right) => right.m - left.m || right.r.localeCompare(left.r));
    const state = { page: 1 };
    const renderAbove = () => {
      const pageSize = 20;
      const start = (state.page - 1) * pageSize;
      const items = above.slice(start, start + pageSize).map((row) => staticWindowItem(row, position, roll));
      renderRows("above-body", items, "There are no candidates ahead of this position.");
      setText("above-page", "Page " + state.page);
      setText("above-summary", above.length + " candidates are ahead of this stored position.");
      $("above-previous").disabled = state.page <= 1;
      $("above-next").disabled = start + items.length >= above.length;
    };
    if ($("above-previous")) $("above-previous").onclick = () => {
      if (state.page > 1) { state.page -= 1; renderAbove(); }
    };
    if ($("above-next")) $("above-next").onclick = () => {
      if (state.page * 20 < above.length) { state.page += 1; renderAbove(); }
    };
    renderAbove();
  }

  function printReport(data, exam) {
    const candidate = data.candidate || {};
    const popup = window.open("", "_blank", "noopener,noreferrer,width=800,height=900");
    if (!popup) {
      showMessage("Your browser blocked the report window. Allow pop-ups and try again.", "error");
      return;
    }
    const rows = [
      ["CET examination", examLabel(exam)],
      ["Roll Number", candidate.roll_number],
      ["Name", candidate.name],
      ["CET score", candidate.cet_score],
      ["Percentage", candidate.percentile],
      ["Date of birth", candidate.dob],
      ["Category", candidate.category],
      ["Estimated merit position", data.merit_position],
      ["Candidates processed", data.total_candidates],
      ["Candidates ahead", data.candidates_ahead],
      ["Dataset version", data.dataset_version],
      ["Ranking method", data.ranking_method],
    ];
    popup.document.write("<!doctype html><html><head><meta charset='utf-8'><title>Unofficial Estimated Merit Position</title><style>body{font:15px Arial,sans-serif;color:#222;margin:40px;line-height:1.45}h1{color:#1a3a6e;border-bottom:2px solid #2a5298;padding-bottom:10px}.warning{border:2px solid #c0392b;color:#c0392b;padding:12px;font-weight:bold}.report-table{width:100%;border-collapse:collapse;margin:20px 0}.report-table th,.report-table td{border:1px solid #aaa;padding:9px;text-align:left}.report-table th{width:35%;background:#eef3fa}.method{border-left:4px solid #2a5298;padding:10px;background:#eef3fa}@media print{body{margin:20px}}</style></head><body>");
    popup.document.write("<h1>UHSR CET Rank Calculator 2026</h1><div class='warning'>UNOFFICIAL — ESTIMATED MERIT POSITION</div><p>Independent Candidate Utility — not affiliated with UHSR.</p><table class='report-table'>");
    rows.forEach((row) => popup.document.write("<tr><th>" + escapeHtml(row[0]) + "</th><td>" + escapeHtml(displayValue(row[1])) + "</td></tr>"));
    popup.document.write("</table><div class='method'><strong>Methodology</strong><p>This report reflects the published dataset and stored, locally processed position returned by the service. It is not an official UHSR rank or scorecard. Use the official UHSR result/scorecard for counselling and official purposes.</p></div><p>Generated in your browser from the displayed result.</p></body></html>");
    popup.document.close();
    popup.focus();
    popup.print();
  }

  async function initResult() {
    if (!$("result-content")) return;
    const params = new URLSearchParams(window.location.search);
    const roll = (params.get("roll_no") || "").trim().toUpperCase();
    const exam = params.get("cet_exam") || "";
    let result;
    try { result = JSON.parse(sessionStorage.getItem("uhsr-search-" + roll + "-" + exam) || "null"); } catch (_) { result = null; }
    if (!result) {
      if (staticData) {
        result = staticResult(roll, exam);
      } else try {
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