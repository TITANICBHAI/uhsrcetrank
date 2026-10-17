(function () {
  "use strict";

  var dataUrl = document.body.getAttribute("data-allotment-data") ||
    "data/msc-nursing-allotments-2026-27.json";
  var expectedRound = document.body.getAttribute("data-allotment-round") || "Round 1";
  var courseField = document.body.getAttribute("data-allotted-course-field") || "course";
  var isRound2 = expectedRound === "Round 2";
  var pageSizeOptions = [25, 50, 100];
  var records = [];
  var recordsByCourse = new Map();
  var courses = [];
  var state = {
    selectedCourse: "",
    candidateSearch: "",
    minScore: "",
    maxScore: "",
    allottedCategory: "",
    page: 1,
    pageSize: pageSizeOptions[0]
  };

  var elements = {
    loadMessage: document.getElementById("load-message"),
    layout: document.querySelector(".course-allotment-layout"),
    datasetSummary: document.getElementById("dataset-summary"),
    courseSelect: document.getElementById("course-select"),
    courseCount: document.getElementById("course-count"),
    selectedCourse: document.getElementById("selected-course"),
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

  function getCategory(record) {
    return isRound2 ? record.allottedCategory : record.category;
  }

  function renderCategoryFilter(courseRecords) {
    var categories = Array.from(new Set(courseRecords.map(function (record) {
      return String(getCategory(record) == null ? "" : getCategory(record)).trim();
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

  function getFilteredRecords(courseRecords) {
    var term = state.candidateSearch.trim().toLocaleLowerCase("en-IN");
    var minimum = state.minScore === "" ? Number.NEGATIVE_INFINITY : Number(state.minScore);
    var maximum = state.maxScore === "" ? Number.POSITIVE_INFINITY : Number(state.maxScore);

    return courseRecords.filter(function (record) {
      var matchesCandidate = !term ||
        record.candidateName.toLocaleLowerCase("en-IN").includes(term) ||
        record.rollNo.toLocaleLowerCase("en-IN").includes(term);
      var matchesCategory = !state.allottedCategory || getCategory(record) === state.allottedCategory;
      return matchesCandidate && record.cetScore >= minimum && record.cetScore <= maximum && matchesCategory;
    }).sort(function (a, b) {
      return b.cetScore - a.cetScore || a.serialNo - b.serialNo;
    });
  }

  function renderCandidates() {
    var courseRecords = recordsByCourse.get(state.selectedCourse) || [];
    renderCategoryFilter(courseRecords);
    var filtered = getFilteredRecords(courseRecords);
    var pageCount = Math.max(1, Math.ceil(filtered.length / state.pageSize));
    state.page = Math.min(state.page, pageCount);
    var start = (state.page - 1) * state.pageSize;
    var pageRecords = filtered.slice(start, start + state.pageSize);
    var firstShown = filtered.length ? start + 1 : 0;
    var lastShown = Math.min(start + state.pageSize, filtered.length);
    var scores = courseRecords.map(function (record) { return record.cetScore; });

    elements.selectedCourse.textContent = state.selectedCourse || "No course selected";
    elements.selectedTotal.textContent = courseRecords.length.toLocaleString();
    elements.statTotal.textContent = courseRecords.length.toLocaleString();
    elements.statMin.textContent = scores.length ? String(Math.min.apply(Math, scores)) : "—";
    elements.statMax.textContent = scores.length ? String(Math.max.apply(Math, scores)) : "—";
    elements.resultsSummary.innerHTML = "Showing <strong>" + firstShown.toLocaleString() + "–" + lastShown.toLocaleString() +
      "</strong> of <strong>" + filtered.length.toLocaleString() + "</strong> matching candidates · CET score descending";
    elements.pageStatus.textContent = "Page " + state.page + " of " + pageCount;
    elements.previousPage.disabled = state.page <= 1;
    elements.nextPage.disabled = state.page >= pageCount;
    elements.candidateRows.innerHTML = pageRecords.map(renderRecordRow).join("");
    elements.candidateCards.innerHTML = pageRecords.map(renderRecordCard).join("");
    elements.emptyResults.hidden = pageRecords.length > 0;
    elements.candidateRows.closest(".desktop-records").hidden = pageRecords.length === 0;
    elements.candidateCards.hidden = pageRecords.length === 0;
  }

  function renderRecordRow(record) {
    if (isRound2) {
      return "<tr>" +
        '<td class="serial-cell">' + escapeHtml(record.serialNo) + "</td>" +
        "<td><span class=\"candidate-name\">" + escapeHtml(record.candidateName) + "</span>" +
          '<span class="candidate-sub">Roll no. ' + escapeHtml(record.rollNo) + "</span></td>" +
        '<td class="candidate-score">' + escapeHtml(record.cetScore) + "</td>" +
        "<td>" + escapeHtml(visibleValue(record.previousInstitute)) + "</td>" +
        "<td>" + escapeHtml(visibleValue(record.previousCourse)) + "</td>" +
        '<td><span class="category-tag">' + escapeHtml(visibleValue(record.previousCategory)) + "</span></td>" +
        '<td class="remark-cell">' + escapeHtml(visibleValue(record.previousRemark)) + "</td>" +
        "<td>" + escapeHtml(visibleValue(record.allottedInstitute)) + "</td>" +
        "<td>" + escapeHtml(visibleValue(record.allottedCourse)) + "</td>" +
        '<td><span class="category-tag">' + escapeHtml(visibleValue(record.allottedCategory)) + "</span></td>" +
        '<td class="remark-cell">' + escapeHtml(visibleValue(record.remark)) + "</td>" +
        "</tr>";
    }
    return "<tr>" +
      '<td class="serial-cell">' + escapeHtml(record.serialNo) + "</td>" +
      "<td><span class=\"candidate-name\">" + escapeHtml(record.candidateName) + "</span>" +
        '<span class="candidate-sub">Roll no. ' + escapeHtml(record.rollNo) + "</span></td>" +
      '<td class="candidate-score">' + escapeHtml(record.cetScore) + "</td>" +
      '<td><span class="category-tag">' + escapeHtml(record.category) + "</span></td>" +
      "<td>" + escapeHtml(record.college) + "</td>" +
      '<td class="remark-cell">' + escapeHtml(record.remark) + "</td>" +
      "</tr>";
  }

  function renderRecordCard(record) {
    if (isRound2) {
      var round2Details = [
        ["Allotted course", record.allottedCourse],
        ["Previous institute", record.previousInstitute],
        ["Previous course", record.previousCourse],
        ["Previous category", record.previousCategory],
        ["Previous remark", record.previousRemark],
        ["Round 2 institute", record.allottedInstitute],
        ["Allotted category", record.allottedCategory],
        ["Round 2 remark", record.remark]
      ];
      return '<article class="record-card">' +
        '<div class="record-top"><div><span class="candidate-name">' + escapeHtml(record.candidateName) + "</span>" +
        '<span class="candidate-sub">Sr. No. ' + escapeHtml(record.serialNo) + " · Roll no. " + escapeHtml(record.rollNo) + "</span></div>" +
        '<span class="record-score">CET ' + escapeHtml(record.cetScore) + "</span></div>" +
        '<dl class="record-meta round2-record-meta">' + round2Details.map(function (item) {
          return "<div><dt>" + escapeHtml(item[0]) + "</dt><dd>" +
            escapeHtml(visibleValue(item[1])) + "</dd></div>";
        }).join("") + "</dl></article>";
    }
    return '<article class="record-card">' +
      '<div class="record-top"><div><span class="candidate-name">' + escapeHtml(record.candidateName) + "</span>" +
      '<span class="candidate-sub">Sr. No. ' + escapeHtml(record.serialNo) + " · Roll no. " + escapeHtml(record.rollNo) + "</span></div>" +
      '<span class="record-score">CET ' + escapeHtml(record.cetScore) + "</span></div>" +
      '<dl class="record-meta">' +
      '<div><dt>Allotted course</dt><dd>' + escapeHtml(record.course) + "</dd></div>" +
      '<div><dt>Category</dt><dd><span class="category-tag">' + escapeHtml(record.category) + "</span></dd></div>" +
      "<div><dt>Allotted institute</dt><dd>" + escapeHtml(record.college) + "</dd></div>" +
      "<div><dt>Remark / status</dt><dd>" + escapeHtml(record.remark) + "</dd></div>" +
      "</dl></article>";
  }

  function initialize(data) {
    records = Array.isArray(data.records) ? data.records : [];
    if (!records.length) throw new Error("The M.Sc. Nursing allotment dataset contains no candidate records.");
    var dataRound = typeof data.round === "number" ? "Round " + data.round : String(data.round || "");
    if (data.course !== "M.Sc. Nursing" || dataRound !== expectedRound) {
      throw new Error("The loaded file is not the M.Sc. Nursing " + expectedRound + " dataset.");
    }

    records.forEach(function (record) {
      var course = record[courseField];
      if (!course || course === "-") {
        throw new Error("A record is missing its allotted course.");
      }
      if (!recordsByCourse.has(course)) recordsByCourse.set(course, []);
      recordsByCourse.get(course).push(record);
    });

    courses = Array.from(recordsByCourse.keys()).sort(function (a, b) {
      return a.localeCompare(b, "en");
    });
    elements.courseSelect.innerHTML = courses.map(function (course) {
      return '<option value="' + escapeHtml(course) + '">' + escapeHtml(course) +
        " (" + recordsByCourse.get(course).length.toLocaleString() + ")</option>";
    }).join("");
    state.selectedCourse = courses[0];
    elements.courseCount.textContent = courses.length.toLocaleString() + " allotted courses";
    elements.datasetSummary.textContent = records.length.toLocaleString() + " allotted candidates across " +
      courses.length.toLocaleString() + " courses · CET scores " +
      Math.min.apply(Math, records.map(function (record) { return record.cetScore; })) + "–" +
      Math.max.apply(Math, records.map(function (record) { return record.cetScore; })) +
      " · List dated " + String(data.asOf || "unknown date");
    elements.layout.hidden = false;
    elements.loadMessage.hidden = true;
    renderCandidates();
  }

  function resetPage() {
    state.page = 1;
    renderCandidates();
  }

  elements.courseSelect.addEventListener("change", function () {
    state.selectedCourse = elements.courseSelect.value;
    state.page = 1;
    renderCandidates();
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
    state.candidateSearch = "";
    state.minScore = "";
    state.maxScore = "";
    state.allottedCategory = "";
    state.pageSize = pageSizeOptions[0];
    state.page = 1;
    elements.candidateSearch.value = "";
    elements.minScore.value = "";
    elements.maxScore.value = "";
    elements.allottedCategory.value = "";
    elements.pageSize.value = String(state.pageSize);
    renderCandidates();
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
    if (!response.ok) throw new Error("M.Sc. Nursing allotment data could not be loaded (HTTP " + response.status + ").");
    return response.json();
  }).then(initialize).catch(function (error) {
    elements.loadMessage.classList.add("error");
    elements.loadMessage.textContent = error.message || "M.Sc. Nursing allotment data could not be loaded.";
  });
})();
