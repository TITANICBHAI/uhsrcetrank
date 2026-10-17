(function () {
  "use strict";

  var dataUrl = document.body.getAttribute("data-allotment-data") ||
    "data/nursing-round2-allotments-2026-27.json";
  var expectedCourse = document.body.getAttribute("data-allotment-course") || "B.Sc. Nursing";
  var showPreviousRoundFields = expectedCourse !== "B.Sc. Nursing";
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
    allottedCategory: "",
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
    allottedCategory: document.getElementById("allotted-category-filter"),
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

  function visibleValue(value) {
    return value && value !== "-" ? value : "—";
  }

  function renderCategoryFilter(selectedRecords) {
    var categories = Array.from(new Set(selectedRecords.map(function (record) {
      return String(record.allottedCategory == null ? "" : record.allottedCategory).trim();
    }).filter(Boolean))).sort(function (a, b) {
      return a.localeCompare(b, "en");
    });
    if (state.allottedCategory && categories.indexOf(state.allottedCategory) === -1) {
      state.allottedCategory = "";
    }
    elements.allottedCategory.innerHTML = '<option value="">All categories</option>' +
      categories.map(function (category) {
        return '<option value="' + escapeHtml(category) + '">' + escapeHtml(category) + "</option>";
      }).join("");
    elements.allottedCategory.value = state.allottedCategory;
  }

  function getFilteredRecords(selectedRecords) {
    var term = state.candidateSearch.trim().toLocaleLowerCase("en-IN");
    var minimum = state.minScore === "" ? Number.NEGATIVE_INFINITY : Number(state.minScore);
    var maximum = state.maxScore === "" ? Number.POSITIVE_INFINITY : Number(state.maxScore);

    return selectedRecords.filter(function (record) {
      var matchesCandidate = !term ||
        record.candidateName.toLocaleLowerCase("en-IN").includes(term) ||
        record.rollNo.toLocaleLowerCase("en-IN").includes(term);
      var matchesCategory = !state.allottedCategory || record.allottedCategory === state.allottedCategory;
      return matchesCandidate && record.cetScore >= minimum && record.cetScore <= maximum && matchesCategory;
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
    var previousRoundCells = showPreviousRoundFields
      ? "<td>" + escapeHtml(visibleValue(record.previousCourse)) + "</td>" +
        '<td><span class="category-tag">' + escapeHtml(visibleValue(record.previousCategory)) + "</span></td>" +
        '<td class="remark-cell">' + escapeHtml(visibleValue(record.previousRemark)) + "</td>"
      : "";
    return "<tr>" +
      '<td class="serial-cell">' + escapeHtml(record.serialNo) + "</td>" +
      "<td><span class=\"candidate-name\">" + escapeHtml(record.candidateName) + "</span>" +
        '<span class="candidate-sub">Roll no. ' + escapeHtml(record.rollNo) + "</span></td>" +
      '<td class="candidate-score">' + escapeHtml(record.cetScore) + "</td>" +
      "<td>" + escapeHtml(visibleValue(record.previousInstitute)) + "</td>" +
      previousRoundCells +
      "<td>" + escapeHtml(visibleValue(record.allottedInstitute)) + "</td>" +
      "<td>" + escapeHtml(visibleValue(record.allottedCourse)) + "</td>" +
      '<td><span class="category-tag">' + escapeHtml(visibleValue(record.allottedCategory)) + "</span></td>" +
      '<td class="remark-cell">' + escapeHtml(visibleValue(record.remark)) + "</td>" +
      "</tr>";
  }

  function renderRecordCard(record) {
    var details = [
      ["Previous institute", record.previousInstitute]
    ];
    if (showPreviousRoundFields) {
      details.push(
        ["Previous course", record.previousCourse],
        ["Previous category", record.previousCategory],
        ["Previous remark", record.previousRemark]
      );
    }
    details.push(
      ["Round 2 institute", record.allottedInstitute],
      ["Allotted course", record.allottedCourse],
      ["Allotted category", record.allottedCategory],
      ["Round 2 remark", record.remark]
    );
    return '<article class="record-card">' +
      '<div class="record-top"><div><span class="candidate-name">' + escapeHtml(record.candidateName) + "</span>" +
      '<span class="candidate-sub">Sr. No. ' + escapeHtml(record.serialNo) + " · Roll no. " + escapeHtml(record.rollNo) + "</span></div>" +
      '<span class="record-score">CET ' + escapeHtml(record.cetScore) + "</span></div>" +
      '<dl class="record-meta round2-record-meta">' + details.map(function (item) {
        return "<div><dt>" + escapeHtml(item[0]) + "</dt><dd>" +
          escapeHtml(visibleValue(item[1])) + "</dd></div>";
      }).join("") + "</dl></article>";
  }

  function renderCandidates() {
    var selectedRecords = recordsByCollege.get(state.selectedCollege) || [];
    renderCategoryFilter(selectedRecords);
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
    if (!records.length) throw new Error("The source file contains no " + expectedCourse + " records.");
    if (Number(data.round) !== 2 || data.course !== expectedCourse) {
      throw new Error("The loaded file is not the " + expectedCourse + " Round 2 dataset.");
    }

    records.forEach(function (record) {
      if (!recordsByCollege.has(record.allottedInstitute)) recordsByCollege.set(record.allottedInstitute, []);
      recordsByCollege.get(record.allottedInstitute).push(record);
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

    state.selectedCollege = records[0].allottedInstitute;
    elements.datasetSummary.textContent = records.length.toLocaleString() + " candidate records across " +
      colleges.length + " colleges · CET scores " +
      Math.min.apply(Math, records.map(function (record) { return record.cetScore; })) + "–" +
      Math.max.apply(Math, records.map(function (record) { return record.cetScore; })) +
      " · Round 2 as of " + String(data.asOf || "");
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
  elements.allottedCategory.addEventListener("change", function () {
    state.allottedCategory = elements.allottedCategory.value;
    resetPage();
  });
  elements.resetFilters.addEventListener("click", function () {
    state.collegeSearch = "";
    state.candidateSearch = "";
    state.minScore = "";
    state.maxScore = "";
    state.allottedCategory = "";
    state.collegeOrder = "alphabetical";
    state.pageSize = pageSizeOptions[0];
    state.page = 1;
    elements.collegeSearch.value = "";
    elements.candidateSearch.value = "";
    elements.minScore.value = "";
    elements.maxScore.value = "";
    elements.allottedCategory.value = "";
    elements.collegeOrder.value = "alphabetical";
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
    if (!response.ok) throw new Error("Round 2 allotment data could not be loaded (HTTP " + response.status + ").");
    return response.json();
  }).then(initialize).catch(function (error) {
    elements.loadMessage.classList.add("error");
    elements.loadMessage.textContent = error.message || "Round 2 allotment data could not be loaded.";
  });
})();
