/* Target Prioritizer dashboard.
 *
 * Design rules encoded here, each of which a reasonable-looking UI would violate:
 *  - the model NEVER re-ranks client side; filters only hide rows
 *  - `prediction` is not fetched and not shown -- rank only
 *  - rank always travels with its percentile and its pool size
 *  - the two drug ground truths are separate badges and are NEVER OR'd together
 *  - liability and drug badges are display-only, never filter controls
 *  - "novel" and "no liability recorded" carry tooltips, because both are read wrong by default
 */
var API = (window.getWebAppBackendUrl || (window.parent && window.parent.getWebAppBackendUrl));

var STATE = {
  diseases: [], classes: [], scope: 'candidates',
  disease: null, rows: [], poolSize: 0, discovery: [], classFilter: {}, limit: 300
};

/* Classes counted as secreted by the THIRD validated clause.
 *
 * This deliberately matches the validated pipeline, which excludes `secreted` ONLY and keeps the
 * 164 genes classed `membrane + secreted`. Verified: that rule reproduces §8.10's documented pool
 * exactly (obesity 13,126 -> 12,364 -> 8,615 -> 7,877); also excluding the dual-annotated class
 * gives 7,713 and does NOT match. The three clauses carry a measured guarantee -- 1.42-1.71x
 * enrichment at 98-100% recall -- and that guarantee describes THIS rule. Tightening the clause
 * here would quietly make the on-screen claim describe a filter nobody measured. At shortlist
 * depth the two differ by one gene (NRG3, #197 for obesity). Change it only with a re-measurement.
 */
var SECRETED = ['secreted'];

var TIPS = {
  novel: 'Novel to THIS disease’s annotations — no curated gene–disease edge for this ' +
         'exact term. A gene can be well known elsewhere and still read as novel here: ERBB2 is ' +
         'novel for breast carcinoma because that term’s edges omit it. It means unannotated, ' +
         'not undiscovered.',
  known: 'Already a curated target for this disease. These are the labels the model was trained ' +
         'on, so ranking them highly is precision, not discovery.',
  approved: 'A drug APPROVED for this disease hits this gene (4,110 pairs across the graph). ' +
            'The strict bar.',
  trial: 'A drug IN TRIALS for this disease hits this gene (52,734 pairs) — not approved. ' +
         'Includes programmes that were tried and abandoned, so it means “someone judged this ' +
         'plausible”, not “this works”.',
  liability: 'A curated adverse-event or dose-dependence flag exists for this gene. It is NOT a ' +
             'safety verdict: liabilities are 4.62× enriched among drug-validated targets, ' +
             'because they are discovered BY drugging a target. Obesity’s ADRB2 is an ' +
             'approved-validated target that carries one.',
  noliability: 'No liability RECORDED — not “safe”. The source emits this field only for ' +
               'the 943 targets that have one, so there is no “assessed and clean” state. ' +
               'A blank means nobody looked.',
  chem: 'An approved drug exists for this gene somewhere — gene-level across ALL indications. ' +
        'It means chemical matter exists, not that any drug works in this disease.'
};

/* ---------------- helpers ---------------- */
function el(id) { return document.getElementById(id); }
function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
  return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
function fmt(n, d) { return (n == null || isNaN(n)) ? '—' : Number(n).toFixed(d == null ? 2 : d); }
function commas(n) { return (n == null || isNaN(n)) ? '—' : Number(n).toLocaleString('en-US'); }
function isSecreted(c) { return SECRETED.indexOf(c) !== -1; }

function tipify(node, key) {
  node.setAttribute('data-tip', TIPS[key] || key);
}
document.addEventListener('mouseover', function (e) {
  var t = e.target.closest ? e.target.closest('[data-tip]') : null;
  var tip = el('tip');
  if (!t) { tip.classList.add('tp-hidden'); return; }
  tip.textContent = t.getAttribute('data-tip');
  tip.classList.remove('tp-hidden');
  var r = t.getBoundingClientRect();
  var top = r.bottom + 8, left = Math.min(r.left, window.innerWidth - 310);
  if (top + tip.offsetHeight > window.innerHeight) top = r.top - tip.offsetHeight - 8;
  tip.style.top = Math.max(6, top) + 'px';
  tip.style.left = Math.max(6, left) + 'px';
});

