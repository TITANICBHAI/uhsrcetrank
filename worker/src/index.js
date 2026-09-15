const EXAMS = {
  "bsc-nursing": "B.Sc Nursing",
  bpt: "BPT",
  paramedical: "Paramedical",
  "pb-bsc-nursing": "Post Basic B.Sc Nursing",
  "msc-nursing": "M.Sc Nursing",
  mpt: "MPT",
  npcc: "NPCC",
};

const JSON_HEADERS = {
  "content-type": "application/json; charset=utf-8",
  "cache-control": "no-store",
};

function response(body, init = {}) {
  return new Response(JSON.stringify(body), {
    ...init,
    headers: { ...JSON_HEADERS, ...(init.headers || {}) },
  });
}

function corsHeaders(request, env) {
  const configured = env.ALLOWED_ORIGIN || "*";
  const origin = request.headers.get("Origin");
  return {
    "access-control-allow-origin":
      configured === "*" || origin === configured ? configured : configured,
    "access-control-allow-methods": "GET, POST, DELETE, OPTIONS",
    "access-control-allow-headers": "Content-Type, X-Admin-Secret",
    vary: "Origin",
  };
}

function withCors(result, request, env) {
  const headers = new Headers(result.headers);
  for (const [key, value] of Object.entries(corsHeaders(request, env))) {
    headers.set(key, value);
  }
  return new Response(result.body, { status: result.status, headers });
}

function validRoll(value) {
  return /^[A-Z0-9-]{1,40}$/.test(value);
}

function numberParam(value, fallback, minimum, maximum) {
  const parsed = Number.parseInt(value || "", 10);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.min(Math.max(parsed, minimum), maximum);
}

function safeJson(value, fallback) {
  try {
    return JSON.parse(value || "");
  } catch {
    return fallback;
  }
}

function activeDatasetQuery(exam) {
  return `
    SELECT id, cet_exam, academic_year, display_name, version, ranking_mode,
           ranking_algorithm_version, ranking_criteria_json, candidate_count
    FROM datasets
    WHERE cet_exam = ? AND is_published = 1
    ORDER BY id DESC
    LIMIT 1
  `;
}

function publicCandidate(row, own = false) {
  const candidate = {
    roll_number: row.roll_number,
    name: own ? row.name : abbreviatedName(row.name),
    cet_score: row.cet_score,
    percentile: row.percentile,
    cet_exam: row.cet_exam,
  };
  if (own) {
    candidate.dob = row.dob;
    candidate.category = row.category;
    candidate.course = row.course;
    candidate.extra_fields = safeJson(row.extra_fields_json, {});
  }
  return candidate;
}

function abbreviatedName(name) {
  if (!name) return null;
  const parts = String(name).trim().split(/\s+/).filter(Boolean);
  return parts.length === 1
    ? `${parts[0].slice(0, 1)}.`
    : `${parts[0].slice(0, 1)}. ${parts[parts.length - 1].slice(0, 1)}.`;
}

async function getPublishedDataset(env, exam) {
  if (!env.DB) return null;
  return env.DB.prepare(activeDatasetQuery(exam)).bind(exam).first();
}

