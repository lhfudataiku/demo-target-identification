// Visual Graph conditional styling: propagate the Graph Editor's rules to the Graph Explorers, on this
// DSS instance or on another one. Written for Visual Graph plugin 1.6.0. See docs/graph/GRAPH_BUILDING.md §6.1.
//
// The plugin keeps the rules in the browser's localStorage, per DSS site, one key per webapp and graph.
// The Graph Editor in Part 1 is the only place rules are authored; every other key is a copy.
//
// Paste this whole file into the DevTools console on any page of the DSS instance, then:
//   vgStyling.status()                   reads only: each target key, whether it exists, its rule count
//   vgStyling.propagate()                dry run: what would be written from this browser's editor rules
//   vgStyling.propagate(null, true)      writes them into every Explorer target
//   vgStyling.exportBundle()             copies the editor rules (and state templates) to the clipboard
//   vgStyling.propagate(bundle)          dry run with a pasted bundle from another instance
//   vgStyling.propagate(bundle, true)    writes the bundle's rules into the editor and every Explorer
//   vgStyling.exportBundle(key)          recovery: bundle the rules of another key (an Explorer's) when
//                                        the editor lost them; then propagate(bundle, true) here
// Every write backs up the existing value first as `<key>.backup-<timestamp>`. Reload the webapps afterwards.
var vgStyling = (() => {
  // Configuration. When the graph moves to a new snapshot, change SNAPSHOT; when a webapp is added,
  // add it to EXPLORERS.
  const SNAPSHOT = 'j2B2cE'; // built graph the Explorers open; it is the last segment of their keys
  const EDITOR = { project: 'DEMO_KG_LS', webapp: 'lVWgU2m' };
  const EXPLORERS = [
    { project: 'DEMO_KG_LS', webapp: 'wBcApLN' },
    { project: 'DEMO_TARGET_IDENTIFICATION', webapp: 'wBcApLN' },
  ];

  const STATE = 'graph-visual-state:v1';
  const ED_PREFIX = `visual-graph-editor:${STATE}:${EDITOR.project}:${EDITOR.webapp}:`;
  const explorerKey = t => `visual-graph-explorer:${STATE}:${t.project}:${t.webapp}:${SNAPSHOT}`;
  const read = k => { try { return JSON.parse(localStorage.getItem(k)); } catch { return null; } };
  const rulesOf = v => v?.conditionalStylings || {};
  const count = v => Object.keys(rulesOf(v)).length;
  const liveKeys = () => Object.keys(localStorage).filter(k => k.startsWith('visual-graph-') && !k.includes('.backup-'));
  // The editor key ends with the editor's graph id, which only the plugin knows; find it by prefix.
  const localEditorKey = () => liveKeys().find(k => k.startsWith(ED_PREFIX)) || null;

  function status() {
    const edKey = localEditorKey();
    const rows = [
      { webapp: 'Graph Editor', key: edKey || `${ED_PREFIX}<not created yet>`, exists: !!edKey, rules: count(read(edKey)) },
      ...EXPLORERS.map(t => {
        const k = explorerKey(t);
        return { webapp: `Explorer ${t.project}`, key: k, exists: localStorage.getItem(k) !== null, rules: count(read(k)) };
      }),
    ];
    console.log(`Instance: ${location.host}`);
    console.table(rows);
    const others = liveKeys().filter(k => !rows.some(r => r.key === k));
    if (others.length) console.log('Other Visual Graph keys (not targets):', others);
    return rows;
  }

  // Source of truth on this instance: the editor's rules. Templates are full states used to create
  // a key that does not exist yet (the plugin writes a key only when it saves view state).
  // fromKey (recovery only): take the rules from another key, such as an Explorer's, when the
  // editor has lost them.
  function localSource(fromKey = null) {
    const edKey = localEditorKey();
    const ed = read(edKey);
    const from = fromKey ? read(fromKey) : ed;
    if (!from || !count(from)) throw new Error(fromKey ? `${fromKey} has no rules.` : 'The Graph Editor has no rules in this browser on this instance. Style the graph in the editor first, pass a bundle, or recover with exportBundle(<key that has rules>).');
    const explorerTemplate = EXPLORERS.map(t => read(explorerKey(t))).find(Boolean) || ed || from;
    return { editorKey: edKey, rules: rulesOf(from), editorState: ed || null, explorerState: explorerTemplate };
  }

  function exportBundle(fromKey = null) {
    const src = localSource(fromKey);
    const bundle = { format: 'vgStyling/1', from: location.host, snapshot: SNAPSHOT, at: new Date().toISOString(), ...src };
    const text = JSON.stringify(bundle);
    if (typeof copy === 'function') copy(text); // DevTools console helper
    console.log(`Bundle with ${Object.keys(src.rules).length} rule(s) from ${location.host} copied to the clipboard (${text.length} characters). On the other instance run vgStyling.propagate(<paste>).`);
    return bundle;
  }

  function propagate(bundle = null, apply = false) {
    if (typeof bundle === 'string') bundle = JSON.parse(bundle);
    if (bundle && bundle.format !== 'vgStyling/1') throw new Error('Not a vgStyling bundle: run vgStyling.exportBundle() on the source instance.');
    if (bundle && bundle.snapshot !== SNAPSHOT) throw new Error(`The bundle is for snapshot ${bundle.snapshot}, this script targets ${SNAPSHOT}. Group ids may differ; update SNAPSHOT deliberately.`);
    const src = bundle || localSource();
    const n = Object.keys(src.rules).length;
    if (!n) throw new Error('The source has no rules; refusing to overwrite targets with an empty set.');
    const same = v => JSON.stringify(rulesOf(v)) === JSON.stringify(src.rules);

    const targets = [];
    if (bundle) {
      // From another instance, the editor is a target too. Reuse its local key if the editor was opened
      // here; otherwise create it under the source's graph id (the editor's graph id is the
      // vg_internal_storage_ds graph_id, which a bundle deploy keeps).
      const edKey = localEditorKey() || bundle.editorKey;
      if (edKey && (read(edKey) || bundle.editorState)) targets.push({ key: edKey, template: bundle.editorState });
      else console.log('Skipping the Graph Editor: no editor key here or in the bundle. Open the editor once, then run again.');
    }
    EXPLORERS.forEach(t => targets.push({ key: explorerKey(t), template: src.explorerState }));

    const plan = targets.map(t => {
      const cur = read(t.key);
      return { ...t, cur, action: !cur ? 'create' : same(cur) ? 'unchanged' : 'update', before: count(cur) };
    });
    console.log(`${apply ? 'Writing' : 'Dry run:'} ${n} rule(s) from ${bundle ? `bundle (${bundle.from}, ${bundle.at})` : `this instance's editor`} on ${location.host}`);
    console.table(plan.map(({ key, action, before }) => ({ key, action, rulesBefore: before, rulesAfter: n })));
    if (!apply) { console.log(`Run vgStyling.propagate(${bundle ? 'bundle' : 'null'}, true) to write.`); return plan; }

    const stamp = Date.now();
    plan.filter(p => p.action !== 'unchanged').forEach(p => {
      if (p.cur) localStorage.setItem(`${p.key}.backup-${stamp}`, JSON.stringify(p.cur));
      const base = p.cur || { ...p.template, lastSavedQueryId: null };
      localStorage.setItem(p.key, JSON.stringify({ ...base, conditionalStylings: src.rules }));
    });
    console.log(`Done. Backups use suffix .backup-${stamp}. Reload the editor and the Explorers.`);
    return plan;
  }

  // Put back every key written in one run, from its backups. Keys that were created have no backup and
  // are left in place.
  function undo(stamp) {
    const suffix = `.backup-${stamp}`;
    const restored = Object.keys(localStorage).filter(k => k.endsWith(suffix)).map(k => {
      localStorage.setItem(k.slice(0, -suffix.length), localStorage.getItem(k));
      return k.slice(0, -suffix.length);
    });
    console.log(restored.length ? `Restored ${restored.length} key(s) from backup ${stamp}:` : `No backups with suffix ${suffix}.`, restored);
    return restored;
  }

  return { status, propagate, exportBundle, undo, config: { SNAPSHOT, EDITOR, EXPLORERS } };
})();