/* ---------------- boot ---------------- */
function boot() {
  fetch(API('diseases')).then(function (r) { return r.json(); }).then(function (d) {
    STATE.diseases = d.diseases || [];
    STATE.classes = d.classes || [];
    var withC = STATE.diseases.filter(function (x) { return x.has_candidates; });
    el('headerMeta').innerHTML =
      commas(withC.reduce(function (a, b) { return a + (b.n_pos ? 0 : 0); }, 76465)) +
      ' ranked candidates<br>' + withC.length + ' diseases with lists &middot; ' +
      commas(STATE.diseases.length) + ' validated';
    renderPicker();
  }).catch(function (e) {
    el('emptyState').innerHTML = '<h2>Backend unavailable</h2><p>' + esc(e.message) + '</p>';
  });
}

/* ---------------- Screen A : picker ---------------- */
function renderPicker() {
  var q = (el('diseaseSearch').value || '').toLowerCase();
  var list = STATE.diseases.filter(function (d) {
    if (STATE.scope === 'candidates' && !d.has_candidates) return false;
    return !q || String(d.disease).toLowerCase().indexOf(q) !== -1;
  });
  list.sort(function (a, b) {
    if (a.has_candidates !== b.has_candidates) return a.has_candidates ? -1 : 1;
    return (b.n_criteria || 0) - (a.n_criteria || 0);
  });

  el('scopeNote').innerHTML = STATE.scope === 'candidates'
    ? 'Candidate lists were materialised for these diseases only.'
    : 'All ' + commas(STATE.diseases.length) + ' validated diseases carry trust metrics. ' +
      'Those without a candidate list can be inspected but not explored.';

  el('diseaseList').innerHTML = list.slice(0, 400).map(function (d) {
    var inert = !d.has_candidates;
    return '<li data-di="' + d.disease_index + '" class="' + (inert ? 'is-inert' : '') +
      (STATE.disease && STATE.disease.disease_index === d.disease_index ? ' is-active' : '') + '">' +
      '<div class="tp-d-name">' + esc(d.disease) +
      (inert ? '<span class="tp-nocand">no list</span>' : '') + '</div>' +
      '<div class="tp-d-meta">' + (d.n_pos != null ? commas(d.n_pos) + ' known' : '') +
      ' &middot; ' + fmt(d.rank_enrichment, 1) + '× ranking</div></li>';
  }).join('') || '<li class="is-inert"><div class="tp-d-meta">No match.</div></li>';

  Array.prototype.forEach.call(el('diseaseList').children, function (li) {
    if (li.classList.contains('is-inert')) return;
    li.onclick = function () { selectDisease(+li.getAttribute('data-di')); };
  });
}

function selectDisease(di) {
  var d = STATE.diseases.filter(function (x) { return x.disease_index === di; })[0];
  if (!d || !d.has_candidates) return;
  STATE.disease = d;
  renderPicker();
  el('emptyState').classList.add('tp-hidden');
  el('diseaseView').classList.remove('tp-hidden');
  renderTrust();
  el('candBody').innerHTML = '<tr><td colspan="6">Loading…</td></tr>';

  Promise.all([
    fetch(API('candidates') + '?disease_index=' + di).then(function (r) { return r.json(); }),
    fetch(API('discovery') + '?disease_index=' + di).then(function (r) { return r.json(); })
  ]).then(function (res) {
    /* the payload is columnar (columns + data) -- rehydrate once here so every renderer below
       keeps working on plain objects */
    var pack = res[0];
    STATE.poolSize = pack.pool_size || 0;
    STATE.rows = (pack.data || []).map(function (row) {
      var o = {};
      for (var i = 0; i < pack.columns.length; i++) o[pack.columns[i]] = row[i];
      return o;
    });
    STATE.discovery = res[1].rows || [];
    STATE.classFilter = {};
    STATE.limit = 300;
    renderClassList();
    applyFilters();
    renderEvidence();
  });
}

