/* SPDX-License-Identifier: GPL-3.0-only
 * Ganttify Python browser enhancements. Calendar calculations deliberately use UTC.
 */
(function (root, factory) {
    'use strict';
    const api = factory();
    if (typeof module === 'object' && module.exports) {
        module.exports = api;
    } else if (root.document && root.Plotly) {
        const el = root.document.getElementById('{plot_id}');
        if (el) api.mount(el, root.Plotly, root);
    }
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
    'use strict';
    const DAY = 86400000;
    const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
        'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const BACKGROUND = 'ganttify-background';
    const FIRST_DATE = Date.parse('0001-01-01T00:00:00Z');
    const LAST_DATE = Date.parse('9999-12-31T23:59:59.999Z');
    const HOVER_SPACING = 8;
    const MAX_HOVER_POINTS = 2000;

    function calendarMillis(year, month, day) {
        const value = new Date(0);
        value.setUTCHours(0, 0, 0, 0);
        value.setUTCFullYear(year, month, day);
        return value.getTime();
    }

    function utcMillis(value) {
        if (typeof value === 'number') return value;
        if (value instanceof Date) return value.getTime();
        if (typeof value !== 'string') return NaN;
        let text = value.trim().replace(' ', 'T');
        if (/^\d{4}-\d\d-\d\d$/.test(text)) text += 'T00:00:00Z';
        else if (/^\d{4}-\d\d-\d\dT/.test(text) && !/(Z|[+-]\d\d:?\d\d)$/i.test(text)) text += 'Z';
        return Date.parse(text);
    }

    function minimumBar(startValue, endValue, range) {
        const start = utcMillis(startValue);
        const end = utcMillis(endValue);
        const extent = Math.abs(utcMillis(range[1]) - utcMillis(range[0]));
        if (![start, end, extent].every(Number.isFinite) || end < start) return null;
        const width = Math.max(end - start, extent * 0.003);
        const base = Math.max(FIRST_DATE, (start + end - width) / 2);
        return {base: new Date(base).toISOString(), width};
    }

    function background(start, end, index) {
        return {type: 'rect', name: BACKGROUND, xref: 'x', yref: 'paper',
            x0: new Date(Math.max(FIRST_DATE, start)).toISOString(),
            x1: new Date(Math.min(LAST_DATE, end)).toISOString(),
            y0: 0, y1: 1, fillcolor: index % 2 === 0 ? 'rgba(240,240,240,0.6)' : 'rgba(255,255,255,0)',
            line: {width: 0}, layer: 'below'};
    }

    function timeline(range, existingShapes) {
        const start = utcMillis(range[0]);
        const end = utcMillis(range[1]);
        if (![start, end].every(Number.isFinite) || end <= start) return null;
        const days = (end - start) / DAY;
        const yearMode = days > 730;
        const monthMode = days > 60 && !yearMode;
        const format = yearMode ? '%Y' : days > 180 ? '%b %Y' : monthMode ? '%b %d' : '%Y-%m-%d';
        const shapes = [];
        const values = [];
        const labels = [];
        const first = new Date(start);
        const last = new Date(end);
        // Adapt the unit to cover the complete range with bounded SVG work.
        // A fixed iteration cutoff silently omitted the later centuries.
        const years = last.getUTCFullYear() - first.getUTCFullYear() + 1;
        const wanted = Math.max(1, Math.ceil(years / 200));
        const power = 10 ** Math.floor(Math.log10(wanted));
        const yearStep = [1, 2, 5, 10].find(value => value * power >= wanted) * power;
        let cursor;
        if (yearMode) cursor = calendarMillis(
            Math.floor((first.getUTCFullYear() - 1) / yearStep) * yearStep + 1, 0, 1);
        else if (monthMode) cursor = calendarMillis(first.getUTCFullYear(), first.getUTCMonth(), 1);
        else cursor = calendarMillis(first.getUTCFullYear(), first.getUTCMonth(), first.getUTCDate() - first.getUTCDay());
        for (let count = 0; cursor <= end && count < 202; count += 1) {
            const current = new Date(cursor);
            let next;
            let midpoint;
            let label;
            let parity;
            if (yearMode) {
                next = calendarMillis(current.getUTCFullYear() + yearStep, 0, 1);
                midpoint = yearStep === 1 ? calendarMillis(current.getUTCFullYear(), 6, 1) :
                    (cursor + Math.min(next, end)) / 2;
                label = String(current.getUTCFullYear());
                if (yearStep > 1) label += '–' + Math.min(9999, current.getUTCFullYear() + yearStep - 1);
                parity = Math.floor((current.getUTCFullYear() - 1) / yearStep);
            } else if (monthMode) {
                next = calendarMillis(current.getUTCFullYear(), current.getUTCMonth() + 1, 1);
                midpoint = calendarMillis(current.getUTCFullYear(), current.getUTCMonth(), 15);
                label = MONTHS[current.getUTCMonth()] + ' ' + (days > 180 ? current.getUTCFullYear() : '15');
                parity = current.getUTCFullYear() * 12 + current.getUTCMonth();
            } else {
                next = cursor + 7 * DAY;
                parity = Math.floor(cursor / (7 * DAY));
            }
            shapes.push(background(cursor, next, parity));
            if (midpoint !== undefined && midpoint >= start && midpoint <= end) {
                values.push(new Date(midpoint).toISOString());
                labels.push(label);
            }
            if (!Number.isFinite(next) || next <= cursor) break;
            cursor = next;
        }
        // Keep every user/renderer shape; only this runtime's own bands are replaceable.
        for (const shape of existingShapes || []) {
            if (shape.name !== BACKGROUND) shapes.push(shape);
        }
        return {format, mode: yearMode || monthMode ? 'array' : 'auto',
            values: values.length ? values : null, labels: labels.length ? labels : null, shapes};
    }

    function normalizeYRange(range, totalRows, maxVisibleRows) {
        const total = Math.max(1, Number(totalRows) || 0);
        const span = Math.min(total, Math.max(1, Number(maxVisibleRows) || total));
        let center = (Number(range[0]) + Number(range[1])) / 2;
        if (!Number.isFinite(center)) center = total + 0.5 - span / 2;
        const lower = Math.max(0.5, Math.min(total + 0.5 - span, center - span / 2));
        return [lower, lower + span];
    }

    function closeRange(a, b) {
        return a && b && Math.abs(a[0] - b[0]) < 0.000001 && Math.abs(a[1] - b[1]) < 0.000001;
    }

    function clearTitle(node) {
        for (const child of Array.from(node.children || [])) {
            if (String(child.tagName).toLowerCase() === 'title') node.removeChild(child);
        }
    }

    function fitLabel(node, full, width, maxChars, bold) {
        const original = String(full || '');
        node.setAttribute('text-anchor', 'start');
        node.setAttribute('x', '4');
        node.style.fontWeight = bold ? 'bold' : '';
        node.style.pointerEvents = 'all';
        if (node.parentNode && node.parentNode.style) node.parentNode.style.pointerEvents = 'all';
        clearTitle(node);
        const match = original.match(/^[\s\u00a0]*/);
        const indent = match ? match[0] : '';
        const body = Array.from(original.slice(indent.length));
        const characterLimit = maxChars == null ? body.length : Math.max(0, Number(maxChars));
        const limit = Math.min(body.length, body.length > characterLimit ? Math.max(0, characterLimit - 1) : characterLimit);
        function measure(text) {
            node.textContent = text;
            try { return node.getComputedTextLength(); } catch (_) { return text.length * 7; }
        }
        const fullWidth = measure(original);
        // Browsers can report zero until SVG text has been laid out; retry afterplot.
        if (fullWidth === 0 && original.trim()) return false;
        let truncated = body.length > limit || fullWidth > width;
        if (truncated) {
            let lo = 0;
            let hi = limit;
            let best = 0;
            while (lo <= hi) {
                const mid = Math.floor((lo + hi) / 2);
                if (measure(indent + body.slice(0, mid).join('') + '…') <= width) {
                    best = mid;
                    lo = mid + 1;
                } else hi = mid - 1;
            }
            const chosen = indent + body.slice(0, best).join('') + '…';
            // Extremely deep indentation must also stay inside the reserved gutter.
            if (measure(chosen) > width) node.textContent = width >= measure('…') ? '…' : '';
            else node.textContent = chosen;
            node.setAttribute('aria-label', original);
            node.setAttribute('data-ganttify-truncated', 'true');
            const title = node.ownerDocument.createElementNS('http://www.w3.org/2000/svg', 'title');
            title.textContent = original;
            node.appendChild(title);
        } else {
            node.textContent = original;
            node.removeAttribute('aria-label');
            node.removeAttribute('data-ganttify-truncated');
        }
        node.setAttribute('data-ganttify-full-label', original);
        return true;
    }

    function alignLabels(el) {
        const layout = el.layout || {};
        const meta = (layout.meta || {}).ganttify || {};
        const axis = layout.yaxis || {};
        const positions = axis.tickvals || [];
        const full = meta.full_labels || [];
        const kinds = meta.row_kinds || [];
        const actualMargin = ((el._fullLayout || {}).margin || {}).l;
        const inputMargin = (layout.margin || {}).l;
        const width = Math.max(0, Number(actualMargin ?? inputMargin ?? meta.gutter_width ?? 300) - 10);
        let nodes = el.querySelectorAll('.yaxislayer-above .ytick text');
        if (!nodes.length) nodes = el.querySelectorAll('.ytick text');
        for (let order = 0; order < nodes.length; order += 1) {
            const node = nodes[order];
            const datum = node.__data__ || (node.parentNode || {}).__data__ || {};
            const index = positions.findIndex(function (position) { return Number(position) === Number(datum.x); });
            const selected = index >= 0 ? index : order;
            let label = full[selected] !== undefined ? full[selected] :
                node.getAttribute('data-ganttify-full-label') || node.textContent;
            const original = meta.rendered_ticktext;
            const current = axis.ticktext;
            if (original && current && current[selected] !== original[selected]) {
                // Plotly already rendered/sanitized the caller's replacement.
                // Cache its complete DOM text before fitting so redraws never
                // restore the generator's stale label or truncate twice.
                const source = String(current[selected] ?? '');
                if (node.getAttribute('data-ganttify-user-source') !== source) {
                    let text = node.textContent || '';
                    for (const child of Array.from(node.children || [])) {
                        if (String(child.tagName).toLowerCase() === 'title' &&
                            text.endsWith(child.textContent || '')) {
                            text = text.slice(0, text.length - (child.textContent || '').length);
                        }
                    }
                    node.setAttribute('data-ganttify-user-source', source);
                    node.setAttribute('data-ganttify-user-label', text);
                }
                label = node.getAttribute('data-ganttify-user-label') || '';
            } else {
                node.removeAttribute('data-ganttify-user-source');
                node.removeAttribute('data-ganttify-user-label');
            }
            fitLabel(node, label, width, meta.label_max_chars, kinds[selected] === 'wbs');
        }
    }

    function evenlySpaced(start, end, count) {
        return Array.from({length: count}, function (_, index) {
            return start + (end - start) * index / (count - 1);
        });
    }

    function hoverSamples(el, trace) {
        const layout = el.layout || {};
        const fullLayout = el._fullLayout || {};
        const meta = (trace.meta || {}).ganttify || {};
        const yRange = (layout.yaxis || {}).range;
        if (!yRange || yRange.length !== 2) return null;
        const lower = Math.min(Number(yRange[0]), Number(yRange[1]));
        const upper = Math.max(Number(yRange[0]), Number(yRange[1]));
        if (![lower, upper].every(Number.isFinite)) return null;
        if (meta.kind === 'milestone-line') {
            const date = meta.date || meta.original_start || (trace.x || [])[0];
            if (!Number.isFinite(utcMillis(date))) return null;
            const height = Number((fullLayout.yaxis || {})._length) || 400;
            const count = Math.min(MAX_HOVER_POINTS, Math.max(2, Math.ceil(height / HOVER_SPACING) + 1));
            return {x: Array(count).fill(date), y: evenlySpaced(lower, upper, count)};
        }
        if (meta.kind !== 'milestone-area') return null;
        const originalStart = utcMillis(meta.original_start || (trace.x || [])[0]);
        const originalEnd = utcMillis(meta.original_end || (trace.x || []).at(-1));
        const xRange = (layout.xaxis || {}).range;
        if (!xRange || xRange.length !== 2) return null;
        const rangeStart = Math.min(utcMillis(xRange[0]), utcMillis(xRange[1]));
        const rangeEnd = Math.max(utcMillis(xRange[0]), utcMillis(xRange[1]));
        if (![originalStart, originalEnd, rangeStart, rangeEnd].every(Number.isFinite) ||
            rangeEnd <= rangeStart || originalEnd < originalStart) return null;
        const start = Math.max(originalStart, rangeStart);
        const end = Math.min(originalEnd, rangeEnd);
        const edge = meta.label_position === 'bottom' ? lower :
            meta.label_position === 'middle' ? (lower + upper) / 2 : upper;
        if (end < start) {
            // Keep original hover text available while the area is off screen.
            return {x: [originalStart, originalEnd].map(value => new Date(value).toISOString()),
                y: [edge, edge]};
        }
        const width = Number((fullLayout.xaxis || {})._length) || 800;
        const visibleWidth = width * (end - start) / (rangeEnd - rangeStart);
        const count = Math.min(MAX_HOVER_POINTS, Math.max(2, Math.ceil(visibleWidth / HOVER_SPACING) + 1));
        return {x: evenlySpaced(start, end, count).map(value => new Date(value).toISOString()),
            y: Array(count).fill(edge)};
    }

    function samePoints(first, second) {
        return first && first.length === second.length && second.every(function (value, index) {
            return typeof value === 'number' ? Math.abs(Number(first[index]) - value) < 0.000001 :
                utcMillis(first[index]) === utcMillis(value);
        });
    }

    function geometryKey(el) {
        const layout = el.layout || {};
        const full = el._fullLayout || {};
        return JSON.stringify([(layout.yaxis || {}).range,
            (full.xaxis || {})._length, (full.yaxis || {})._length]);
    }

    function mount(el, Plotly, host) {
        if (el.__ganttifyRuntime) return el.__ganttifyRuntime;
        const env = host || (typeof globalThis !== 'undefined' ? globalThis : {});
        const schedule = env.setTimeout ? env.setTimeout.bind(env) : setTimeout;
        const cancel = env.clearTimeout ? env.clearTimeout.bind(env) : clearTimeout;
        const state = {internal: 0, destroyed: false, pending: false, running: null,
            timer: null, lastRangeKey: null, lastGeometryKey: null, lastError: null};
        const handlers = [];

        function guarded(operation) {
            state.internal += 1;
            return Promise.resolve().then(operation).finally(function () { state.internal -= 1; });
        }

        function dateAxes(layout) {
            const axes = {'xaxis.type': 'date'};
            const range = (layout.xaxis || {}).range;
            if (range && range.length === 2) {
                axes['xaxis.range'] = range.slice();
                axes['xaxis.autorange'] = false;
            }
            if (layout.xaxis2) {
                axes['xaxis2.type'] = 'date';
                if (range && range.length === 2) {
                    axes['xaxis2.range'] = range.slice();
                    axes['xaxis2.autorange'] = false;
                }
            }
            return axes;
        }

        async function updateMilestoneHover() {
            const indices = [];
            const xUpdates = [];
            const yUpdates = [];
            const hoverUpdates = [];
            const customUpdates = [];
            for (let i = 0; i < (el.data || []).length; i += 1) {
                const trace = el.data[i];
                const points = hoverSamples(el, trace);
                if (!points || (samePoints(trace.x, points.x) && samePoints(trace.y, points.y))) continue;
                const hover = Array.isArray(trace.hovertext) ? trace.hovertext[0] : trace.hovertext;
                const custom = trace.customdata && trace.customdata[0];
                indices.push(i);
                xUpdates.push(points.x);
                yUpdates.push(points.y);
                hoverUpdates.push(Array(points.x.length).fill(hover || ''));
                customUpdates.push(custom === undefined ? null : Array(points.x.length).fill(custom));
            }
            if (indices.length) {
                const axes = dateAxes(el.layout || {});
                await guarded(function () { return Plotly.update(el,
                    {x: xUpdates, y: yUpdates, hovertext: hoverUpdates, customdata: customUpdates}, axes, indices); });
            }
        }

        async function refreshOnce() {
            if (state.destroyed) return;
            await updateMilestoneHover();
            const layout = el.layout || {};
            const sourceRange = (layout.xaxis || {}).range;
            if (!sourceRange || sourceRange.length !== 2) { alignLabels(el); return; }
            const range = sourceRange.slice();
            const indices = [];
            const widths = [];
            const bases = [];
            for (let i = 0; i < (el.data || []).length; i += 1) {
                const trace = el.data[i];
                const meta = (trace.meta || {}).ganttify;
                if (!meta || meta.kind !== 'bar') continue;
                const bar = minimumBar(meta.start, meta.end, range);
                if (!bar) continue;
                const oldWidth = trace.x && Number(trace.x[0]);
                const oldBase = trace.base && utcMillis(Array.isArray(trace.base) ? trace.base[0] : trace.base);
                if (Math.abs(oldWidth - bar.width) < 0.001 && Math.abs(oldBase - utcMillis(bar.base)) < 0.5) continue;
                indices.push(i);
                widths.push([bar.width]);
                bases.push([bar.base]);
            }
            if (indices.length) {
                // Restyling numeric bar durations alone makes Plotly infer a linear x axis.
                // Apply trace data and the explicit date type/range atomically.
                const axes = dateAxes(layout);
                await guarded(function () { return Plotly.update(el, {x: widths, base: bases}, axes, indices); });
            }
            const rangeKey = JSON.stringify(range);
            if (rangeKey !== state.lastRangeKey) {
                const style = timeline(range, layout.shapes);
                if (style) {
                    const update = {...dateAxes(layout), 'xaxis.tickformat': style.format, 'xaxis.tickmode': style.mode,
                        'xaxis.tickvals': style.values, 'xaxis.ticktext': style.labels, shapes: style.shapes};
                    if (layout.xaxis2) {
                        update['xaxis2.type'] = 'date';
                        update['xaxis2.tickformat'] = style.format;
                        update['xaxis2.tickmode'] = style.mode;
                        update['xaxis2.tickvals'] = style.values;
                        update['xaxis2.ticktext'] = style.labels;
                    }
                    await guarded(function () { return Plotly.relayout(el, update); });
                }
                state.lastRangeKey = rangeKey;
            }
            alignLabels(el);
            state.lastGeometryKey = geometryKey(el);
        }

        function refresh() {
            state.pending = true;
            if (!state.running) {
                state.running = (async function () {
                    while (state.pending && !state.destroyed) {
                        state.pending = false;
                        await refreshOnce();
                    }
                }()).catch(function (error) {
                    state.lastError = error;
                    if (env.console && env.console.warn) env.console.warn('Ganttify could not update chart interactions.', error);
                }).finally(function () { state.running = null; });
            }
            return state.running;
        }

        function requestRefresh() {
            if (state.timer !== null) cancel(state.timer);
            state.timer = schedule(function () { state.timer = null; refresh(); }, 30);
        }

        function onRelayout(event) {
            if (state.internal || state.destroyed || (el._context || {}).staticPlot) return;
            const change = event || {};
            if (Object.keys(change).some(function (key) { return /^xaxis2?\.(range|autorange)/.test(key); })) requestRefresh();
            if (Object.keys(change).some(function (key) { return /^yaxis\.(range|autorange)/.test(key); })) {
                const layout = el.layout || {};
                const meta = (layout.meta || {}).ganttify || {};
                const current = (layout.yaxis || {}).range || [0.5, 1.5];
                const requested = change['yaxis.range'] || [
                    change['yaxis.range[0]'] !== undefined ? change['yaxis.range[0]'] : current[0],
                    change['yaxis.range[1]'] !== undefined ? change['yaxis.range[1]'] : current[1]];
                const corrected = normalizeYRange(requested, meta.total_rows, meta.max_visible_rows);
                if (!closeRange(requested, corrected) || change['yaxis.autorange']) {
                    guarded(function () { return Plotly.relayout(el, {'yaxis.range': corrected, 'yaxis.autorange': false}); }).then(refresh);
                } else {
                    requestRefresh();
                }
            }
        }

        function onAfterplot() {
            if (state.destroyed) return;
            alignLabels(el);
            if (!state.internal && !state.running && geometryKey(el) !== state.lastGeometryKey) requestRefresh();
        }

        function onWheel(event) {
            const layout = el.layout || {};
            const meta = (layout.meta || {}).ganttify || {};
            if (state.destroyed || (el._context || {}).staticPlot || event.ctrlKey || event.metaKey || event.shiftKey ||
                Math.abs(event.deltaX || 0) > Math.abs(event.deltaY || 0) || !event.deltaY ||
                meta.total_rows <= meta.max_visible_rows) return;
            if (event.preventDefault) event.preventDefault();
            const range = (layout.yaxis || {}).range || [0.5, 1.5];
            const span = Math.min(meta.total_rows, meta.max_visible_rows);
            const factor = event.deltaMode === 2 ? span : event.deltaMode === 1 ? 1 : 1 / 40;
            const delta = event.deltaY * factor;
            const corrected = normalizeYRange([range[0] - delta, range[1] - delta], meta.total_rows, meta.max_visible_rows);
            if (!closeRange(range, corrected)) {
                guarded(function () { return Plotly.relayout(el, {'yaxis.range': corrected}); }).then(refresh);
            }
        }

        function bind(name, handler) {
            if (el.on) { el.on(name, handler); handlers.push([name, handler]); }
        }
        if (!(el._context || {}).staticPlot) bind('plotly_relayout', onRelayout);
        bind('plotly_afterplot', onAfterplot);
        if (el.addEventListener && !(el._context || {}).staticPlot) {
            el.addEventListener('wheel', onWheel, {passive: false});
        }
        const controller = {refresh, state, destroy: function () {
            state.destroyed = true;
            if (state.timer !== null) cancel(state.timer);
            for (const pair of handlers) if (el.removeListener) el.removeListener(pair[0], pair[1]);
            if (el.removeEventListener) el.removeEventListener('wheel', onWheel);
            delete el.__ganttifyRuntime;
        }};
        el.__ganttifyRuntime = controller;
        requestRefresh();
        return controller;
    }

    return Object.freeze({utcMillis, minimumBar, timeline, normalizeYRange, fitLabel, alignLabels,
        hoverSamples, mount});
}));