async function search(request, env, url) {
  const exam = url.searchParams.get("cet_exam") || "";
  const roll = (url.searchParams.get("roll_no") || "").trim().toUpperCase();
  if (!EXAMS[exam] || !validRoll(roll)) {
    return response(
      { status: "invalid", message: "Please select a recognized CET and enter a valid Roll Number." },
      { status: 400 },
    );
  }
  const dataset = await getPublishedDataset(env, exam);
  if (!dataset) {
    return response({
      status: "unavailable",
      message: "Result data for this CET examination has not been processed and published yet.",
    });
  }
  const row = await env.DB.prepare(`
    SELECT roll_number, normalized_roll_number, name, cet_score, percentile, dob,
           category, course, extra_fields_json, cet_exam, merit_position,
           published_order, tie_break_used
    FROM candidates
    WHERE dataset_id = ? AND normalized_roll_number = ?
    LIMIT 1
  `).bind(dataset.id, roll).first();
  if (!row) {
    return response({
      status: "not_found",
      message: "No candidate was found with this Roll Number in the selected CET 2026 dataset. Check the Roll Number and selected examination.",
    });
  }
  if (!Number.isInteger(row.merit_position)) {
    return response({
      status: "error",
      message: "This record was found, but a reliable estimated merit position is not available. No position has been invented.",
    });
  }
  const criteria = safeJson(dataset.ranking_criteria_json, []);
  const disclaimer = dataset.ranking_mode === "ENGINE" &&
    String(dataset.ranking_algorithm_version).includes("UNVERIFIED")
    ? "This estimate uses a ranking configuration that has not been verified against the complete published UHSR ordering. Do not treat it as an official UHSR rank."
    : null;
  const result = {
    status: "found",
    data: {
      candidate: publicCandidate(row, true),
      merit_position: row.merit_position,
      total_candidates: dataset.candidate_count,
      candidates_ahead: Math.max(row.merit_position - 1, 0),
      tie_break_used: row.tie_break_used,
      dataset_version: dataset.version,
      ranking_mode: dataset.ranking_mode,
      ranking_algorithm_version: dataset.ranking_algorithm_version,
      ranking_method: row.published_order != null ? "Published source order" : "Locally processed ranking",
      criteria,
      ranking_disclaimer: disclaimer,
      calculated_at: new Date().toISOString(),
    },
  };
  return response(result, { headers: { "cache-control": "public, max-age=300" } });
}

async function activeDatasets(env) {
  const { results = [] } = await env.DB.prepare(`
    SELECT cet_exam, academic_year, display_name, version, ranking_mode,
           ranking_algorithm_version, candidate_count
    FROM datasets
    WHERE is_published = 1
    ORDER BY cet_exam
  `).all();
  return response(results.map((item) => ({
    cet_exam: item.cet_exam,
    label: item.display_name || EXAMS[item.cet_exam] || item.cet_exam,
    academic_year: item.academic_year,
    dataset_version: item.version,
    ranking_mode: item.ranking_mode,
    ranking_algorithm_version: item.ranking_algorithm_version,
    candidate_count: item.candidate_count,
  })), { headers: { "cache-control": "public, max-age=300" } });
}

async function candidateWindow(env, url, mode) {
  const exam = url.searchParams.get("cet_exam") || "";
  const position = numberParam(url.searchParams.get("position"), 0, 1, 2147483647);
  const pageSize = numberParam(url.searchParams.get("limit"), 20, 1, 50);
  if (!EXAMS[exam] || !position) {
    return response({ status: "invalid", message: "A recognized CET and position are required." }, { status: 400 });
  }
  const dataset = await getPublishedDataset(env, exam);
  if (!dataset) return response({ status: "unavailable", items: [] });

  if (mode === "nearby") {
    const windowSize = Math.min(numberParam(url.searchParams.get("window"), 5, 1, 10), 10);
    const rows = await env.DB.prepare(`
      SELECT roll_number, name, cet_score, percentile, cet_exam, merit_position
      FROM candidates
      WHERE dataset_id = ? AND merit_position BETWEEN ? AND ?
      ORDER BY merit_position ASC
      LIMIT 21
    `).bind(dataset.id, Math.max(1, position - windowSize), position + windowSize).all();
    return response({
      status: "ok",
      position,
      items: (rows.results || []).map((row) => ({
        position: row.merit_position,
        roll_number: row.roll_number,
        name: abbreviatedName(row.name),
        cet_score: row.cet_score,
        percentile: row.percentile,
        is_self: row.merit_position === position,
      })),
    }, { headers: { "cache-control": "public, max-age=300" } });
  }

  const page = numberParam(url.searchParams.get("page"), 1, 1, 1000000);
  const offset = (page - 1) * pageSize;
  const [rows, count] = await Promise.all([
    env.DB.prepare(`
      SELECT roll_number, name, cet_score, percentile, cet_exam, merit_position
      FROM candidates
      WHERE dataset_id = ? AND merit_position < ?
      ORDER BY merit_position DESC
      LIMIT ? OFFSET ?
    `).bind(dataset.id, position, pageSize, offset).all(),
    env.DB.prepare(`
      SELECT COUNT(*) AS total
      FROM candidates
      WHERE dataset_id = ? AND merit_position < ?
    `).bind(dataset.id, position).first(),
  ]);
  const items = (rows.results || []).map((row) => ({
    position: row.merit_position,
    roll_number: row.roll_number,
    name: abbreviatedName(row.name),
    cet_score: row.cet_score,
    percentile: row.percentile,
  }));
  return response({
    status: "ok",
    position,
    page,
    page_size: pageSize,
    total_above: count?.total || 0,
    has_more: offset + items.length < (count?.total || 0),
    items,
  }, { headers: { "cache-control": "public, max-age=300" } });
}