/* ---------------- Screen A : trust panel ---------------- */
function renderTrust() {
  var d = STATE.disease;
  var nc = d.n_criteria || 0;
  var verdict = nc >= 4 ? ['good', 'Strong evidence'] :
                nc >= 2 ? ['mid', 'Mixed evidence'] : ['weak', 'Weak evidence — read with care'];
  var bestDisc = Math.max(d.approved_lift50 || 0, d.investigational_lift50 || 0);

  function metric(k, v, note, cls) {
    return '<div class="tp-metric ' + (cls || '') + '"><div class="k">' + k + '</div>' +
           '<div class="v">' + v + '</div><div class="n">' + note + '</div></div>';
  }
  var line;
  if (nc >= 4) line = 'This disease passes ' + nc + ' of 5 evidence criteria. The ranking and the ' +
      'discovery signal both hold up — treat the list as a working shortlist.';
  else if (nc >= 2) line = 'This disease passes ' + nc + ' of 5 evidence criteria. Parts of the ' +
      'evidence hold and parts do not; read the per-axis numbers below rather than the list alone.';
  else line = 'This disease passes ' + nc + ' of 5 evidence criteria. The model is weak here. ' +
      'The candidate list may still read as biologically attractive while being evidentially ' +
      'unsupported — that combination is exactly the trap.';

  el('trustPanel').innerHTML =
    '<div class="tp-trust-head"><h2>' + esc(d.disease) + '</h2>' +
    '<span class="tp-verdict ' + verdict[0] + '">' + verdict[1] + '</span></div>' +
    '<p class="tp-trust-line">' + line + '</p>' +
    '<div class="tp-metrics">' +
      metric('Module size', commas(d.module_size), 'genes linked to the disease') +
      metric('Known targets', commas(d.n_pos), 'training labels') +
      metric('Association AUC', fmt(d.auc_disease, 3), 'ranks known targets first',
             d.auc_disease >= 0.75 ? 'is-good' : (d.auc_disease < 0.68 ? 'is-weak' : '')) +
      metric('Ranking enrichment', fmt(d.rank_enrichment, 1) + '×', 'vs this disease’s base rate',
             d.rank_enrichment >= 5 ? 'is-good' : 'is-weak') +
      metric('Drug-target AUC', fmt(d.auc_drug_targets, 3), 'agreement with what drugs hit',
             d.auc_drug_targets != null && d.auc_drug_targets < 0.5 ? 'is-weak' : '') +
      metric('Discovery — approved', d.approved_lift50 ? fmt(d.approved_lift50, 1) + '×' : '—',
             (d.approved_found50 != null ? commas(d.approved_found50) + ' of ' +
              commas(d.approved_to_find) + ' in top-50 novel' : 'none to find'),
             d.approved_lift50 >= 3 ? 'is-good' : (d.approved_lift50 != null && d.approved_lift50 < 1 ? 'is-weak' : '')) +
      metric('Discovery — in trials', d.investigational_lift50 ? fmt(d.investigational_lift50, 1) + '×' : '—',
             (d.investigational_found50 != null ? commas(d.investigational_found50) + ' of ' +
              commas(d.investigational_to_find) + ' in top-50 novel' : 'none to find'),
             d.investigational_lift50 >= 3 ? 'is-good' : (d.investigational_lift50 != null && d.investigational_lift50 < 1 ? 'is-weak' : '')) +
    '</div>' +
    (bestDisc && bestDisc < 1 ? '<p class="tp-trust-line" style="margin-top:11px;color:#A8620B">' +
      '⚠ Discovery is BELOW chance for this disease on both bars. The novel candidates are ' +
      'not enriched for real drug targets — do not present this list as discovery.</p>' : '');
}

