(function () {
  "use strict";

  var dataUrl = "data/bsc-nursing-allotments-2026-27.json";
  var pageSizeOptions = [25, 50, 100];
  var records = [];
  var recordsByCollege = new Map();
  var colleges = [];
  var state = {
    selectedCollege: "",
    collegeSearch: "",
    collegeOrder: "alphabetical",
    candidateSearch: "",
    minScore: "",
    maxScore: "",
    page: 1,
    pageSize: pageSizeOptions[0]
  };

  var elements = {
    loadMessage: document.getElementById("load-message"),
    layout: document.querySelector(".allotment-layout"),
    datasetSummary: document.getElementById("dataset-summary"),
    collegeSearch: document.getElementById("college-search"),
    collegeOrder: document.getElementById("college-order"),
    collegeCount: document.getElementById("college-count"),
    collegeList: document.getElementById("college-list"),
    selectedCollege: document.getElementById("selected-college"),
    selectedTotal: document.getElementById("selected-total"),
    statTotal: document.getElementById("stat-total"),
    statMin: document.getElementById("stat-min"),
    statMax: document.getElementById("stat-max"),
    candidateSearch: document.getElementById("candidate-search"),
    minScore: document.getElementById("min-score"),
    maxScore: document.getElementById("max-score"),
    resetFilters: document.getElementById("reset-filters"),
    pageSize: document.getElementById("page-size"),
    resultsSummary: document.getElementById("results-summary"),
    candidateRows: document.getElementById("candidate-rows"),
    candidateCards: document.getElementById("candidate-cards"),
    emptyResults: document.getElementById("empty-results"),
    pageStatus: document.getElementById("page-status"),
    previousPage: document.getElementById("previous-page"),
    nextPage: document.getElementById("next-page")
  };

  function escapeHtml(value) {
    return String(value == null ? "" : value).replace(/[&<>"']/g, function (character) {
      return {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
      }[character];
    });
  }

  function formatPercent(value) {
    var number = Number(value);
    return (Number.isInteger(number) ? String(number) : String(number).replace(/(\.\d*?)0+$/, "$1").replace(/\.$/, "")) + "%";
  }

  function getFilteredRecords(selectedRecords) {
    var term = state.candidateSearch.trim().toLocaleLowerCase("en-IN");
    var minimum = state.minScore === "" ? Number.NEGATIVE_INFINITY : Number(state.minScore);
    var maximum = state.maxScore === "" ? Number.POSITIVE_INFINITY : Number(state.maxScore);

    return selectedRecords.filter(function (record) {
      var matchesCandidate = !term ||
        record.candidateName.toLocaleLowerCase("en-IN").includes(term) ||
        record.rollNo.toLocaleLowerCase("en-IN").includes(term);
      return matchesCandidate && record.cetScore >= minimum && record.cetScore <= maximum;
    }).sort(function (a, b) {
      return a.serialNo - b.serialNo;
    });
  }

  function renderCollegeList() {
    var term = state.collegeSearch.trim().toLocaleLowerCase("en-IN");
    var visible = colleges.filter(function (college) {
      return !term || college.name.toLocaleLowerCase("en-IN").includes(term);
    }).sort(function (a, b) {
      if (state.collegeOrder === "high-score-total") {
        return b.rankingTotal - a.rankingTotal ||
          b.highScoreCount - a.highScoreCount ||
          a.name.localeCompare(b.name, "en");
      }
      return a.name.localeCompare(b.name, "en");
    });

    elements.collegeCount.textContent = state.collegeOrder === "high-score-total"
      ? colleges.length + " colleges · >140 totals with top-5 fallback"
      : colleges.length + " colleges · alphabetical order";
    if (!visible.length) {
      elements.collegeList.innerHTML = '<div class="empty-state"><strong>No college found</strong><p>Try a shorter name or clear the search.</p></div>';
      return;
    }

    elements.collegeList.innerHTML = visible.map(function (college) {
      var metrics = state.collegeOrder === "high-score-total"
        ? (college.usesTopFiveFallback
          ? '<span class="college-metrics"><span class="college-count">Top 5 marks</span><span class="college-score-total">' +
            college.topFiveTotal.toLocaleString() + ' total</span></span>'
          : '<span class="college-metrics"><span class="college-count">' + college.highScoreCount.toLocaleString() +
            ' above 140</span><span class="college-score-total">' + college.highScoreTotal.toLocaleString() + ' total</span></span>')
        : '<span class="college-metrics"><span class="college-count">' + college.count.toLocaleString() + "</span></span>";
      return '<button class="college-option" type="button" role="option" data-college="' +
        escapeHtml(college.name) + '" aria-selected="' + String(college.name === state.selectedCollege) + '">' +
        '<span class="college-option-name">' + escapeHtml(college.name) + '</span>' +
        metrics + '</button>';
    }).join("");
  }

  function renderRecordRow(record) {
    return "<tr>" +
      '<td class="serial-cell">' + escapeHtml(record.serialNo) + "</td>" +
      "<td><span class=\"candidate-name\">" + escapeHtml(record.candidateName) + "</span>" +
        '<span class="candidate-sub">Roll no. ' + escapeHtml(record.rollNo) + "</span></td>" +
      '<td class="candidate-score">' + escapeHtml(record.cetScore) + "</td>" +
      "<td>" + escapeHtml(formatPercent(record.qualifyingPercent)) + "</td>" +
      "<td>" + escapeHtml(record.dateOfBirth) + "</td>" +
      '<td><span class="category-tag">' + escapeHtml(record.category) + "</span></td>" +
      "<td>" + escapeHtml(record.course) + "</td>" +
      '<td class="remark-cell">' + escapeHtml(record.remark) + "</td>" +
      "</tr>";
  }

  function renderRecordCard(record) {
    return '<article class="record-card">' +
      '<div class="record-top"><div><span class="candidate-name">' + escapeHtml(record.candidateName) + "</span>" +
      '<span class="candidate-sub">Sr. No. ' + escapeHtml(record.serialNo) + " · Roll no. " + escapeHtml(record.rollNo) + "</span></div>" +
      '<span class="record-score">CET ' + escapeHtml(record.cetScore) + "</span></div>" +
      '<dl class="record-meta">' +
      "<div><dt>Qualifying %</dt><dd>" + escapeHtml(formatPercent(record.qualifyingPercent)) + "</dd></div>" +
      "<div><dt>Date of birth</dt><dd>" + escapeHtml(record.dateOfBirth) + "</dd></div>" +
      '<div><dt>Category</dt><dd><span class="category-tag">' + escapeHtml(record.category) + "</span></dd></div>" +
      "<div><dt>Course</dt><dd>" + escapeHtml(record.course) + "</dd></div>" +
      "<div><dt>Remark / status</dt><dd>" + escapeHtml(record.remark) + "</dd></div>" +
      "</dl></article>";
  }

  function renderCandidates() {
    var selectedRecords = recordsByCollege.get(state.selectedCollege) || [];
    var filtered = getFilteredRecords(selectedRecords);
    var pageCount = Math.max(1, Math.ceil(filtered.length / state.pageSize));
    state.page = Math.min(state.page, pageCount);
    var start = (state.page - 1) * state.pageSize;
    var pageRecords = filtered.slice(start, start + state.pageSize);
    var firstShown = filtered.length ? start + 1 : 0;
    var lastShown = Math.min(start + state.pageSize, filtered.length);
    var scores = selectedRecords.map(function (record) { return record.cetScore; });

    elements.selectedCollege.textContent = state.selectedCollege || "No college selected";
    elements.selectedTotal.textContent = selectedRecords.length.toLocaleString();
    elements.statTotal.textContent = selectedRecords.length.toLocaleString();
    elements.statMin.textContent = scores.length ? String(Math.min.apply(Math, scores)) : "—";
    elements.statMax.textContent = scores.length ? String(Math.max.apply(Math, scores)) : "—";
    elements.resultsSummary.innerHTML = "Showing <strong>" + firstShown.toLocaleString() + "–" + lastShown.toLocaleString() +
      "</strong> of <strong>" + filtered.length.toLocaleString() + "</strong> matching candidates";
    elements.pageStatus.textContent = "Page " + state.page + " of " + pageCount;
    elements.previousPage.disabled = state.page <= 1;
    elements.nextPage.disabled = state.page >= pageCount;
    elements.candidateRows.innerHTML = pageRecords.map(renderRecordRow).join("");
    elements.candidateCards.innerHTML = pageRecords.map(renderRecordCard).join("");
    elements.emptyResults.hidden = pageRecords.length > 0;
    elements.candidateRows.closest(".desktop-records").hidden = pageRecords.length === 0;
    elements.candidateCards.hidden = pageRecords.length === 0;
  }

  function render() {
    renderCollegeList();
    renderCandidates();
  }

  function resetPage() {
    state.page = 1;
    renderCandidates();
  }

  function initialize(data) {
    records = Array.isArray(data.records) ? data.records : [];
    if (!records.length) throw new Error("The source file contains no candidate records.");

    records.forEach(function (record) {
      if (!recordsByCollege.has(record.college)) recordsByCollege.set(record.college, []);
      recordsByCollege.get(record.college).push(record);
    });
    recordsByCollege.forEach(function (collegeRecords) {
      collegeRecords.sort(function (a, b) { return a.serialNo - b.serialNo; });
    });
    colleges = Array.from(recordsByCollege.entries()).map(function (entry) {
      var highScoreRecords = entry[1].filter(function (record) { return record.cetScore > 140; });
      var topFiveScores = entry[1].map(function (record) { return record.cetScore; })
        .sort(function (a, b) { return b - a; })
        .slice(0, 5);
      var highScoreTotal = highScoreRecords.reduce(function (total, record) {
        return total + record.cetScore;
      }, 0);
      var topFiveTotal = topFiveScores.reduce(function (total, score) {
        return total + score;
      }, 0);
      return {
        name: entry[0],
        count: entry[1].length,
        highScoreCount: highScoreRecords.length,
        highScoreTotal: highScoreTotal,
        topFiveTotal: topFiveTotal,
        usesTopFiveFallback: highScoreRecords.length === 0,
        rankingTotal: highScoreRecords.length ? highScoreTotal : topFiveTotal
      };
    }).sort(function (a, b) {
      return a.name.localeCompare(b.name, "en");
    });

    state.selectedCollege = records[0].college;
    elements.datasetSummary.textContent = records.length.toLocaleString() + " candidate records across " +
      colleges.length + " colleges · CET scores " +
      Math.min.apply(Math, records.map(function (record) { return record.cetScore; })) + "–" +
      Math.max.apply(Math, records.map(function (record) { return record.cetScore; })) +
      " · List dated 24 September 2026";
    elements.layout.hidden = false;
    elements.loadMessage.hidden = true;
    render();
  }

  elements.collegeSearch.addEventListener("input", function () {
    state.collegeSearch = elements.collegeSearch.value;
    renderCollegeList();
  });
  elements.collegeOrder.addEventListener("change", function () {
    state.collegeOrder = elements.collegeOrder.value;
    renderCollegeList();
  });

  elements.collegeList.addEventListener("click", function (event) {
    var option = event.target.closest("[data-college]");
    if (!option) return;
    state.selectedCollege = option.getAttribute("data-college");
    state.page = 1;
    render();
  });

  elements.candidateSearch.addEventListener("input", function () {
    state.candidateSearch = elements.candidateSearch.value;
    resetPage();
  });
  elements.minScore.addEventListener("input", function () {
    state.minScore = elements.minScore.value;
    resetPage();
  });
  elements.maxScore.addEventListener("input", function () {
    state.maxScore = elements.maxScore.value;
    resetPage();
  });
  elements.resetFilters.addEventListener("click", function () {
    state.collegeSearch = "";
    state.candidateSearch = "";
    state.minScore = "";
    state.maxScore = "";
    state.pageSize = pageSizeOptions[0];
    state.page = 1;
    elements.collegeSearch.value = "";
    elements.candidateSearch.value = "";
    elements.minScore.value = "";
    elements.maxScore.value = "";
    elements.pageSize.value = String(state.pageSize);
    render();
  });
  elements.pageSize.addEventListener("change", function () {
    state.pageSize = Number(elements.pageSize.value);
    resetPage();
  });
  elements.previousPage.addEventListener("click", function () {
    state.page = Math.max(1, state.page - 1);
    renderCandidates();
  });
  elements.nextPage.addEventListener("click", function () {
    state.page += 1;
    renderCandidates();
  });

  fetch(dataUrl).then(function (response) {
    if (!response.ok) throw new Error("The allotment data could not be loaded (HTTP " + response.status + ").");
    return response.json();
  }).then(initialize).catch(function (error) {
    elements.loadMessage.classList.add("error");
    elements.loadMessage.textContent = error.message || "The allotment data could not be loaded.";
  });
})();