function authorized(request, env) {
  const secret = env.ADMIN_SECRET;
  return Boolean(secret && request.headers.get("X-Admin-Secret") === secret);
}

async function admin(request, env, url) {
  if (!authorized(request, env)) {
    return response({ error: "Unauthorized", code: "UNAUTHORIZED" }, { status: 401 });
  }
  const parts = url.pathname.split("/").filter(Boolean);
  if (request.method === "GET" && parts.length === 2 && parts[1] === "datasets") {
    const { results = [] } = await env.DB.prepare(`
      SELECT id, cet_exam, academic_year, display_name, version, ranking_mode,
             ranking_algorithm_version, candidate_count, validation_status,
             is_published, created_at, published_at
      FROM datasets ORDER BY id DESC
    `).all();
    return response(results);
  }
  if (parts[1] !== "datasets" || !parts[2]) {
    return response({ error: "Not found", code: "NOT_FOUND" }, { status: 404 });
  }
  const datasetId = Number.parseInt(parts[2], 10);
  if (!Number.isInteger(datasetId)) return response({ error: "Invalid dataset id" }, { status: 400 });
  const dataset = await env.DB.prepare("SELECT * FROM datasets WHERE id = ?").bind(datasetId).first();
  if (!dataset) return response({ error: "Dataset not found", code: "NOT_FOUND" }, { status: 404 });

  if (parts[3] === "validation" && request.method === "GET") {
    return response(safeJson(dataset.validation_report_json, {}));
  }
  if (parts[3] === "publish" && request.method === "POST") {
    if (dataset.validation_status !== "PASS" && dataset.validation_status !== "PASS_WITH_WARNINGS") {
      return response({ error: "Validation must pass before publication", code: "VALIDATION_REQUIRED" }, { status: 422 });
    }
    await env.DB.batch([
      env.DB.prepare("UPDATE datasets SET is_published = 0, published_at = NULL WHERE cet_exam = ?").bind(dataset.cet_exam),
      env.DB.prepare("UPDATE datasets SET is_published = 1, published_at = CURRENT_TIMESTAMP WHERE id = ?").bind(datasetId),
    ]);
    return response({ status: "published", id: datasetId });
  }
  if (parts[3] === "unpublish" && request.method === "POST") {
    await env.DB.prepare("UPDATE datasets SET is_published = 0, published_at = NULL WHERE id = ?").bind(datasetId).run();
    return response({ status: "unpublished", id: datasetId });
  }
  if (request.method === "DELETE" && !dataset.is_published) {
    await env.DB.prepare("DELETE FROM datasets WHERE id = ?").bind(datasetId).run();
    return response({ status: "deleted", id: datasetId });
  }
  return response({ error: "Action not found", code: "NOT_FOUND" }, { status: 404 });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "OPTIONS") {
      return withCors(new Response(null, { status: 204 }), request, env);
    }
    let result;
    try {
      if (url.pathname === "/api/health") result = response({ status: "ok" });
      else if (url.pathname === "/api/datasets/active" || url.pathname === "/api/datasets") {
        result = await activeDatasets(env);
      } else if (url.pathname === "/api/search") {
        result = await search(request, env, url);
      } else if (url.pathname === "/api/candidates/nearby") {
        result = await candidateWindow(env, url, "nearby");
      } else if (url.pathname === "/api/candidates/above") {
        result = await candidateWindow(env, url, "above");
      } else if (url.pathname.startsWith("/admin/")) {
        result = await admin(request, env, url);
      } else {
        result = response({ error: "Not found", code: "NOT_FOUND" }, { status: 404 });
      }
    } catch (error) {
      console.error("request failed", error);
      result = response({ error: "The service could not complete that request.", code: "INTERNAL_ERROR" }, { status: 500 });
    }
    return withCors(result, request, env);
  },
};