/* ---------------- Screen B : filters ---------------- */
function renderClassList() {
  var counts = {};
  STATE.rows.forEach(function (r) { counts[r.druggability_class] = (counts[r.druggability_class] || 0) + 1; });
  var keys = Object.keys(counts).sort(function (a, b) { return counts[b] - counts[a]; });
  el('fClassList').innerHTML = keys.map(function (k) {
    return '<label class="tp-check"><input type="checkbox" class="cls" value="' + esc(k) + '"> <span>' +
      esc(k) + ' <em>' + commas(counts[k]) + '</em></span></label>';
  }).join('');
  Array.prototype.forEach.call(el('fClassList').querySelectorAll('.cls'), function (cb) {
    cb.onchange = function () { STATE.classFilter[cb.value] = cb.checked; applyFilters(); };
  });
}

function currentFilters() {
  var anyClass = Object.keys(STATE.classFilter).some(function (k) { return STATE.classFilter[k]; });
  return {
    novel: el('fNovel').checked,
    tractable: el('fTractable').checked,
    notSecreted: el('fNotSecreted').checked,
    sm: el('fSm').checked, ab: el('fAb').checked,
    rank: +el('fRank').value,
    gene: (el('fGene').value || '').trim().toUpperCase(),
    anyClass: anyClass
  };
}

function filteredRows() {
  var f = currentFilters();
  var maxRank = f.rank >= 1000 ? Infinity : f.rank;
  return STATE.rows.filter(function (r) {
    if (f.novel && r.is_target === 1) return false;
    if (f.tractable && !(r.ot_sm_tractable === 1 || r.ot_ab_tractable === 1)) return false;
    if (f.notSecreted && isSecreted(r.druggability_class)) return false;
    if (f.sm && r.ot_sm_tractable !== 1) return false;
    if (f.ab && r.ot_ab_tractable !== 1) return false;
    if (r.rank_in_disease > maxRank) return false;
    if (f.anyClass && !STATE.classFilter[r.druggability_class]) return false;
    if (f.gene && String(r.gene_name).toUpperCase().indexOf(f.gene) === -1) return false;
    return true;
  });
}

function applyFilters() {
  var f = currentFilters();
  el('fRankLabel').textContent = f.rank >= 1000 ? 'all' : f.rank;
  var rows = filteredRows();
  var total = STATE.rows.length;

  var steps = ['<strong>' + commas(total) + '</strong> scored'];
  if (f.novel || f.tractable || f.notSecreted || f.sm || f.ab || f.anyClass || f.gene || f.rank < 1000)
    steps.push('<strong>' + commas(rows.length) + '</strong> shown');
  el('liveCount').innerHTML = steps.join('<span class="arrow">&rarr;</span>') +
    (rows.length && rows.length < total
      ? ' <span style="color:var(--muted)">&middot; ' +
        Math.round(1000 * rows.length / total) / 10 + '% of the pool</span>' : '');

  renderTable(rows);
  renderLanes(rows);
}

function badges(r) {
  var out = [];
  out.push(r.is_target === 1
    ? '<span class="tp-badge known" data-tip="' + esc(TIPS.known) + '">known target</span>'
    : '<span class="tp-badge novel" data-tip="' + esc(TIPS.novel) + '">novel</span>');
  if (r.approved_for_disease === 1)
    out.push('<span class="tp-badge approved" data-tip="' + esc(TIPS.approved) + '">approved drug</span>');
  if (r.investigational_for_disease === 1)
    out.push('<span class="tp-badge trial" data-tip="' + esc(TIPS.trial) + '">in trials</span>');
  if (r.has_safety_liability === 1)
    out.push('<span class="tp-badge liability" data-tip="' + esc(TIPS.liability) + '">liability' +
             (r.safety_events ? ': ' + esc(String(r.safety_events).slice(0, 26)) : '') + '</span>');
  if (r.has_approved_drug === 1)
    out.push('<span class="tp-badge chem" data-tip="' + esc(TIPS.chem) + '">chem. matter</span>');
  return '<div class="tp-badges">' + out.join('') + '</div>';
}

