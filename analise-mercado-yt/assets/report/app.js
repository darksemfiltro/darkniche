(function () {
  'use strict';
  const D = window.__DATA__;
  const app = document.getElementById('app');
  if (!D) { app.innerHTML = '<p class="empty-note">Sem dados: rode scripts/build_report.py.</p>'; return; }

  /* ---------------- utilidades ---------------- */
  const nf = new Intl.NumberFormat('pt-BR');
  const fmt = v => v == null || isNaN(v) ? '—' : v >= 1e9 ? (v / 1e9).toFixed(1).replace('.', ',') + ' bi' : v >= 1e6 ? (v / 1e6).toFixed(v >= 1e7 ? 0 : 1).replace('.', ',') + ' mi' : v >= 1e3 ? Math.round(v / 1e3) + ' mil' : String(Math.round(v));
  const pct = v => v == null ? '—' : Math.round(v * 100) + '%';
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const vurl = id => `https://www.youtube.com/watch?v=${encodeURIComponent(id)}`;
  const curl = id => `https://www.youtube.com/channel/${encodeURIComponent(id)}`;
  const safeUrl = href => { try { const u = new URL(String(href)); return ['http:', 'https:'].includes(u.protocol) ? u.href : null; } catch { return null; } };
  const a = (href, text, cls) => safeUrl(href) ? `<a class="ext ${cls || ''}" href="${esc(safeUrl(href))}" target="_blank" rel="noopener">${esc(text)}</a>` : esc(text);
  // Os campos editoriais aceitam ênfase, mas nenhum script, evento ou URL executável.
  const safeHtml = value => {
    const doc = new DOMParser().parseFromString(String(value || ''), 'text/html');
    const allowed = new Set(['B', 'STRONG', 'EM', 'I', 'BR', 'CODE', 'SPAN', 'MARK', 'A']);
    const clean = node => {
      if (node.nodeType === 3) return document.createTextNode(node.textContent);
      const fragment = document.createDocumentFragment();
      if (node.nodeType !== 1 || ['SCRIPT', 'STYLE', 'IFRAME', 'OBJECT', 'SVG', 'MATH'].includes(node.tagName)) return fragment;
      const out = allowed.has(node.tagName) ? document.createElement(node.tagName.toLowerCase()) : fragment;
      if (node.tagName === 'A' && safeUrl(node.getAttribute('href'))) {
        out.setAttribute('href', safeUrl(node.getAttribute('href')));
        out.setAttribute('target', '_blank'); out.setAttribute('rel', 'noopener noreferrer');
      }
      [...node.childNodes].forEach(child => out.appendChild(clean(child)));
      return out;
    };
    const root = document.createElement('div');
    [...doc.body.childNodes].forEach(child => root.appendChild(clean(child)));
    return root.innerHTML;
  };
  const vlink = (id, title) => id ? a(vurl(id), title || id) : esc(title);
  const clink = (id, name) => id ? a(curl(id), name || id) : esc(name);
  const dt = s => s ? String(s).slice(0, 10).split('-').reverse().join('/') : '—';
  const mins = s => s == null ? '—' : Math.round(s / 60) + ' min';
  const L = {}; (D.meta.languages || []).forEach(l => { L[l.lang] = l; });
  const langLabel = l => (L[l] && L[l].label) || (l || '?').toUpperCase();
  const tierOf = o => (o.computed && o.computed.tier) || o.tier || 'B';
  const store = { get(k, d) { try { const v = localStorage.getItem('amy:' + k); return v ? JSON.parse(v) : d; } catch (e) { return d; } },
                  set(k, v) { try { localStorage.setItem('amy:' + k, JSON.stringify(v)); } catch (e) {} } };

  const tip = document.getElementById('tip');
  function showTip(html, x, y) {
    tip.innerHTML = html; tip.style.opacity = 1;
    const r = tip.getBoundingClientRect(); let l = x + 14, t = y + 14;
    if (l + r.width > innerWidth - 8) l = x - r.width - 14; if (t + r.height > innerHeight - 8) t = y - r.height - 14;
    tip.style.left = Math.max(8, l) + 'px'; tip.style.top = Math.max(8, t) + 'px';
  }
  const hideTip = () => { tip.style.opacity = 0; };
  function bindTip(el, html) {
    el.addEventListener('mousemove', e => showTip(html, e.clientX, e.clientY));
    el.addEventListener('mouseleave', hideTip);
    el.addEventListener('focus', () => { const r = el.getBoundingClientRect(); showTip(html, r.right, r.top); });
    el.addEventListener('blur', hideTip);
  }
  const NS = 'http://www.w3.org/2000/svg';
  const mk = (tag, at, p) => { const e = document.createElementNS(NS, tag); for (const k in at) e.setAttribute(k, at[k]); if (p) p.appendChild(e); return e; };

  /* ---------------- estado dos filtros ---------------- */
  const allLangs = [...new Set([...(D.meta.languages || []).map(l => l.lang), ...(D.cells || []).map(c => c.lang)])];
  const S = { langs: new Set(store.get('langs', allLangs).filter(l => allLangs.includes(l))), tiers: new Set(store.get('tiers', ['S', 'A', 'B', 'C'])), q: '' };
  if (!S.langs.size) allLangs.forEach(l => S.langs.add(l));
  const renders = [];
  const onFilter = fn => { renders.push(fn); return fn; };
  const rerender = () => { store.set('langs', [...S.langs]); store.set('tiers', [...S.tiers]); renders.forEach(f => f()); };
  const qmatch = (...txt) => !S.q || txt.join(' ').toLowerCase().includes(S.q);

  function buildBar() {
    const fl = document.getElementById('f-langs'), ft = document.getElementById('f-tiers');
    fl.innerHTML = allLangs.map(l => `<button class="tog" data-l="${esc(l)}" aria-pressed="${S.langs.has(l)}">${esc(langLabel(l))}</button>`).join('') + '<button class="tog" data-l="*">todos</button>';
    ft.innerHTML = ['S', 'A', 'B', 'C'].map(t => `<button class="tog" data-t="${t}" aria-pressed="${S.tiers.has(t)}">${t}</button>`).join('');
    fl.onclick = e => { const b = e.target.closest('button'); if (!b) return; const l = b.dataset.l;
      if (l === '*') { const all = S.langs.size === allLangs.length; S.langs.clear(); if (!all) allLangs.forEach(x => S.langs.add(x)); else S.langs.add(allLangs[0]); }
      else if (S.langs.has(l) && S.langs.size > 1) S.langs.delete(l); else S.langs.add(l);
      fl.querySelectorAll('[data-l]').forEach(x => x.dataset.l !== '*' && x.setAttribute('aria-pressed', S.langs.has(x.dataset.l))); rerender(); };
    ft.onclick = e => { const b = e.target.closest('button'); if (!b) return; const t = b.dataset.t;
      if (S.tiers.has(t) && S.tiers.size > 1) S.tiers.delete(t); else S.tiers.add(t); b.setAttribute('aria-pressed', S.tiers.has(t)); rerender(); };
    let tmr; document.getElementById('f-q').oninput = e => { clearTimeout(tmr); tmr = setTimeout(() => { S.q = e.target.value.trim().toLowerCase(); rerender(); }, 160); };
  }

  /* ---------------- tabelas ordenáveis ---------------- */
  function table(host, cols, getRows, opt = {}) {
    let sortKey = opt.sort || null, dir = opt.dir || -1, limit = opt.limit || 0, shown = limit;
    function draw() {
      let rows = getRows();
      if (sortKey) { const c = cols.find(c => c.key === sortKey); const sv = c.sv || (r => r[sortKey]);
        rows = rows.slice().sort((x, y) => { const p = sv(x), q = sv(y); return (p == null) - (q == null) || (p < q ? -dir : p > q ? dir : 0); }); }
      const total = rows.length; if (limit) rows = rows.slice(0, shown);
      host.innerHTML = `<div class="tbl"><table><thead><tr>${cols.map(c => `<th class="${c.r ? 'r ' : ''}${c.cls ? c.cls + ' ' : ''}${c.nosort ? '' : 'sort'}" data-k="${c.key}" ${sortKey === c.key ? `aria-sort="${dir > 0 ? 'ascending' : 'descending'}"` : ''} scope="col" ${c.nosort ? '' : 'tabindex="0"'}>${esc(c.label)}</th>`).join('')}</tr></thead><tbody>${
        rows.map(r => `<tr>${cols.map(c => `<td class="${c.r ? 'r' : ''}${c.cls ? ' ' + c.cls : ''}">${c.f ? c.f(r) : esc(r[c.key])}</td>`).join('')}</tr>`).join('') || `<tr><td colspan="${cols.length}" class="small">Nada com os filtros atuais.</td></tr>`
      }</tbody></table></div>${limit && total > shown ? `<button class="tog more">mostrar mais (${total - shown})</button>` : ''}<p class="small">${total} linha(s)</p>`;
      host.querySelectorAll('th.sort').forEach(th => { th.onclick = () => { const k = th.dataset.k; dir = sortKey === k ? -dir : -1; sortKey = k; draw(); };
        th.onkeydown = e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); th.click(); } }; });
      const m = host.querySelector('.more'); if (m) m.onclick = () => { shown += limit; draw(); };
    }
    draw(); return draw;
  }

  /* ---------------- seções ---------------- */
  const sections = [];
  function section(id, eyebrow, title, html) {
    const s = document.createElement('section'); s.id = id;
    s.innerHTML = `<p class="eyebrow">${String(sections.length).padStart(2, '0')} · ${esc(eyebrow)}</p><h2>${esc(title)}</h2>${html || ''}`;
    app.appendChild(s); sections.push({ id, eyebrow }); return s;
  }
  const list = (items, cls) => items && items.length ? `<ul class="${cls || ''}">${items.map(i => `<li>${typeof i === 'string' ? safeHtml(i) : (i.title ? `<strong>${esc(i.title)}</strong> ` : '') + (i.html ? safeHtml(i.html) : esc(i.text || ''))}</li>`).join('')}</ul>` : '';
  const evHref = e => e.url || (e.video ? vurl(e.video) : e.channel ? curl(e.channel) : e.id ? (/^UC/.test(e.id) ? curl(e.id) : vurl(e.id)) : null);
  const ev = evs => evs && evs.length ? `<ul class="small">${evs.map(e => `<li>${evHref(e) ? a(evHref(e), e.text || evHref(e)) : esc(e.text)}${e.views ? ` <span class="small">${fmt(e.views)}</span>` : ''}${e.note ? ` <span class="small">· ${esc(e.note)}</span>` : ''}${e.accessed ? ` <span class="small">· acesso ${dt(e.accessed)}</span>` : ''}</li>`).join('')}</ul>` : '';

  app.innerHTML = '';
  /* HERO */
  const m = D.meta;
  const hero = document.createElement('section'); hero.className = 'hero'; hero.id = 'topo';
  hero.innerHTML = `${m.stamp ? `<span class="stamp">${esc(m.stamp)}</span>` : ''}<p class="eyebrow">Análise de mercado · ${esc(m.reference ? m.reference.label : 'nicho ou ideia')}</p>
    <h1>${m.title_html ? safeHtml(m.title_html) : esc(m.title)}</h1>
    <div class="meta">${[`Coleta: ${m.data_stamp && String(m.data_stamp).slice(0, 10) !== String(m.date || '').slice(0, 10) ? `${dt(m.date)} a ${dt(m.data_stamp)}` : dt(m.data_stamp || m.date)}${m.data_stamp ? ` · dado mais recente: ${dt(m.data_stamp)} ${esc(String(m.data_stamp).slice(11, 16))} UTC` : ''}`, m.reference && m.reference.url ? a(m.reference.url, 'referência') : '', `${allLangs.length} idiomas`, `${(D.cells || []).length} células nicho×idioma`, `${(D.channels || []).length} canais perfilados`, m.quota ? `uso local: ${nf.format(m.quota.units)} unidades gerais + ${m.quota.searches} buscas` : ''].filter(Boolean).map(x => `<span>${x}</span>`).join('')}</div>
    ${D.summary && D.summary.lead ? `<p class="lead">${safeHtml(D.summary.lead)}</p>` : ''}`;
  app.appendChild(hero);

  /* 00 RESUMO + RANKING + QUADRANTE */
  const opps = D.opportunities || [];
  const technical = D.meta && D.meta.analysis_mode === 'technical';

  /* VEREDITO: a resposta curta antes de qualquer tabela */
  const VERD = { GO: ['ok', 'vale executar'], TESTAR: ['warn', 'teste barato antes de investir'], EVITAR: ['bad', 'não vale como está'] };
  const verdOf = o => (o.computed && o.computed.verdict) || null;
  const vchip = v => v && VERD[v] ? `<span class="chip vb ${VERD[v][0]}">${v}</span>` : '';
  const AXN = { D: 'demanda', L: 'lacuna de oferta', F: 'fit cultural', G: 'formato' };
  const topV = technical ? [] : opps.filter(verdOf).slice(0, 3);
  if (topV.length) {
    const first = (D.plan || [])[0];
    section('veredito', 'Veredito', 'Resultado por oportunidade',
      `${D.summary && D.summary.verdict_text ? `<p class="lead">${safeHtml(D.summary.verdict_text)}</p>` : ''}
       <div class="vcards">${topV.map(o => { const c = o.computed;
        return `<article class="vcard v-${VERD[c.verdict][0]}"><div class="vhead">${vchip(c.verdict)}<span class="vsub">${esc(VERD[c.verdict][1])}</span></div>
          <h3><a href="#op-${esc(o.id)}">${esc(o.name)}</a></h3>
          <p class="mk">${esc(langLabel(o.lang))}${o.markets ? ' · ' + esc(o.markets) : ''} · tier ${c.tier} · nota <b>${c.total}</b> <span class="small">(faixa ${c.range[0]}–${c.range[1]})</span> · confiança <b>${esc(c.confidence)}</b></p>
          ${o.oneliner ? `<p class="why">${esc(o.oneliner)}</p>` : ''}
          <ul class="small">${(c.reasons || []).map(r => `<li>${esc(r)}</li>`).join('')}</ul>
          ${c.missing && c.missing.length ? `<p class="small"><strong>${c.verdict === 'GO' ? 'Ainda julgado (confirme no primeiro mês)' : 'Medir antes de decidir'}:</strong> ${c.missing.map(x => esc(AXN[x.axis] || x.axis)).join(', ')}.</p>` : ''}</article>`; }).join('')}</div>
       ${first ? `<p class="small"><strong>Próximo passo:</strong> ${esc(first.what)}${first.success ? ' · sucesso: ' + esc(first.success) : ''}</p>` : ''}
       <p class="small">GO: tier S ou A, no máximo metade dos eixos do oceano sem medição, risco abaixo de 4 e confiança média ou alta. TESTAR: promissor, mas falta medir ou o risco pede teste pequeno. EVITAR: demanda vazia, mar vermelho sem formato diferente, tema que não conversa com o mercado ou risco proibitivo. A faixa mostra a nota se cada eixo ainda julgado estivesse 1 ponto pior ou melhor.</p>`);
  }
  const s0 = section('resumo', technical ? 'Resumo dos dados · sem IA' : 'Resumo e ranking', 'O que importa',
    `${D.summary && D.summary.findings ? `<ol class="findings">${D.summary.findings.map(f => `<li><p>${typeof f === 'string' ? safeHtml(f) : `<strong>${esc(f.title)}</strong> ${f.html ? safeHtml(f.html) : esc(f.text)}`}</p></li>`).join('')}</ol>` : ''}
     <div ${technical ? 'hidden' : ''}><h3>Ranking de oportunidades</h3><div id="rank"></div></div>
     <h3>${technical ? 'Mediana versus canais ativos na amostra' : 'Quadrante oceano azul'}</h3>
     <div class="legend" aria-hidden="true" ${technical ? 'hidden' : ''}><span><i style="background:var(--viz-axis);opacity:.5"></i>célula nicho × idioma</span><span><i style="background:var(--tier-s)"></i>oportunidade S</span><span><i style="background:var(--tier-a)"></i>A</span><span><i style="background:var(--tier-b)"></i>B/C</span></div>
     <div class="fig"><div class="chart" id="quad" role="img" aria-label="Demanda (mediana de views) versus concorrência (canais nativos ativos) por célula"></div>
     <p class="cap">${technical ? 'Cada ponto descreve uma célula nicho × idioma da amostra. A posição no gráfico não valida uma oportunidade. Mediana de views no eixo vertical; canais ativos observados no horizontal. Passe o mouse para ver detalhes.' : 'Cada ponto é uma célula nicho × idioma. Eixo vertical: ritmo de views por dia dos vídeos maduros do topo, em equivalente EN (log); sem datas, a mediana de views. Eixo horizontal: canais nativos ativos no topo da busca (invertido: à direita há menos concorrência). O canto superior direito é o oceano azul. Passe o mouse para ver detalhes; os filtros do topo valem aqui.'}</p></div>`);
  const rankDraw = onFilter(table(s0.querySelector('#rank'), [
    { key: 'tier', label: 'Tier', f: o => `<span class="chip ${tierOf(o)}">${tierOf(o)}</span>${o.computed && o.computed.caps && o.computed.caps.length ? `<br><span class="small capnote" title="${esc(o.computed.caps.join(' · '))}">${o.computed.caps.some(c => /incerteza/.test(c)) ? 'validar' : 'trava'}</span>` : ''}`, sv: o => -'SABC'.indexOf(tierOf(o)) * 1000 + ((o.computed && o.computed.total) || 0) },
    { key: 'verdict', label: 'Veredito', sv: o => ({ GO: 3, TESTAR: 2, EVITAR: 1 })[verdOf(o)] || 0, f: o => vchip(verdOf(o)) + (o.computed && o.computed.confidence ? `<br><span class="small">conf. ${esc(o.computed.confidence)}</span>` : '') },
    { key: 'name', label: 'Oportunidade', f: o => `<a href="#op-${esc(o.id)}">${esc(o.name)}</a>${o.computed && o.computed.blue_ocean ? ' <span class="chip ok">oceano azul</span>' : ''}` },
    { key: 'lang', label: 'Idioma', f: o => esc(langLabel(o.lang)) },
    { key: 'bend', label: 'Bend', cls: 'hide-sm', f: o => esc(o.bend && (o.bend.label || o.bend.type) || '') },
    { key: 'O', label: 'Oceano', r: 1, sv: o => o.computed && o.computed.O, f: o => o.computed ? o.computed.O.toFixed(1).replace('.', ',') : '—' },
    { key: 'P', label: 'Produção', r: 1, sv: o => o.computed && o.computed.P, f: o => o.computed ? o.computed.P.toFixed(1).replace('.', ',') : '—' },
    { key: 'total', label: 'Nota', r: 1, sv: o => o.computed && o.computed.total, f: o => `<span class="bar-in" style="width:${Math.round((o.computed ? o.computed.total : 0) / 2)}px"></span>${o.computed ? o.computed.total + (o.computed.range ? ` <span class="small">(${o.computed.range[0]}–${o.computed.range[1]})</span>` : '') : '—'}` },
    { key: 'why', label: 'Em uma linha', nosort: 1, cls: 'hide-sm w-txt', f: o => esc(o.oneliner || '') },
  ], () => opps.filter(o => S.tiers.has(tierOf(o)) && (!o.lang || S.langs.has(o.lang) || o.lang === 'multi') && qmatch(o.name, o.oneliner, o.lens, o.domain)), { sort: 'tier' }));

  function quad() {
    const host = s0.querySelector('#quad'); host.innerHTML = '';
    const cells = (D.cells || []).filter(c => S.langs.has(c.lang) && c.m && c.m.n_long >= 3 && qmatch(c.label, c.id));
    if (!cells.length) { host.innerHTML = '<p class="empty-note">Sem células com dados suficientes nos filtros.</p>'; return; }
    const W = 900, H = 420, mg = { l: 62, r: 24, t: 18, b: 44 };
    const svg = mk('svg', { viewBox: `0 0 ${W} ${H}`, role: 'group', 'aria-label': 'Quadrante: demanda por canais ativos, um ponto por célula nicho × idioma (use Tab e Enter)' }, host);
    const maxA = Math.max(4, ...cells.map(c => c.m.active));
    const x = act => mg.l + (1 - Math.log1p(act) / Math.log1p(maxA)) * (W - mg.l - mg.r);
    // eixo vertical: ritmo (views/dia equivalente EN) quando todas as células têm datas; senão, a mediana de views
    const byRate = cells.every(c => c.auto && Number.isFinite(c.auto.vpd_en_equiv));
    const demand = c => byRate ? c.auto.vpd_en_equiv : c.auto && Number.isFinite(c.auto.med_en_equiv) ? c.auto.med_en_equiv : c.m.med;
    const floor = byRate ? 3 : 100, ticks = byRate ? [1, 10, 100, 1e3, 1e4, 1e5] : [100, 1e3, 1e4, 1e5, 1e6, 1e7];
    const vmax = Math.max(byRate ? 100 : 1e4, ...cells.map(demand)); const y0 = Math.log10(floor), y1 = Math.log10(vmax) + 0.1;
    const y = v => mg.t + (1 - (Math.log10(Math.max(v, floor)) - y0) / (y1 - y0)) * (H - mg.t - mg.b);
    ticks.filter(v => v >= floor && v <= Math.pow(10, y1)).forEach(v => { mk('line', { x1: mg.l, x2: W - mg.r, y1: y(v), y2: y(v), class: 'grid' }, svg); const t = mk('text', { x: mg.l - 8, y: y(v) + 4, 'text-anchor': 'end' }, svg); t.textContent = fmt(v); });
    [0, 1, 2, 5, 10, 20, 40].filter(v => v <= maxA).forEach(v => { const t = mk('text', { x: x(v), y: H - mg.b + 18, 'text-anchor': 'middle' }, svg); t.textContent = v; });
    const tx = mk('text', { x: W - mg.r, y: H - 6, 'text-anchor': 'end' }, svg); tx.textContent = 'canais nativos ativos (menos → à direita)';
    const meds = cells.map(demand).sort((p, q) => p - q), acts = cells.map(c => c.m.active).sort((p, q) => p - q);
    const my = y(meds[Math.floor(meds.length / 2)]), mx = x(acts[Math.floor(acts.length / 2)]);
    mk('line', { x1: mx, x2: mx, y1: mg.t, y2: H - mg.b, stroke: 'var(--viz-axis)', 'stroke-dasharray': '3 4' }, svg);
    mk('line', { x1: mg.l, x2: W - mg.r, y1: my, y2: my, stroke: 'var(--viz-axis)', 'stroke-dasharray': '3 4' }, svg);
    const ql = mk('text', { x: W - mg.r - 4, y: mg.t + 12, 'text-anchor': 'end', class: 'lbl' }, svg); ql.textContent = 'OCEANO AZUL · ' + (byRate ? 'views/dia equivalente EN' : 'demanda equivalente EN');
    const qr = mk('text', { x: mg.l + 6, y: mg.t + 12, 'text-anchor': 'start' }, svg); qr.textContent = 'mar vermelho';
    const labels = [], dots = [];
    const opByCell = {}; opps.forEach(o => (o.cells || []).forEach(k => { (opByCell[k] = opByCell[k] || []).push(o); }));
    cells.forEach((c, i) => {
      const jit = ((i * 37) % 11 - 5) * 1.6;
      const cx = x(c.m.active) + jit, cy = y(demand(c));
      const key = `${c.id}__${c.lang}`, ops = (opByCell[key] || []).filter(o => S.tiers.has(tierOf(o)));
      const t = ops.length ? tierOf(ops[0]) : null;
      const col = t === 'S' ? 'var(--tier-s)' : t === 'A' ? 'var(--tier-a)' : t ? 'var(--tier-b)' : 'var(--viz-axis)';
      const dot = mk('circle', { cx, cy, r: ops.length ? 7 : 4.5, fill: col, 'fill-opacity': ops.length ? 1 : .45, stroke: 'var(--viz-surface)', 'stroke-width': 2, tabindex: 0, role: 'button', 'aria-label': `${c.label}, ${langLabel(c.lang)}: ${c.m.active} canais ativos, mediana ${fmt(c.m.med)} views${ops.length ? ', oportunidade ' + ops.map(o => o.name).join(', ') : ''}` }, svg);
      bindTip(dot, `<b>${esc(c.label)} · ${esc(langLabel(c.lang))}</b><br>mediana ${nf.format(c.m.med)} · ritmo ${c.m.vpd_p50 == null ? '—' : nf.format(c.m.vpd_p50) + ' views/dia'} · ≥100 mil: ${c.m.k100}<br>ativos ${c.m.active} (efetivos ${c.m.n_eff == null ? '—' : String(c.m.n_eff).replace('.', ',')}) · pureza ${pct(c.m.lang_purity)} · frescos ${pct(c.m.fresh_share)}${ops.length ? '<br>' + ops.map(o => `${tierOf(o)} · ${esc(o.name)}`).join('<br>') : ''}`);
      dot.addEventListener('click', () => openCell(c));
      dot.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openCell(c); } });
      if (ops.length) labels.push({ cx, cy, text: `${ops[0].name} · ${c.lang}`, must: 'SA'.includes(tierOf(ops[0])) });
      if (ops.length) dots.push({ x: cx - 8, y: cy - 8, w: 16, h: 16 });
    });
    // rótulos sem sobreposição: tenta direita, esquerda, acima e abaixo do ponto; fica com a primeira posição livre
    const boxes = dots.slice(), cw = 6.7, lh = 13;
    labels.sort((p, q) => (q.must - p.must) || (p.cy - q.cy)).forEach(L0 => {
      const w = L0.text.length * cw;
      const cand = [[10, 4], [-10 - w, 4], [-w / 2, -12], [-w / 2, 18], [10, -10], [10, 18], [-10 - w, -10], [-10 - w, 18]];
      let pick = null;
      for (const [dx, dy] of cand) {
        const bx = L0.cx + dx, by = L0.cy + dy - lh + 3;
        if (bx < mg.l || bx + w > W - mg.r + 4 || by < 0 || by + lh > H - mg.b) continue;
        if (!boxes.some(b => bx < b.x + b.w && bx + w > b.x && by < b.y + b.h && by + lh > b.y)) { pick = { x: bx, y: by, w, h: lh, tx: L0.cx + dx, ty: L0.cy + dy }; break; }
      }
      if (!pick && !L0.must) return;  // sem espaço: o rótulo fica só na dica (passe o mouse no ponto)
      if (!pick) { const dx = L0.cx + 10 + w > W - mg.r ? -10 - w : 10; pick = { x: L0.cx + dx, y: L0.cy - 9, w, h: lh, tx: L0.cx + dx, ty: L0.cy + 4 }; }
      boxes.push(pick);
      const tl = mk('text', { x: pick.tx, y: pick.ty, class: 'lbl' }, svg); tl.textContent = L0.text;
    });
  }
  onFilter(quad)();

  /* comentários (referência ou modo ideia) */
  function renderComments(host, Rx) {
      const rows = Object.entries(Rx.comments).map(([id, c]) => ({ id, ...c, title: c.title || ((Rx.timeline || []).find(v => v.id === id) || {}).title || id }));
      host.innerHTML = `<div class="tbl"><table><thead><tr><th>Vídeo</th><th class="r">Lidos</th><th class="r">% políticos</th><th class="r">% curtidas políticas</th><th class="r">% elogio ao formato</th><th class="r">Pedidos de pauta</th></tr></thead><tbody>${rows.map(r => `<tr><td>${vlink(r.id, r.title)}</td><td class="r">${r.n}</td><td class="r">${pct(r.political_share)}</td><td class="r"><span class="bar-in" style="width:${Math.round(r.political_like_share * 70)}px"></span>${pct(r.political_like_share)}</td><td class="r">${pct(r.format_praise_share)}</td><td class="r">${r.request_count}</td></tr>`).join('')}</tbody></table></div>
        <div class="cols">${rows.slice(0, 4).map(r => `<div><h4>${vlink(r.id, r.title)}</h4>${(r.top || []).slice(0, 3).map(q => `<p class="quote">${esc(q.text)}<span class="who">${nf.format(q.likes)} curtidas</span></p>`).join('')}${(r.requests || []).length ? `<p class="small"><strong>Pedidos:</strong> ${r.requests.slice(0, 3).map(q => esc(q.text.slice(0, 120))).join(' · ')}</p>` : ''}</div>`).join('')}</div>`;
  }

  /* 01 REFERÊNCIA */
  const R = D.reference;
  if (R && !R.channel && (R.format_vector || R.script_blocks || R.comments || R.examples)) {
    section('referencia', 'Ponto de partida', R.title || 'A ideia decomposta', `${R.notes_html ? `<p>${safeHtml(R.notes_html)}</p>` : ''}
      ${R.format_vector ? `<h3>Vetor de formato</h3><div class="tbl"><table><thead><tr><th>Variável</th><th>Na ideia</th><th>Trocas possíveis (bends)</th></tr></thead><tbody>${R.format_vector.map(v => `<tr><td><strong>${esc(v.var)}</strong></td><td>${esc(v.value)}</td><td>${esc(v.swaps || '')}</td></tr>`).join('')}</tbody></table></div>` : ''}
      ${R.examples && R.examples.length ? `<h3>Exemplos que inspiraram</h3>${ev(R.examples)}` : ''}
      ${R.gallery ? `<div class="gallery">${R.gallery.map(g => `<figure><img src="${esc(g.src)}" alt="${esc(g.caption || '')}" loading="lazy"><figcaption>${esc(g.caption || '')}</figcaption></figure>`).join('')}</div>` : ''}
      ${R.comments ? `<h3>O que o público diz</h3><div id="idea-com"></div>` : ''}`);
    if (R.comments) renderComments(document.getElementById('idea-com'), R);
  }
  if (R && R.channel) {
    const ch = R.channel, pv = R.pivot;
    const s1 = section('referencia', 'Raio-X da referência', ch.title,
      `<p>${clink(ch.id, ch.title)} ${ch.handle ? `<span class="small">${esc(ch.handle)}</span>` : ''} · ${esc(ch.country || '—')} · conta criada em ${dt(ch.created)}. ${safeHtml(R.notes_html)}</p>
       <div class="tiles">
        <div class="tile"><div class="k">Inscritos</div><div class="v">${fmt(ch.subs)}</div><div class="d">${nf.format(ch.videos)} vídeos</div></div>
        <div class="tile"><div class="k">Views totais</div><div class="v">${fmt(ch.views)}</div><div class="d">top 3 = ${pct(R.top3_share)}</div></div>
        <div class="tile"><div class="k">Mediana long-form</div><div class="v">${fmt(R.median_long)}</div><div class="d">todos os vídeos com mais de 3 min</div></div>
        ${pv ? `<div class="tile hl"><div class="k">Pivô${pv.strength === 'fraco' ? ' fraco' : ''} · ${dt(pv.date)}</div><div class="v">×${String(pv.factor).replace('.', ',')}</div><div class="d">${fmt(pv.median_before)} → ${fmt(pv.median_after)} views</div></div>` : ''}
       </div>
       <div class="fig"><div class="chart" id="ref-tl" role="img" aria-label="Views por vídeo da referência ao longo do tempo"></div>
       <p class="cap">Views por vídeo (log) por data. ${pv ? `Linha tracejada: pivô detectado em ${dt(pv.date)} (“${esc(pv.first_title)}”), duração mediana ${pv.dur_before_min} → ${pv.dur_after_min} min.${pv.strength === 'fraco' ? ' Pivô fraco: as faixas de views dos dois lados se sobrepõem, então pode ser ruído.' : ''}` : ''} Clique num ponto para abrir o vídeo.</p></div>
       <h3>Vídeos de maior destaque</h3><div id="ref-top"></div>
       ${R.format_vector ? `<h3>Vetor de formato</h3><div class="tbl"><table><thead><tr><th>Variável</th><th>Na referência</th><th>Trocas possíveis (bends)</th></tr></thead><tbody>${R.format_vector.map(v => `<tr><td><strong>${esc(v.var)}</strong></td><td>${esc(v.value)}</td><td>${esc(v.swaps || '')}</td></tr>`).join('')}</tbody></table></div>` : ''}
       ${R.script_blocks ? `<h3>Anatomia do roteiro</h3><p class="small">${R.script_source ? 'Vídeo: ' + vlink(R.script_source.id, R.script_source.title) : ''}</p><div class="chart"><div class="anat">${(() => { const tot = R.script_blocks.reduce((s, b) => s + (b.end - b.start), 0) || 1; return R.script_blocks.map(b => `<div class="k-${esc(b.kind || 'didatico')}" style="width:${((b.end - b.start) / tot * 100).toFixed(2)}%" title="${esc(b.label)} · ${Math.floor(b.start / 60)}:${String(b.start % 60).padStart(2, '0')}">${(b.end - b.start) / tot > 0.06 ? esc(b.label) : ''}</div>`).join(''); })()}</div></div>
         <div class="tbl"><table><thead><tr><th>Bloco</th><th>Tempo</th><th>Como é feito</th></tr></thead><tbody>${R.script_blocks.map(b => `<tr><td><strong>${esc(b.label)}</strong></td><td class="r">${Math.floor(b.start / 60)}:${String(b.start % 60).padStart(2, '0')}–${Math.floor(b.end / 60)}:${String(b.end % 60).padStart(2, '0')}</td><td>${esc(b.note || '')}</td></tr>`).join('')}</tbody></table></div>` : ''}
       ${R.palette || R.motion || R.gallery ? `<h3>Identidade visual e motion</h3><div class="cols"><div>${R.palette ? `<h4>Paleta</h4><div class="sw-row">${R.palette.map(p => `<div><span style="background:${esc(p.hex)}"></span>${esc(p.label || p.hex)}</div>`).join('')}</div>` : ''}${R.aesthetic_notes ? list(R.aesthetic_notes.map(esc)) : ''}</div><div>${R.motion ? `<h4>Gramática do motion</h4><ol>${R.motion.map(x => `<li>${esc(x)}</li>`).join('')}</ol>` : ''}</div></div>
         ${R.gallery ? `<div class="gallery">${R.gallery.map(g => `<figure><img src="${esc(g.src)}" alt="${esc(g.caption || '')}" loading="lazy"><figcaption>${esc(g.caption || '')}</figcaption></figure>`).join('')}</div>` : ''}` : ''}
       ${R.comments ? `<h3>O que o público diz</h3><div id="ref-com"></div>` : ''}`);
    // linha do tempo
    (function () {
      const host = s1.querySelector('#ref-tl'); const tl = R.timeline || []; if (!tl.length) return;
      const W = 900, H = 320, mg = { l: 58, r: 20, t: 16, b: 34 };
      const svg = mk('svg', { viewBox: `0 0 ${W} ${H}`, 'aria-hidden': 'true' }, host);
      const t0 = Date.parse(tl[0].date) - 864e5 * 10, t1 = Date.parse(tl[tl.length - 1].date) + 864e5 * 10;
      const x = d => mg.l + (Date.parse(d) - t0) / (t1 - t0) * (W - mg.l - mg.r);
      const vmax = Math.max(1e3, ...tl.map(v => v.views)); const y0 = Math.max(1, Math.floor(Math.log10(Math.max(10, Math.min(...tl.map(v => v.views || 10)))))), y1 = Math.log10(vmax) + 0.1;
      const y = v => mg.t + (1 - (Math.log10(Math.max(v, Math.pow(10, y0))) - y0) / (y1 - y0)) * (H - mg.t - mg.b);
      for (let e = y0; e <= Math.ceil(y1); e++) { const v = Math.pow(10, e); if (v > Math.pow(10, y1)) break; mk('line', { x1: mg.l, x2: W - mg.r, y1: y(v), y2: y(v), class: 'grid' }, svg); const t = mk('text', { x: mg.l - 8, y: y(v) + 4, 'text-anchor': 'end' }, svg); t.textContent = fmt(v); }
      const nt = 6; for (let i = 0; i <= nt; i++) { const tt = t0 + (t1 - t0) * i / nt; const t = mk('text', { x: x(new Date(tt).toISOString()), y: H - 10, 'text-anchor': 'middle' }, svg); t.textContent = new Date(tt).toISOString().slice(2, 7).replace('-', '/'); }
      if (pv) { mk('line', { x1: x(pv.date), x2: x(pv.date), y1: mg.t, y2: H - mg.b, stroke: 'var(--accent)', 'stroke-dasharray': '4 4' }, svg); }
      const phases = R.phases || [{ key: 'antes', label: 'antes do pivô' }, { key: 'depois', label: 'depois do pivô' }, { key: 'único', label: 'vídeos' }];
      const pc = {}; phases.forEach((p, i) => { pc[p.key] = p.color || ['var(--s1)', 'var(--s3)', 'var(--s2)'][i % 3]; });
      tl.forEach(v => { const c = mk('circle', { cx: x(v.date), cy: y(v.views), r: 5, fill: pc[v.phase] || 'var(--s1)', stroke: 'var(--viz-surface)', 'stroke-width': 1.5, tabindex: 0, style: 'cursor:pointer' }, svg);
        bindTip(c, `<b>${esc(v.title)}</b><br>${dt(v.date)} · ${mins(v.dur)} · ${nf.format(v.views)} views`); c.addEventListener('click', () => window.open(vurl(v.id), '_blank', 'noopener')); });
      host.insertAdjacentHTML('beforebegin', `<div class="legend">${phases.filter(p => tl.some(v => v.phase === p.key)).map(p => `<span><i style="background:${pc[p.key]}"></i>${esc(p.label)}</span>`).join('')}</div>`);
    })();
    table(s1.querySelector('#ref-top'), [
      { key: 'title', label: 'Vídeo', cls: 'w-name', f: v => vlink(v.id, v.title) }, { key: 'date', label: 'Data', f: v => dt(v.date) },
      { key: 'dur', label: 'Dur.', r: 1, f: v => mins(v.dur) }, { key: 'views', label: 'Views', r: 1, f: v => nf.format(v.views) },
      { key: 'vpd', label: 'Views/dia', r: 1, f: v => nf.format(v.vpd || 0) }, { key: 'likes', label: 'Likes/views', r: 1, sv: v => v.likes / Math.max(1, v.views), f: v => pct(v.likes / Math.max(1, v.views)) },
      { key: 'desc_links', label: 'Links na desc.', r: 1 },
    ], () => (R.timeline || []).filter(v => qmatch(v.title)), { sort: 'views', limit: 12 });
    if (R.comments) renderComments(s1.querySelector('#ref-com'), R);
  }

  /* 02 BENDS */
  if (D.bends && D.bends.length) {
    const s2 = section('bends', 'Nichebending', 'Variações geradas', `<p>Cada linha troca uma variável do formato original e mantém o resto, para que o resultado seja atribuível. As células da varredura (seção seguinte) saem daqui.</p><div id="bends"></div>`);
    table(s2.querySelector('#bends'), [
      { key: 'axis', label: 'Eixo' }, { key: 'from', label: 'De' }, { key: 'to', label: 'Para', f: b => `<strong>${esc(b.to)}</strong>` },
      { key: 'cells', label: 'Células', nosort: 1, f: b => esc((b.cells || []).join(', ')) }, { key: 'note', label: 'Por quê', nosort: 1 },
    ], () => D.bends.filter(b => qmatch(b.axis, b.from, b.to, b.note)));
  }

  /* 03 MAPA DE MERCADO */
  const METRICS = [
    { k: 'med', label: 'Mediana long-form', get: c => c.m.med, bins: [1e3, 5e3, 2e4, 6e4, 1.5e5, 5e5], f: v => fmt(v) },
    { k: 'k100', label: 'Vídeos ≥100 mil', get: c => c.m.k100, bins: [1, 2, 4, 8, 15, 25], f: v => v },
    { k: 'active', label: 'Concorrentes ativos', get: c => c.m.active, bins: [1, 3, 6, 10, 16, 25], f: v => v },
    { k: 'vpd', label: 'Ritmo (views/dia)', get: c => c.m.vpd_p50, bins: [20, 60, 150, 400, 1000, 3000], f: v => v == null ? '—' : fmt(v) },
    { k: 'n_eff', label: 'Canais efetivos', get: c => c.m.n_eff, bins: [2, 4, 7, 12, 20, 35], f: v => v == null ? '—' : String(v).replace('.', ',') },
    { k: 'small', label: 'Views de canais < 100 mil', get: c => c.m.small_view_share, bins: [.03, .08, .15, .25, .4, .6], f: v => pct(v) },
    { k: 'purity', label: 'Pureza do idioma', get: c => c.m.lang_purity, bins: [.2, .35, .5, .65, .8, .9], f: v => pct(v) },
    { k: 'fresh', label: 'Views de canais frescos', get: c => c.m.fresh_share || 0, bins: [.02, .05, .1, .2, .3, .5], f: v => pct(v) },
    { k: 'D', label: 'D auto (demanda)', get: c => c.auto && c.auto.D, bins: [1.5, 2, 2.5, 3, 4, 5], f: v => v },
    { k: 'L', label: 'L auto (lacuna)', get: c => c.auto && c.auto.L, bins: [1.5, 2, 2.5, 3, 4, 5], f: v => v },
  ];
  let metric = store.get('metric', 'med'); let selCell = null;
  const s3 = section('mapa', 'Mapa de mercado', 'Nicho × idioma',
    `<p>${esc((D.method && D.method.scan) || 'Para cada célula: busca por idioma com filtros (últimos 12 meses, ordenado por views), enriquecida com dados de vídeo e canal. Só contam como oferta os vídeos long-form no idioma-alvo.')}</p>
     <div class="hm-ctl" id="hm-ctl" role="group" aria-label="Métrica do mapa"></div><div class="ramp" id="hm-ramp"></div>
     <div class="chart" style="overflow-x:auto"><div class="heat" id="heat" role="group" aria-label="Mapa nicho por idioma"></div></div>
     <p class="cap small">Hachurado = menos de 5 vídeos long-form nativos. Clique numa célula para ver consulta, métricas e os vídeos que a sustentam.</p>
     <div class="detail" id="cell-detail" hidden></div>`);
  const MIXN = [['<10k', '< 10 mil'], ['10k–100k', '10–100 mil'], ['100k–1M', '100 mil–1 mi'], ['>1M', '> 1 mi']];
  const FLAGS = { idioma_nao_verificado: 'parte dos vídeos sem idioma identificável ficou fora da oferta (pode estar subestimada)', idioma_nao_verificavel: 'idioma sem detector por título: vale o metadado do YouTube e o filtro da busca', sem_datas: 'vídeos sem data: ritmo e frescor não medidos', sem_inscritos: 'sem inscritos: tamanho de canal não medido',
    cabeca_saturada: 'topo saturado: nicho largo, desça um subnicho', mediana_instavel: 'mediana instável (intervalo largo)', oferta_acima_do_teto: 'oferta acima do teto da estimativa (1 mi)',
    tamanho_assumido: 'tamanho do mercado assumido', V_por_canais_pequenos: 'V estimado pelas views de canais pequenos', V_sem_dados: 'V sem dados' };
  function vitals(c) {
    const mm = c.m, au = c.auto || {}, n = v => v == null ? '—' : nf.format(v), d1 = v => v == null ? '—' : String(v).replace('.', ',');
    const mix = mm.size_mix ? `<div class="mix" role="img" aria-label="Views por faixa de inscritos do canal">${MIXN.map(([k, lb], i) => `<i class="m${i}" style="width:${Math.round(mm.size_mix[k].views * 100)}%" title="${lb}: ${pct(mm.size_mix[k].views)} das views"></i>`).join('')}</div><p class="small">${MIXN.map(([k, lb], i) => `<span class="mx${i}">■</span> ${lb} ${pct(mm.size_mix[k].views)}`).join(' · ')} das views, por inscritos do canal.</p>` : '<p class="small">Sem inscritos nos dados: tamanho de canal não medido.</p>';
    return `<div class="vitals">
      <div><span class="k">Ritmo (views/dia)</span><b>${n(mm.vpd_p50)}</b><span class="small">p25 ${n(mm.vpd_p25)} · p75 ${n(mm.vpd_p75)}${mm.vpd_lo != null ? ` · IC 90%: ${n(mm.vpd_lo)}–${n(mm.vpd_hi)}` : ''}</span></div>
      <div><span class="k">Canais efetivos</span><b>${d1(mm.n_eff)}</b><span class="small">de ${mm.active} ativos · top 3 = ${pct(mm.dominance)} das views</span></div>
      <div><span class="k">Porta aberta</span><b>${pct(mm.small_view_share)}</b><span class="small">das views vêm de canais com menos de 100 mil inscritos · ${mm.small_wins} vídeos ≥ 100 mil de canal pequeno</span></div>
      <div><span class="k">Oferta estimada</span><b>${mm.supply_est == null ? '—' : fmt(mm.supply_est)}</b><span class="small">vídeos que casam com a busca (aproximado) · Shorts nos resultados: ${pct(mm.short_share)}</span></div>
    </div>${mix}${(au.flags || []).length ? `<p class="small">${au.flags.map(f => `<span class="chip warn">${esc(FLAGS[f] || f)}</span>`).join(' ')}</p>` : ''}${c.fetched_at ? `<p class="small">Coletado em ${esc(String(c.fetched_at).replace('T', ' ').replace('Z', ' UTC'))}${au.d_basis ? ' · D sugerido por ' + esc(au.d_basis) : ''}.</p>` : ''}`;
  }
  function openCell(c) {
    selCell = `${c.id}__${c.lang}`; drawHeat();
    const el = s3.querySelector('#cell-detail'); const mm = c.m;
    el.hidden = false;
    el.innerHTML = `<button class="x" aria-label="Fechar">fechar ✕</button><h4>${esc(c.label)} · ${esc(langLabel(c.lang))}</h4>
      <p class="small">Consulta: ${c.queries.map(q => `<code>${esc(q)}</code>`).join(' ')} · modos: ${esc(c.modes.join(', '))}${c.lens ? ' · lente: ' + esc(c.lens) : ''}</p>
      <div class="tiles"><div class="tile"><div class="k">Mediana long</div><div class="v">${fmt(mm.med)}</div><div class="d">p90 ${fmt(mm.p90)} · topo ${fmt(mm.top_views)}</div></div>
      <div class="tile"><div class="k">≥100 mil / ≥1 mi</div><div class="v">${mm.k100} / ${mm.m1}</div><div class="d">${mm.n_long} long-form nativos de ${mm.n}</div></div>
      <div class="tile"><div class="k">Concorrentes ativos</div><div class="v">${mm.active}</div><div class="d">top 3 = ${pct(mm.dominance)} das views</div></div>
      <div class="tile"><div class="k">Pureza / frescos</div><div class="v">${pct(mm.lang_purity)}</div><div class="d">frescos ${pct(mm.fresh_share)} · recentes ${pct(mm.recent_share)}</div></div>
      <div class="tile hl"><div class="k">Auto D · L · V</div><div class="v">${c.auto ? `${c.auto.D}·${c.auto.L}·${c.auto.V}` : '—'}</div><div class="d">base do idioma: ${fmt(c.auto && c.auto.lang_baseline_med)}</div></div></div>
      ${vitals(c)}
      <div class="tbl"><table><thead><tr><th>Vídeo nativo</th><th>Canal</th><th class="r">Views</th><th class="r">Inscritos</th><th>Data</th><th class="r">Dur.</th></tr></thead><tbody>${mm.top.map(t => `<tr><td>${vlink(t.id, t.title)}</td><td>${clink(t.channel_id, t.channel)}</td><td class="r">${nf.format(t.views || 0)}</td><td class="r">${fmt(t.subs)}</td><td>${dt(t.published)}</td><td class="r">${mins(t.dur)}</td></tr>`).join('')}</tbody></table></div>
      ${mm.foreign_top && mm.foreign_top.length ? `<p class="small"><strong>Concorrência em outro idioma que aparece nesta busca:</strong> ${mm.foreign_top.map(t => `${vlink(t.id, t.title)} (${esc(t.lang || '?')}, ${fmt(t.views)})`).join(' · ')}</p>` : ''}`;
    el.querySelector('.x').onclick = () => { el.hidden = true; selCell = null; drawHeat(); };
    el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
  function drawHeat() {
    const M = METRICS.find(x => x.k === metric) || METRICS[0];
    s3.querySelector('#hm-ctl').innerHTML = METRICS.map(x => `<button class="tog" data-m="${x.k}" aria-pressed="${x.k === metric}">${esc(x.label)}</button>`).join('');
    s3.querySelector('#hm-ctl').onclick = e => { const b = e.target.closest('button'); if (!b) return; metric = b.dataset.m; store.set('metric', metric); drawHeat(); };
    const b = M.bins; s3.querySelector('#hm-ramp').innerHTML = `<span style="margin-right:6px">${esc(M.label)}:</span>` + [0, 1, 2, 3, 4, 5, 6].map(i => `<span class="sw hb${i}">${i === 0 ? '<' + M.f(b[0]) : i === 6 ? '≥' + M.f(b[5]) : M.f(b[i - 1]) + '–' + M.f(b[i])}</span>`).join('');
    const langs = allLangs.filter(l => S.langs.has(l));
    const byId = {}; (D.cells || []).forEach(c => { (byId[c.id] = byId[c.id] || { label: c.label, lens: c.lens, cells: {} }).cells[c.lang] = c; });
    const rows = Object.entries(byId).filter(([id, r]) => qmatch(id, r.label, r.lens));
    rows.sort((p, q) => langs.reduce((s, l) => s + ((q[1].cells[l] && M.get(q[1].cells[l])) || 0), 0) - langs.reduce((s, l) => s + ((p[1].cells[l] && M.get(p[1].cells[l])) || 0), 0));
    const bin = v => v == null ? 0 : b.findIndex(t => v < t) === -1 ? 6 : b.findIndex(t => v < t);
    const host = s3.querySelector('#heat');
    host.style.gridTemplateColumns = `minmax(118px,1.2fr) repeat(${langs.length}, minmax(60px,1fr))`;
    host.style.minWidth = (125 + langs.length * 64) + 'px';
    host.innerHTML = `<div class="hd">Nicho</div>${langs.map(l => `<div class="hd">${esc(langLabel(l))}</div>`).join('')}` + rows.map(([id, r]) =>
      `<div class="rh">${esc(r.label)}${r.lens ? `<small>${esc(r.lens)}</small>` : ''}</div>` + langs.map(l => { const c = r.cells[l]; if (!c) return '<div class="empty">—</div>';
        const v = M.get(c); const low = c.m.n_long < 5;
        return `<button class="cell hb${bin(v)}${low ? ' lown' : ''}${selCell === id + '__' + l ? ' sel' : ''}" data-k="${esc(id)}|${esc(l)}"><div class="m">${M.f(v)}</div><div class="x">${metric === 'med' ? '' : fmt(c.m.med) + ' · '}n=${c.m.n_long}</div></button>`; }).join('')).join('');
    host.querySelectorAll('.cell').forEach(el => { const [id, l] = el.dataset.k.split('|'); const c = byId[id].cells[l];
      bindTip(el, `<b>${esc(c.label)} · ${esc(langLabel(l))}</b><br>“${esc(c.queries[0])}”<br>mediana ${nf.format(c.m.med)} · ≥100 mil ${c.m.k100} · ativos ${c.m.active}<br>pureza ${pct(c.m.lang_purity)} · frescos ${pct(c.m.fresh_share)} · auto D${c.auto ? c.auto.D : '?'} L${c.auto ? c.auto.L : '?'}`);
      el.onclick = () => openCell(c); });
  }
  onFilter(drawHeat)();
  { // link direto para uma célula: relatorio.html#cell=<id>__<idioma>
    const dl = location.hash.match(/^#cell=([^&]+)/);
    let key = null; try { key = dl && decodeURIComponent(dl[1]); } catch (e) { key = null; }  // #cell=100% não pode abortar o relatório
    const c0 = key && (D.cells || []).find(x => `${x.id}__${x.lang}` === key);
    if (c0) { openCell(c0); if (!/noscroll/.test(location.hash)) s3.scrollIntoView({ behavior: 'auto', block: 'start' }); }
  }

  /* 04 FIT CULTURAL */
  if ((D.markets && D.markets.length) || (D.signals && (D.signals.wiki || D.signals.suggest || D.signals.trending))) {
    const s4 = section('fit', 'Fit cultural', 'Fit por país', `${D.method && D.method.fit ? `<p>${esc(D.method.fit)}</p>` : ''}<div class="cards" id="mk"></div><div id="sig"></div>`);
    onFilter(() => {
      s4.querySelector('#mk').innerHTML = (D.markets || []).filter(k => S.langs.has(k.lang) && qmatch(k.label, k.fit_notes, k.consumption)).map(k => `<div class="card"><h4>${esc(k.label || langLabel(k.lang))} ${k.fit != null ? `<span class="chip ${k.fit >= 4 ? 'ok' : k.fit <= 2 ? 'bad' : 'mut'}">fit ${k.fit}/5</span>` : ''}</h4>
        <div class="sub">${esc(k.countries || '')}${k.rpm_class ? ' · RPM ' + esc(k.rpm_class) : ''}${k.yt_users ? ' · ' + esc(k.yt_users) : ''}</div>
        ${k.fit_notes ? `<p>${esc(k.fit_notes)}</p>` : ''}${k.consumption ? `<p class="small"><strong>Consumo:</strong> ${esc(k.consumption)}</p>` : ''}${k.queries ? `<p class="small"><strong>Como buscam:</strong> ${esc(k.queries)}</p>` : ''}${k.risks ? `<p class="small"><strong>Cuidado:</strong> ${esc(k.risks)}</p>` : ''}${ev(k.evidence)}</div>`).join('');
      const sig = D.signals || {}; let h = '';
      (sig.wiki || []).forEach(w => { const rows = (w.rows || []).filter(r => S.langs.has(r.lang)); if (!rows.length) return; const mx = Math.max(1, ...rows.map(r => r.index || 0));
        h += `<h3>Interesse relativo · ${esc(w.concept || w.seed)}</h3><p class="small">Pageviews de 12 meses ÷ tráfego total de cada Wikipédia (índice 100 = idioma com maior interesse relativo; × mediana > 1,5 = o tema pesa mais ali que no idioma típico). Tendência = últimos 12 meses contra os 12 anteriores, descontada a queda da própria Wikipédia. Mede curiosidade cultural pelo conceito, não consumo de vídeo.</p><div class="tbl"><table><thead><tr><th>Idioma</th><th>Artigo</th><th class="r">Views 12m</th><th class="r">× mediana</th><th class="r">Índice</th><th>Tendência</th></tr></thead><tbody>${rows.sort((p, q) => (q.index || 0) - (p.index || 0)).map(r => `<tr><td>${esc(langLabel(r.lang))}</td><td>${r.url ? a(r.url, r.title) : '<span class="small">sem artigo</span>'}</td><td class="r">${r.views == null ? '—' : nf.format(r.views)}</td><td class="r">${r.rel == null ? '—' : String(r.rel).replace('.', ',') + '×'}</td><td class="r">${r.index == null ? '—' : `<span class="bar-in b" style="width:${Math.round(r.index / mx * 80)}px"></span>${r.index}`}</td><td>${r.trend ? `<span class="chip ${r.trend === 'subindo' ? 'ok' : r.trend === 'caindo' ? 'bad' : 'mut'}">${esc(r.trend)}</span> <span class="small">${r.yoy_rel == null ? '' : (r.yoy_rel > 0 ? '+' : '') + Math.round(r.yoy_rel * 100) + '% vs. a Wikipédia'}</span>` : '<span class="small">—</span>'}</td></tr>`).join('')}</tbody></table></div>`; });
      const sug = (sig.suggest || []).filter(s => S.langs.has(s.lang));
      if (sug.length) h += `<h3>Como cada mercado digita</h3><p class="small">Autocomplete do YouTube por idioma: consultas reais, gírias e subnichos.</p><div class="cards">${sug.map(s => `<div class="card"><h4>${esc(langLabel(s.lang))} · “${esc(s.seed)}”</h4><div class="sub">${s.count} sugestões</div><p class="small">${(s.top || []).slice(0, 14).map(esc).join(' · ')}</p></div>`).join('')}</div>`;
      (sig.trending || []).forEach(t => { h += `<h3>Em alta agora · ${esc(t.geo)}</h3><p class="small">Buscas em alta no Google Trends${t.youtube_popular ? ' e vídeos em alta no YouTube' : ''}, em ${dt(t.fetched_at)} ${esc(String(t.fetched_at || '').slice(11, 16))} UTC. Retrato do momento: ajuda a separar demanda de base de pico de evento.</p><div class="cols"><div><h4>Google Trends</h4><ul class="small">${(t.google_trends || []).slice(0, 10).map(x => `<li>${esc(x.query)} <span class="small">${esc(x.traffic || '')}</span>${x.news && x.news[0] ? ` · ${a(x.news[0].url, x.news[0].source || 'notícia')}` : ''}</li>`).join('')}</ul></div>${t.youtube_popular && t.youtube_popular.length ? `<div><h4>YouTube em alta</h4><ul class="small">${t.youtube_popular.slice(0, 10).map(v => `<li>${vlink(v.id, v.title)} <span class="small">${clink(v.channel_id, v.channel)} · ${fmt(v.views)}</span></li>`).join('')}</ul></div>` : ''}</div>`; });
      s4.querySelector('#sig').innerHTML = h;
    })();
  }

  /* 04b PESQUISA EM TEMPO REAL */
  if (D.research && D.research.length) {
    const TOP = { monetizacao: 'Monetização', politica: 'Políticas do YouTube', tendencia: 'Tendência e notícias', concorrencia: 'Concorrência', producao: 'Produção e preços', mercado: 'Mercado e cultura', outro: 'Outros' };
    const CF = { alta: 'ok', media: 'warn', baixa: 'bad' };
    const sR = section('pesquisa', 'Pesquisa em tempo real', 'O que a web diz hoje', `<p>Fatos externos que sustentam receita, risco e tendência. Cada linha tem fonte aberta e data de consulta; número só de blog ou comunidade vem marcado e pede confirmação antes de decidir.</p><div id="rs"></div>`);
    onFilter(table(sR.querySelector('#rs'), [
      { key: 'topic', label: 'Tema', f: r => esc(TOP[r.topic] || r.topic) },
      { key: 'claim', label: 'Fato', cls: 'w-txt', f: r => `${esc(r.claim)}${r.note ? `<br><span class="small">${esc(r.note)}</span>` : ''}` },
      { key: 'value', label: 'Valor', cls: 'nw', f: r => esc(r.value || '—') + (r.unit ? ` <span class="small">${esc(r.unit)}</span>` : '') },
      { key: 'domain', label: 'Fonte', f: r => a(r.url, r.domain || r.url) },
      { key: 'type', label: 'Tipo', cls: 'hide-sm' },
      { key: 'confidence', label: 'Confiança', f: r => `<span class="chip ${CF[r.confidence] || 'mut'}">${esc(r.confidence)}</span>` },
      { key: 'accessed', label: 'Acesso', cls: 'nw', f: r => dt(r.accessed) },
    ], () => D.research.filter(r => qmatch(r.claim, r.topic, r.domain, r.value, r.note)), { sort: 'topic', dir: 1 }));
  }

  /* 05 CONCORRÊNCIA E CANAIS FRESCOS */
  if (D.channels && D.channels.length) {
    let onlyFresh = false;
    const s5 = section('canais', 'Concorrência', 'Quem já está lá', `<p>Canais que aparecem no topo das buscas, perfilados sem custo de busca. “Fresco” = conta criada (ou reativada) há ≤ 18 meses e mediana ≥ 10 mil views: indício de que o algoritmo está distribuindo aquele formato para quem chega agora.</p><p class="small">Víd. 90d = vídeos publicados nos últimos 90 dias · Med. 90d = mediana de views desses vídeos · Med. geral = mediana long-form da amostra · Min = duração média · Outl. = vídeos com ≥ 3× a mediana do canal. Clique no cabeçalho para ordenar.</p><p><button class="tog" id="only-fresh" aria-pressed="false">só canais frescos</button></p><div id="chs"></div>`);
    const draw = onFilter(table(s5.querySelector('#chs'), [
      { key: 'title', label: 'Canal', cls: 'w-name', f: c => `${clink(c.id, c.title)}${c.fresh ? ' <span class="chip ok">fresco</span>' : ''}${c.reactivated ? ' <span class="chip warn">reativado</span>' : ''}<br><span class="small">${esc([c.lang, c.country].filter(Boolean).join(' · ') || '—')}</span>` },
      { key: 'created', label: 'Criado', cls: 'nw', f: c => dt(c.created) + (c.first_upload && c.reactivated ? `<br><span class="small">1º vídeo ${dt(c.first_upload)}</span>` : '') },
      { key: 'subs', label: 'Inscritos', r: 1, f: c => fmt(c.subs) }, { key: 'uploads_90d', label: 'Víd. 90d', r: 1 },
      { key: 'median_90d', label: 'Med. 90d', r: 1, cls: 'nw', f: c => `<span class="bar-in b" style="width:${Math.round(Math.log10(Math.max(10, c.median_90d || 10)) * 10)}px"></span>${fmt(c.median_90d)}` },
      { key: 'median_long', label: 'Med. geral', r: 1, cls: 'hide-sm', f: c => fmt(c.median_long) }, { key: 'avg_dur_min', label: 'Min', r: 1, cls: 'hide-sm', f: c => c.avg_dur_min == null ? '—' : Math.round(c.avg_dur_min) },
      { key: 'outliers', label: 'Outl.', r: 1, cls: 'hide-sm' },
      { key: 'top', label: 'Maior vídeo', nosort: 1, cls: 'w-vid hide-sm', f: c => c.top && c.top[0] ? `${vlink(c.top[0].id, c.top[0].title)} <span class="small">${fmt(c.top[0].views)}</span>` : '—' },
    ], () => D.channels.filter(c => !c.error && (!c.lang || S.langs.has(c.lang)) && (!onlyFresh || c.fresh) && qmatch(c.title, c.handle, c.country)), { sort: 'median_90d', limit: 40 }));
    s5.querySelector('#only-fresh').onclick = e => { onlyFresh = !onlyFresh; e.target.setAttribute('aria-pressed', onlyFresh); draw(); };
  }

  /* 06 LACUNA DE FORMATO */
  if (D.format_gap && D.format_gap.length) {
    const s6 = section('formato', 'Lacuna de formato', 'Ocupação do formato', `${D.method && D.method.format ? `<p>${esc(D.method.format)}</p>` : '<p>Para cada célula promissora, as thumbnails do topo foram classificadas por estilo. Se o estilo proposto não aparece entre os vencedores, o formato está subutilizado ali.</p>'}<div id="fg"></div>`);
    onFilter(() => { s6.querySelector('#fg').innerHTML = `<div class="tbl"><table><thead><tr><th>Célula</th><th>Estilos dominantes</th><th>Estilo proposto presente?</th><th>Leitura</th></tr></thead><tbody>${D.format_gap.filter(g => S.langs.has(g.lang) && qmatch(g.cell, g.note)).map(g => `<tr><td><strong>${esc(g.label || g.cell)}</strong> · ${esc(langLabel(g.lang))}</td><td>${(g.styles || []).map(s => `${esc(s.style)} <span class="small">${pct(s.share)}</span>`).join('<br>')}</td><td>${g.proposed_present == null ? '<span class="chip mut">a conferir</span>' : g.proposed_present ? '<span class="chip bad">sim</span>' : '<span class="chip ok">não: lacuna</span>'}</td><td>${esc(g.note || '')}</td></tr>`).join('')}</tbody></table></div>
      ${D.format_gap.some(g => g.sheet_src) ? `<div class="gallery">${D.format_gap.filter(g => g.sheet_src && S.langs.has(g.lang)).map(g => `<figure><img src="${esc(g.sheet_src)}" alt="Thumbnails do topo de ${esc(g.label || g.cell)} em ${esc(g.lang)}" loading="lazy"><figcaption>${esc(g.label || g.cell)} · ${esc(langLabel(g.lang))}</figcaption></figure>`).join('')}</div>` : ''}`; })();
  }

  /* 07 TRANSPOSIÇÃO DE TÍTULOS */
  if (D.probes && D.probes.length) {
    const s7 = section('titulos', 'Transposição de títulos', 'Títulos em outros mercados', `<p>Ângulos vencedores traduzidos de forma nativa (não literal) e buscados em cada idioma. <span class="dot lacuna"></span> lacuna = nenhum semelhante na amostra válida · <span class="dot fraco"></span> fraco = existe com poucas views · <span class="dot existe"></span> existe = alguém já fez com tração. Inconclusivo = faltam dados para decidir. Contorno tracejado = status revisado à mão (falso positivo ou negativo da comparação automática).</p><div id="pm"></div>`);
    onFilter(() => {
      const langs = allLangs.filter(l => S.langs.has(l)); const src = {}; (D.probe_sources || []).forEach(p => { src[p.id] = p; });
      const by = {}; D.probes.forEach(p => { (by[p.probe] = by[p.probe] || {})[p.lang] = p; });
      s7.querySelector('#pm').innerHTML = `<div class="tbl"><table class="mx"><thead><tr><th>Ângulo de origem</th>${langs.map(l => `<th class="r">${esc(langLabel(l))}</th>`).join('')}</tr></thead><tbody>${Object.entries(by).filter(([id]) => qmatch(id, src[id] && src[id].title)).map(([id, r]) => `<tr><td>${src[id] ? `${src[id].video_id ? vlink(src[id].video_id, src[id].title) : esc(src[id].title)}${src[id].views ? ` <span class="small">${fmt(src[id].views)} · ${esc(src[id].lang || '')}</span>` : ''}` : esc(id)}</td>${langs.map(l => { const p = r[l]; if (!p) return '<td class="st small">·</td>';
        return `<td class="st"><span class="dot ${esc(p.status)}${p.reviewed ? ' rev' : ''}" tabindex="0" role="img" aria-label="${esc(langLabel(l))}: ${esc(p.status)}" data-t="${esc(`<b>${esc(langLabel(l))} · ${esc(p.status)}</b>${p.reviewed ? ` (revisado; automático: ${esc(p.auto_status)})` : ''}<br>“${esc(p.query)}”` + (p.best ? `<br>mais próximo: ${esc(p.best.title)} (${fmt(p.best.views)})` : '') + (p.note ? `<br><i>${esc(p.note)}</i>` : ''))}"></span>${p.best ? `<br>${a(vurl(p.best.id), fmt(p.best.views) || 'ver')}` : ''}</td>`; }).join('')}</tr>`).join('')}</tbody></table></div>`;
      s7.querySelectorAll('.dot[data-t]').forEach(d => bindTip(d, d.dataset.t));
    })();
  }

  /* 08 OPORTUNIDADES */
  const s8 = section('oportunidades', 'Oportunidades', 'Ranking detalhado', `<p>${esc((D.method && D.method.score) || 'Oceano (O) = 0,30·Demanda + 0,30·Lacuna + 0,25·Fit cultural + 0,15·Formato subutilizado. Produção (P) = média de Automação, Custo e Fazer sozinho/local. Nota = 20·(0,50·O + 0,25·P + 0,15·Receita + 0,10·Velocidade). Travas limitam ao tier B quando falta demanda, sobra concorrência, falta fit ou o risco é alto.')}</p><div class="opps" id="opps"></div>`);
  const AX = [['D', 'Demanda', 'o'], ['L', 'Lacuna', 'o'], ['F', 'Fit cultural', 'o'], ['G', 'Formato livre', 'o'], ['A', 'Automação'], ['K', 'Custo baixo'], ['S', 'Solo/local'], ['M', 'Receita'], ['V', 'Velocidade'], ['R', 'Risco', 'r']];
  onFilter(() => {
    const host = s8.querySelector('#opps');
    const list2 = opps.filter(o => S.tiers.has(tierOf(o)) && (!o.lang || o.lang === 'multi' || S.langs.has(o.lang)) && qmatch(o.name, o.oneliner, o.lens, o.domain, (o.titles || []).join(' ')));
    host.innerHTML = list2.map((o, i) => { const c = o.computed || {}; const sc = o.scores || {}; const v = k => { const x = sc[k]; return x == null ? null : typeof x === 'object' ? x.v : x; };
      const OCEAN = 'DLFG'; const why = k => { const x = sc[k]; return x && typeof x === 'object' ? (x.why || '') + (OCEAN.includes(k) ? (x.measured ? ' (medido)' : ' (julgado)') : '') : ''; };
      const pr = o.production || {};
      return `<details class="opp" id="op-${esc(o.id)}" ${i < 3 ? 'open' : ''}><summary><span>${vchip(c.verdict)}<br><span class="chip ${tierOf(o)}">TIER ${tierOf(o)}</span></span><div><h3>${esc(o.name)}</h3><div class="mk">${esc(langLabel(o.lang))}${o.markets ? ' · ' + esc(o.markets) : ''}${o.lens ? ' · lente: ' + esc(o.lens) : ''}${c.blue_ocean ? ' · <span class="chip ok">oceano azul</span>' : ''}</div></div><div class="score"><b>${c.total != null ? c.total : '—'}</b>/100${c.range ? `<br>faixa ${c.range[0]}–${c.range[1]}` : ''}${c.confidence ? `<br>confiança ${esc(c.confidence)}` : ''}${c.uncertainty != null ? `<br>incerteza ${pct(c.uncertainty)}` : ''}</div></summary>
        <div class="body"><div class="axes">${AX.map(([k, lb, cls]) => v(k) == null ? '' : `<div class="axis ${cls || ''}" title="${esc(why(k))}"><span>${k}</span><span class="t"><i style="width:${v(k) * 20}%"></i></span><span>${v(k)}</span></div>`).join('')}</div>
        ${c.caps && c.caps.length ? `<p class="small"><span class="chip warn">trava</span> ${c.caps.map(esc).join(' · ')}</p>` : ''}
        ${c.reasons && c.reasons.length ? `<p class="small"><strong>Por que ${esc(c.verdict || '')}:</strong> ${c.reasons.map(esc).join(' · ')}.</p>` : ''}
        ${c.missing && c.missing.length ? `<p class="small"><strong>Falta medir:</strong> ${c.missing.map(x => `${esc(AXN[x.axis] || x.axis)} (${esc(x.how)})`).join(' · ')}</p>` : ''}
        <dl>${o.bend ? `<dt>Bend</dt><dd>${esc(o.bend.label || '')}${o.bend.from ? ` <span class="small">(${esc(o.bend.from)} → ${esc(o.bend.to || '')})</span>` : ''}</dd>` : ''}
        ${o.why_now ? `<dt>Por que agora</dt><dd>${esc(o.why_now)}</dd>` : ''}
        ${AX.filter(([k]) => why(k)).length ? `<dt>Notas por eixo</dt><dd><ul class="small">${AX.filter(([k]) => sc[k] && typeof sc[k] === 'object' && sc[k].why).map(([k, lb]) => `<li><strong>${lb} ${v(k)}</strong>: ${esc(sc[k].why)}${OCEAN.includes(k) ? (sc[k].measured ? ' <span class="chip ok">medido</span>' : ' <span class="chip mut">julgado</span>') : ''}</li>`).join('')}</ul></dd>` : ''}
        ${o.evidence && o.evidence.length ? `<dt>Evidência</dt><dd>${ev(o.evidence)}</dd>` : ''}
        ${o.aesthetic ? `<dt>Estética</dt><dd>${esc(o.aesthetic)}</dd>` : ''}${o.format ? `<dt>Formato</dt><dd>${esc(o.format)}</dd>` : ''}
        ${o.titles && o.titles.length ? `<dt>Títulos</dt><dd><ul class="titles">${o.titles.map(t => `<li>${esc(t)}</li>`).join('')}</ul></dd>` : ''}
        ${o.signature ? `<dt>Assinatura</dt><dd>${esc(o.signature)}</dd>` : ''}
        ${pr.automation || pr.cost ? `<dt>Produção</dt><dd>${[pr.automation ? 'Automação: ' + esc(pr.automation) : '', pr.cost ? 'Custo/vídeo: ' + esc(pr.cost) : '', pr.local ? 'Local: ' + esc(pr.local) : '', pr.solo ? 'Sozinho: ' + esc(pr.solo) : '', pr.stack ? 'Stack: ' + esc(pr.stack) : ''].filter(Boolean).join('<br>')}</dd>` : ''}
        ${o.monetization ? `<dt>Receita</dt><dd>${esc(o.monetization)}</dd>` : ''}${o.risks ? `<dt>Riscos</dt><dd>${esc(o.risks)}</dd>` : ''}
        ${o.first_videos && o.first_videos.length ? `<dt>Primeiros vídeos</dt><dd><ol>${o.first_videos.map(t => `<li>${esc(t)}</li>`).join('')}</ol></dd>` : ''}
        ${o.competitors && o.competitors.length ? `<dt>Concorrentes</dt><dd>${o.competitors.map(c => c.id ? clink(c.id, c.title) : esc(c.title)).join(' · ')}</dd>` : ''}
        </dl></div></details>`; }).join('') || '<p class="empty-note">Nenhuma oportunidade com os filtros atuais.</p>';
  })();

  /* 09 PRODUÇÃO */
  const P = D.production;
  if (P) {
    section('producao', 'Produção', 'Automação, custo e operação',
      `${P.intro ? `<p>${esc(P.intro)}</p>` : ''}
       ${P.pipeline ? `<div class="pipe">${P.pipeline.map(s => `<div class="st${s.gate ? ' gate' : ''}"><h4>${esc(s.name)}</h4><p>${esc(s.desc)}</p><span class="tool">${esc(s.tool || '')}</span></div>`).join('')}</div>` : ''}
       ${P.costs ? `<h3>Custo por vídeo</h3><div class="tbl"><table><thead><tr><th>Estilo</th><th class="r">100% local</th><th class="r">Híbrido</th><th class="r">Nuvem</th><th class="r">Horas humanas</th><th>Observação</th></tr></thead><tbody>${P.costs.map(c => `<tr><td><strong>${esc(c.style)}</strong></td><td class="r">${esc(c.local || '—')}</td><td class="r">${esc(c.hybrid || '—')}</td><td class="r">${esc(c.cloud || '—')}</td><td class="r">${esc(c.hours || '—')}</td><td>${esc(c.note || '')}</td></tr>`).join('')}</tbody></table></div>` : ''}
       ${P.stack ? `<h3>Stack recomendada</h3>${list(P.stack.map(esc))}` : ''}${P.notes ? list(P.notes.map(esc)) : ''}${ev(P.sources)}`);
  }

  /* 10 RISCOS / 11 PLANO */
  if (D.risks && D.risks.length) section('riscos', 'Riscos', 'O que pode dar errado', `<div class="tbl"><table><thead><tr><th>Risco</th><th>Nível</th><th>Mitigação</th></tr></thead><tbody>${D.risks.map(r => `<tr><td><strong>${esc(r.risk)}</strong>${r.source ? '<br>' + a(r.source, 'fonte') : ''}</td><td><span class="chip ${r.level === 'alto' ? 'bad' : r.level === 'médio' ? 'warn' : 'mut'}">${esc(r.level || '')}</span></td><td>${esc(r.mitigation || '')}</td></tr>`).join('')}</tbody></table></div>`);
  if (D.plan && D.plan.length) section('plano', 'Plano', 'O menor experimento que responde', `<div class="tbl"><table><thead><tr><th>Quando</th><th>Entrega</th><th>Critério de sucesso</th></tr></thead><tbody>${D.plan.map(p => `<tr><td class="r">${esc(p.when)}</td><td>${esc(p.what)}</td><td>${esc(p.success || '')}</td></tr>`).join('')}</tbody></table></div>`);

  /* 12 EXPLORADOR DE VÍDEOS */
  const vids = {}; (D.cells || []).forEach(c => (c.m.top || []).forEach(t => { if (!vids[t.id]) vids[t.id] = { ...t, cell: c.label, cell_lang: c.lang }; }));
  const vlist = Object.values(vids);
  if (vlist.length) {
    const s12 = section('videos', 'Explorador', 'Todos os vídeos de referência', `<p>Os vídeos nativos que sustentam cada célula, com link. Use a busca do topo e os filtros de idioma; clique nas colunas para ordenar.</p><div id="vx"></div>`);
    onFilter(table(s12.querySelector('#vx'), [
      { key: 'title', label: 'Vídeo', cls: 'w-name', f: v => vlink(v.id, v.title) }, { key: 'channel', label: 'Canal', f: v => clink(v.channel_id, v.channel) },
      { key: 'cell_lang', label: 'Idioma', f: v => esc(langLabel(v.cell_lang)) }, { key: 'cell', label: 'Célula', cls: 'hide-sm' },
      { key: 'views', label: 'Views', r: 1, f: v => nf.format(v.views || 0) }, { key: 'subs', label: 'Inscritos', r: 1, cls: 'hide-sm', f: v => fmt(v.subs) },
      { key: 'ratio', label: 'Views/insc.', r: 1, sv: v => (v.views || 0) / Math.max(1000, v.subs || 0), f: v => ((v.views || 0) / Math.max(1000, v.subs || 0)).toFixed(1).replace('.', ',') + '×' },
      { key: 'published', label: 'Data', cls: 'hide-sm', f: v => dt(v.published) }, { key: 'dur', label: 'Dur.', r: 1, f: v => mins(v.dur) },
    ], () => vlist.filter(v => S.langs.has(v.cell_lang) && qmatch(v.title, v.channel, v.cell)), { sort: 'views', limit: 60 }));
  }

  /* GLOSSÁRIO */
  const GLOSS = [
    ['Veredito', 'GO, TESTAR ou EVITAR. Sai da nota, das travas, da confiança e do risco. Não é promessa de resultado.'],
    ['Nota e faixa', 'Nota de 0 a 100 = 20·(0,50·Oceano + 0,25·Produção + 0,15·Receita + 0,10·Velocidade). A faixa é a nota se cada eixo do oceano ainda julgado estivesse 1 ponto pior ou melhor.'],
    ['Tier', 'S ≥ 80 · A ≥ 70 · B ≥ 58 · C abaixo disso. Travas (demanda vazia, mar vermelho, fit ruim, risco alto, incerteza alta) limitam ao B.'],
    ['Confiança', 'Alta: até 25% dos eixos do oceano sem medição e 10+ vídeos long-form por célula. Média: até 50% e 5+. Baixa: o resto.'],
    ['Medido × julgado', 'Medido tem número coletado e o topo foi lido. Julgado é leitura do analista sem dado suficiente. Cada eixo vem marcado.'],
    ['D · Demanda', 'Ritmo (views por dia) dos vídeos maduros do topo da busca, em equivalente EN (dividido pelo tamanho do mercado do idioma).'],
    ['L · Lacuna de oferta', 'Canais nativos ativos na amostra. Poucos = lacuna; muitos = mar vermelho.'],
    ['F · Fit cultural', 'O tema conversa com o país? Âncora local, formato nativo, registro de língua, regulação e hábito de consumo.'],
    ['G · Formato subutilizado', 'Fatia do estilo proposto entre as thumbnails do topo. Quanto menor, mais livre o formato.'],
    ['A · K · S', 'Produção: automação, custo de IA por vídeo (5 = barato) e se dá para fazer sozinho e localmente, conforme o seu perfil.'],
    ['M · V · R', 'Receita (classe de RPM e monetização extra), velocidade (canais novos crescendo) e risco (5 = arriscado; entra como trava).'],
    ['Canais efetivos', '1 ÷ HHI das views por canal. 60 canais iguais = 60; um canal com tudo = 1. Mede concentração melhor que contar canais.'],
    ['Porta aberta', 'Fatia das views do topo que vem de canais com menos de 100 mil inscritos. Alta = o algoritmo entrega para quem é pequeno.'],
    ['Topo saturado', 'Quase todo o topo passa de 100 mil views: o nicho é largo demais para separar vencedores. Desça um subnicho.'],
    ['Oferta estimada', 'Estimativa do YouTube de quantos vídeos casam com a busca. Aproximada e com teto de 1 milhão; serve para comparar células.'],
    ['Long-form', 'Vídeo com 8 minutos ou mais. Shorts (até 3 min) ficam fora das métricas de demanda e oferta.'],
    ['IC 90%', 'Faixa em que a mediana provavelmente está (bootstrap). Faixa larga = amostra pequena ou instável.'],
  ];
  section('glossario', 'Glossário', 'Como ler os números', `<dl class="gl">${GLOSS.map(([t, d]) => `<dt>${esc(t)}</dt><dd>${esc(d)}</dd>`).join('')}</dl>`);

  /* 13 MÉTODO, LIMITAÇÕES E FONTES */
  section('fontes', 'Método e fontes', 'Limitações, dados e fontes',
    `${D.limitations && D.limitations.length ? `<h3>Limitações</h3>${list(D.limitations.map(esc))}` : ''}
     ${D.method && D.method.notes ? `<h3>Método</h3>${list(D.method.notes.map(esc))}` : ''}
     <h3>Fontes</h3>${D.sources && D.sources.length ? `<ol class="small">${D.sources.map(s => `<li>${s.url ? a(s.url, s.label || s.url) : esc(s.label)}${s.note ? ` · ${esc(s.note)}` : ''}${s.accessed ? ` · acesso ${dt(s.accessed)}` : ''}</li>`).join('')}</ol>` : '<p class="small">Dados públicos da YouTube Data API v3 e do YouTube (links em cada canal e vídeo citado).</p>'}
     <footer>${esc(m.footer || 'Gerado pela skill analise-mercado-yt.')} Dados de ${dt(m.date)}.</footer>`);

  /* índice + filtros */
  document.getElementById('toc').innerHTML = sections.map((s, i) => `<li><a href="#${s.id}"><span class="n">${String(i).padStart(2, '0')}</span>${esc(s.eyebrow)}</a></li>`).join('');
  buildBar();
  /* exportação (CSV com ; e BOM: abre direto no Excel em português) e impressão */
  // texto que começa com = + - @ vira fórmula no Excel: o apóstrofo o mantém como texto (títulos e canais vêm do YouTube)
  const csvq = v => { let s = v == null ? '' : String(v); if (typeof v === 'string' && /^[=+\-@\t\r]/.test(s)) s = "'" + s; return /[";\r\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; };
  const toCsv = (rows, cols) => '﻿' + [cols.map(c => csvq(c[0])).join(';'), ...rows.map(r => cols.map(c => csvq(c[1](r))).join(';'))].join('\r\n');
  const saveCsv = (name, text) => { const u = URL.createObjectURL(new Blob([text], { type: 'text/csv;charset=utf-8' })); const l = document.createElement('a'); l.href = u; l.download = name; document.body.appendChild(l); l.click(); l.remove(); setTimeout(() => URL.revokeObjectURL(u), 3000); };
  const axv = k => o => { const x = (o.scores || {})[k]; return x && typeof x === 'object' ? x.v : x; };
  const EXP = [
    ['células', 'celulas.csv', () => D.cells || [], [['celula', c => c.id], ['rotulo', c => c.label], ['idioma', c => c.lang], ['videos_longform', c => c.m.n_long], ['mediana_views', c => c.m.med], ['views_dia_p25', c => c.m.vpd_p25], ['views_dia_p50', c => c.m.vpd_p50], ['views_dia_p75', c => c.m.vpd_p75], ['canais_ativos', c => c.m.active], ['canais_efetivos', c => c.m.n_eff], ['top3_share', c => c.m.dominance], ['views_canais_pequenos', c => c.m.small_view_share], ['views_canais_frescos', c => c.m.fresh_share], ['pureza_idioma', c => c.m.lang_purity], ['videos_100k', c => c.m.k100], ['oferta_estimada', c => c.m.supply_est], ['D_auto', c => c.auto && c.auto.D], ['L_auto', c => c.auto && c.auto.L], ['V_auto', c => c.auto && c.auto.V], ['coletado_em', c => c.fetched_at], ['flags', c => ((c.auto && c.auto.flags) || []).join('|')]]],
    ['canais', 'canais.csv', () => D.channels || [], [['canal', c => c.title], ['url', c => c.url], ['pais', c => c.country], ['criado', c => c.created], ['inscritos', c => c.subs], ['uploads_90d', c => c.uploads_90d], ['mediana_90d', c => c.median_90d], ['mediana_long', c => c.median_long], ['top3_share', c => c.top3_share], ['dedicado_ao_nicho', c => c.topic_share], ['fresco', c => c.fresh ? 'sim' : 'nao']]],
    ['vídeos', 'videos.csv', () => vlist, [['titulo', v => v.title], ['url', v => vurl(v.id)], ['canal', v => v.channel], ['idioma', v => v.cell_lang], ['celula', v => v.cell], ['views', v => v.views], ['inscritos', v => v.subs], ['publicado', v => v.published], ['duracao_s', v => v.dur]]],
    ['oportunidades', 'oportunidades.csv', () => opps, [['nome', o => o.name], ['idioma', o => o.lang], ['veredito', verdOf], ['confianca', o => o.computed && o.computed.confidence], ['tier', tierOf], ['nota', o => o.computed && o.computed.total], ['faixa_min', o => o.computed && o.computed.range && o.computed.range[0]], ['faixa_max', o => o.computed && o.computed.range && o.computed.range[1]], ...'DLFGAKSMVR'.split('').map(k => [k, axv(k)])]],
    ['pesquisa', 'pesquisa.csv', () => D.research || [], [['tema', r => r.topic], ['fato', r => r.claim], ['valor', r => r.value], ['fonte', r => r.url], ['tipo', r => r.type], ['confianca', r => r.confidence], ['acesso', r => r.accessed]]],
  ].filter(e => e[2]().length);
  const fx = document.getElementById('f-exp');
  if (fx) {
    fx.innerHTML = '<span class="lbl">Baixar</span>' + EXP.map((e, i) => `<button class="tog" data-e="${i}">${esc(e[0])} .csv</button>`).join('') + '<button class="tog" data-p="1">imprimir / PDF</button>';
    fx.onclick = ev2 => { const b = ev2.target.closest('button'); if (!b) return; if (b.dataset.p) { window.print(); return; } const e = EXP[+b.dataset.e]; saveCsv(e[1], toCsv(e[2](), e[3])); };
  }
  window.addEventListener('beforeprint', () => document.querySelectorAll('details').forEach(d => { d.open = true; }));
  const cnt = document.getElementById('f-count');
  onFilter(() => { cnt.textContent = `${(D.cells || []).filter(c => S.langs.has(c.lang)).length} células · ${opps.filter(o => S.tiers.has(tierOf(o))).length} oportunidades`; })();
  if ('IntersectionObserver' in window) {
    const links = [...document.querySelectorAll('#toc a')];
    const io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) links.forEach(l => l.classList.toggle('on', l.getAttribute('href') === '#' + e.target.id)); }), { rootMargin: '-30% 0px -60% 0px' });
    sections.forEach(s => { const el = document.getElementById(s.id); if (el) io.observe(el); });
  }
})();