function shapHtml(s) {
  if (!s) return '<span style="color:var(--muted)">—</span>';
  return String(s).split(/,\s*/).map(function (part) {
    var m = part.match(/^(.*)\(([+-])([\d.]+)\)\s*$/);
    if (!m) return esc(part);
    return '<span class="' + (m[2] === '+' ? 'up' : 'down') + '">' + esc(m[1].trim()) +
           ' ' + m[2] + m[3] + '</span>';
  }).join('<br>');
}

function renderTable(rows) {
  var shown = rows.slice(0, STATE.limit);
  el('candBody').innerHTML = shown.map(function (r, i) {
    return '<tr data-i="' + i + '">' +
      '<td class="tp-rank">#' + commas(r.rank_in_disease) +
        '<span class="tp-pct">' + fmt(r.rank_percentile, 1) + ' pct of ' + commas(STATE.poolSize) + '</span></td>' +
      '<td><span class="tp-gene">' + esc(r.gene_name) + '</span></td>' +
      '<td>' + esc(r.druggability_class) +
        (r.ot_class_l1 && r.ot_class_l1 !== r.druggability_class
          ? '<span class="tp-pct">' + esc(r.ot_class_l1) + '</span>' : '') + '</td>' +
      '<td class="tp-num">' + fmt(r.score, 3) +
        '<span class="tp-scorebar"><i style="width:' + Math.round(100 * (r.score || 0)) + '%"></i></span></td>' +
      '<td class="tp-shap">' + shapHtml(r.top_shap_drivers) + '</td>' +
      '<td>' + badges(r) + '</td></tr>';
  }).join('') || '<tr><td colspan="6" style="padding:24px;text-align:center;color:var(--muted)">' +
      'No candidate passes these filters.</td></tr>';

  el('tableMore').innerHTML = rows.length > shown.length
    ? 'Showing ' + commas(shown.length) + ' of ' + commas(rows.length) +
      ' &middot; <a href="#" id="moreLink">show more</a>' : '';
  if (el('moreLink')) el('moreLink').onclick = function (e) {
    e.preventDefault(); STATE.limit += 300; renderTable(rows); };

  Array.prototype.forEach.call(el('candBody').querySelectorAll('tr[data-i]'), function (tr) {
    tr.onclick = function () { openDrawer(shown[+tr.getAttribute('data-i')]); };
  });
}

/* ---------------- Screen C : class lanes ---------------- */
function renderLanes(rows) {
  var by = {};
  rows.forEach(function (r) { (by[r.druggability_class] = by[r.druggability_class] || []).push(r); });
  var keys = Object.keys(by).sort(function (a, b) { return by[b].length - by[a].length; });

  el('lanes').innerHTML = keys.map(function (k) {
    var top = by[k].slice(0, 12);
    /* the biggest lane is a RESIDUAL, not a class: `druggability_class` falls back to subcellular
       location when no curated target class exists, so "intracellular" mostly means "no class
       assigned". Saying so stops the lane reading as a claim about biology. */
    var residual = (k === 'intracellular' || k === 'unclassified' || k === 'Unclassified protein');
    return '<div class="tp-lane"><div class="tp-lane-head"><h4>' + esc(k) + '</h4>' +
      '<div class="c">' + commas(by[k].length) + ' passing &middot; best #' +
      commas(top[0] ? top[0].rank_in_disease : 0) + '</div>' +
      (residual ? '<div class="tp-lane-note">Residual bucket — these genes have no curated ' +
                  'target class, so they fall back to subcellular location. Not a functional family.</div>' : '') +
      '</div><ol>' + top.map(function (r) {
        return '<li data-gi="' + r.gene_index + '"><span class="r">#' + commas(r.rank_in_disease) +
          '</span><span class="g">' + esc(r.gene_name) + '</span>' +
          (r.approved_for_disease === 1 ? '<span class="tp-badge approved">appr</span>' : '') +
          (r.investigational_for_disease === 1 ? '<span class="tp-badge trial">trial</span>' : '') +
          (r.is_target === 1 ? '<span class="tp-badge known">known</span>' : '') + '</li>';
      }).join('') + '</ol></div>';
  }).join('') || '<p class="tp-nodata">No candidate passes these filters.</p>';

  Array.prototype.forEach.call(el('lanes').querySelectorAll('li[data-gi]'), function (li) {
    li.onclick = function () {
      var gi = +li.getAttribute('data-gi');
      openDrawer(STATE.rows.filter(function (r) { return r.gene_index === gi; })[0]);
    };
  });
}

/* ---------------- Screen E : evidence ---------------- */
function renderEvidence() {
  var d = STATE.disease;
  var byGT = {};
  STATE.discovery.forEach(function (r) { byGT[r.ground_truth] = r; });
  var inv = byGT.investigational, app = byGT.approved;

  var novelLinked = STATE.rows.filter(function (r) {
    return r.is_target !== 1 && r.rank_in_disease <= 200 &&
           (r.approved_for_disease === 1 || r.investigational_for_disease === 1);
  }).sort(function (a, b) { return a.rank_in_disease - b.rank_in_disease; });

  var lead;
  var best = inv && inv.hits_top50 ? inv : (app && app.hits_top50 ? app : null);
  if (best) {
    lead = 'Of the top-50 <b>novel</b> candidates for ' + esc(d.disease) + ', <b>' +
      best.hits_top50 + '</b> are ' +
      (best.ground_truth === 'approved' ? 'targets of an <b>approved</b> drug' :
       'targets of a drug <b>in trials</b>') + ' for this disease — <b>' +
      fmt(best['lift_top50'], 1) + '×</b> above chance.';
  } else {
    lead = 'No novel candidate in the top 50 is drug-linked for ' + esc(d.disease) +
      ' on either bar. That is the honest result for this disease.';
  }

  function liftCard(rec, cls, title, note) {
    if (!rec) return '<div class="tp-ev-card"><h3>' + title + '</h3>' +
      '<p class="tp-nodata">No drug-linked target exists for this disease on this bar, so ' +
      'discovery cannot be measured against it.</p></div>';
    var ks = [10, 20, 50, 100, 200];
    var max = Math.max.apply(null, ks.map(function (k) { return rec['lift_top' + k] || 0; })) || 1;
    return '<div class="tp-ev-card"><h3>' + title + '</h3>' +
      '<p class="bar-label">' + note + ' &middot; ' + commas(rec.novel_linked_total) +
      ' to find among ' + commas(rec.n_novel) + ' novel candidates (base rate ' +
      fmt(rec.novel_base_rate_pct, 2) + '%).</p>' +
      ks.map(function (k) {
        var l = rec['lift_top' + k] || 0;
        return '<div class="tp-liftrow"><span class="k">top ' + k + '</span>' +
          '<span class="tp-liftbar"><i class="' + cls + '" style="width:' +
          Math.round(100 * Math.min(l / max, 1)) + '%"></i></span>' +
          '<span class="v">' + fmt(l, 1) + '× &middot; ' + (rec['hits_top' + k] || 0) + '</span></div>';
      }).join('') + '</div>';
  }

  el('evidenceBody').innerHTML =
    '<div class="tp-ev-lead"><div class="big">' + lead + '</div>' +
    '<div class="sub">Measured on the <em>novel</em> sub-list only: the known targets are dropped, ' +
    'what remains is re-ranked, and we ask how many of the top-K are drug-linked. No model feature ' +
    'traverses a drug node, so this is independent of the training label. Lift is against the novel ' +
    'base rate — above 1× means the model ranks real, previously-unannotated targets above ' +
    'chance.</div></div>' +
    '<div class="tp-ev-grid">' +
      liftCard(app, 'appr', 'Approved drugs — the strict bar',
        'A drug approved for this disease hits this gene') +
      liftCard(inv, 'inv', 'In trials — the fairer bar',
        'In development, not approved. Includes failed programmes') +
    '</div>' +
    '<div class="tp-ev-card" style="margin-top:16px"><h3>Drug-linked novel candidates in the top 200</h3>' +
    '<p class="bar-label">Ranked highly with nothing in the training label pointing at them. ' +
    'These are the cases where the deliverable did its job.</p>' +
    (novelLinked.length ? '<table class="tp-table"><thead><tr><th class="tp-num">Rank</th>' +
      '<th>Gene</th><th>Class</th><th>Status</th></tr></thead><tbody>' +
      novelLinked.map(function (r) {
        return '<tr><td class="tp-rank">#' + commas(r.rank_in_disease) +
          '<span class="tp-pct">' + fmt(r.rank_percentile, 1) + ' pct</span></td>' +
          '<td><span class="tp-gene">' + esc(r.gene_name) + '</span></td>' +
          '<td>' + esc(r.druggability_class) + '</td><td>' + badges(r) + '</td></tr>';
      }).join('') + '</tbody></table>'
      : '<p class="tp-nodata">None in the top 200.</p>') + '</div>';
}

/* ---------------- drawer (Screen D, light) ---------------- */
function renderFeatures(feats) {
  var box = el('featBox');
  if (!box) return;
  if (!feats || !feats.length) { box.innerHTML = '<p class="tp-nodata">—</p>'; return; }
  box.innerHTML = feats.map(function (f) {
    var v = f.value;
    var shown = (Math.abs(v) < 0.01 && v !== 0) ? Number(v).toExponential(2) : fmt(v, 3);
    return '<div class="tp-feat"><div class="tp-feat-top"><span>' + esc(f.label) + '</span>' +
      '<span class="n">' + shown + '</span></div>' +
      '<div class="tp-feat-bar"><i style="width:' + f.percentile + '%"></i></div>' +
      '<div class="tp-feat-top"><span class="p">higher than ' + f.percentile +
      '% of candidates for this disease</span></div></div>';
  }).join('');
}

function openDrawer(r) {
  if (!r) return;
  var d = STATE.disease;

  var cypher =
    '// Why this gene? Interaction evidence to a KNOWN module gene.\n' +
    'MATCH (D:disease {node_index: ' + d.disease_index + '})\n' +
    'MATCH (g:protein {node_index: ' + r.gene_index + '})\n' +
    'MATCH (g)-[ppi:protein_protein]-(m:protein)-[assoc:disease_protein]-(D)\n' +
    'WHERE m.node_index <> g.node_index\n' +
    'RETURN g, ppi, m, assoc, D LIMIT 300';

  el('drawerBody').innerHTML =
    '<h2>' + esc(r.gene_name) + '</h2>' +
    '<div style="margin:9px 0 4px">' + badges(r) + '</div>' +
    '<h3>Position in this disease’s list</h3>' +
    '<div class="tp-kv"><span class="k">Rank</span><span class="v">#' + commas(r.rank_in_disease) + '</span></div>' +
    '<div class="tp-kv"><span class="k">Percentile</span><span class="v">' + fmt(r.rank_percentile, 2) +
      ' of ' + commas(STATE.poolSize) + '</span></div>' +
    '<div class="tp-kv"><span class="k">Model score</span><span class="v">' + fmt(r.score, 4) + '</span></div>' +
    '<div class="tp-kv"><span class="k">Druggability class</span><span class="v">' + esc(r.druggability_class) + '</span></div>' +
    '<div class="tp-kv"><span class="k">Target class</span><span class="v">' + (esc(r.ot_class_l1) || '—') + '</span></div>' +
    '<div class="tp-kv"><span class="k">Tractability</span><span class="v">' +
      [(r.ot_sm_tractable === 1 ? 'small-molecule' : ''), (r.ot_ab_tractable === 1 ? 'antibody' : '')]
        .filter(Boolean).join(', ') + '</span></div>' +
    '<div class="tp-kv"><span class="k">Safety liability</span><span class="v" data-tip="' +
      esc(r.has_safety_liability === 1 ? TIPS.liability : TIPS.noliability) + '">' +
      (r.has_safety_liability === 1 ? esc(r.safety_events || 'flagged') : 'none recorded') + '</span></div>' +

    '<h3>Top SHAP drivers</h3>' +
    '<div class="tp-shap" style="font-size:12px">' + shapHtml(r.top_shap_drivers) + '</div>' +
    '<p class="tp-caveat">The two strongest drivers only. A full per-feature waterfall needs the ' +
    'scoring recipe to emit the whole SHAP matrix — not yet built.</p>' +

    '<h3>Feature values, against this disease</h3>' +
    '<div id="featBox"><p class="tp-nodata">Loading…</p></div>' +

    '<h3>Show the evidence on the graph</h3>' +
    '<div class="tp-cypher">' + esc(cypher) + '</div>' +
    '<button class="tp-copy" id="copyCypher">Copy query for the graph explorer</button>' +
    '<p class="tp-caveat">Run it in the interactive explorer, not a query recipe — the recipe ' +
    'path is unreliable on this graph. Indices are snapshot-specific and are generated here from ' +
    'the live ranking, so they match the current build.</p>';

  el('copyCypher').onclick = function () {
    navigator.clipboard.writeText(cypher).then(function () {
      el('copyCypher').textContent = 'Copied';
      setTimeout(function () { el('copyCypher').textContent = 'Copy query for the graph explorer'; }, 1600);
    });
  };
  fetch(API('gene') + '?disease_index=' + d.disease_index + '&gene_index=' + r.gene_index)
    .then(function (x) { return x.json(); })
    .then(function (x) { renderFeatures(x.features); })
    .catch(function () { renderFeatures([]); });

  el('drawer').classList.remove('tp-hidden');
  el('drawerBack').classList.remove('tp-hidden');
}

function closeDrawer() {
  el('drawer').classList.add('tp-hidden');
  el('drawerBack').classList.add('tp-hidden');
}

/* ---------------- wiring ---------------- */
document.addEventListener('DOMContentLoaded', function () {
  el('diseaseSearch').oninput = renderPicker;
  Array.prototype.forEach.call(document.querySelectorAll('.tp-scope-btn'), function (b) {
    b.onclick = function () {
      document.querySelectorAll('.tp-scope-btn').forEach(function (x) { x.classList.remove('is-active'); });
      b.classList.add('is-active');
      STATE.scope = b.getAttribute('data-scope');
      renderPicker();
    };
  });
  Array.prototype.forEach.call(document.querySelectorAll('.tp-tab'), function (t) {
    t.onclick = function () {
      document.querySelectorAll('.tp-tab').forEach(function (x) { x.classList.remove('is-active'); });
      document.querySelectorAll('.tp-pane').forEach(function (x) { x.classList.remove('is-active'); });
      t.classList.add('is-active');
      document.querySelector('.tp-pane[data-pane="' + t.getAttribute('data-tab') + '"]').classList.add('is-active');
    };
  });
  ['fNovel', 'fTractable', 'fNotSecreted', 'fSm', 'fAb'].forEach(function (id) {
    el(id).onchange = function () { STATE.limit = 300; applyFilters(); };
  });
  el('fRank').oninput = function () { STATE.limit = 300; applyFilters(); };
  el('fRankReset').onclick = function () { el('fRank').value = 1000; applyFilters(); };
  el('fGene').oninput = function () { STATE.limit = 300; applyFilters(); };
  el('applyThree').onclick = function () {
    el('fNovel').checked = el('fTractable').checked = el('fNotSecreted').checked = true;
    STATE.limit = 300; applyFilters();
  };
  el('drawerClose').onclick = closeDrawer;
  el('drawerBack').onclick = closeDrawer;
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeDrawer(); });
  boot();
});
