/* Run with: node --test tests/test_runtime.mjs */
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import test from 'node:test';
const require = createRequire(import.meta.url);
const runtime = require('../src/ganttify/assets/runtime.js');
const DAY = 86400000;

function fixture() {
    const events = new Map();
    const wheel = new Map();
    const counters = {restyle: 0, relayout: 0, update: 0};
    const el = {
        layout: {xaxis: {type: 'date', range: ['2025-01-01', '2026-01-01']}, xaxis2: {type: 'date'},
            yaxis: {range: [80.5, 100.5], tickvals: []}, margin: {l: 300},
            shapes: [{name: 'custom', type: 'line'}],
            meta: {ganttify: {total_rows: 100, max_visible_rows: 20, full_labels: [], row_kinds: []}}},
        data: [{x: [0], base: ['2025-01-02'], meta: {ganttify: {kind: 'bar', start: '2025-01-02', end: '2025-01-02'}}}],
        on(name, handler) { if (!events.has(name)) events.set(name, []); events.get(name).push(handler); },
        removeListener(name, handler) { events.set(name, (events.get(name) || []).filter(item => item !== handler)); },
        addEventListener(name, handler) { wheel.set(name, handler); },
        removeEventListener(name) { wheel.delete(name); },
        querySelectorAll() { return []; },
    };
    function emit(name, payload) { for (const handler of events.get(name) || []) handler(payload); }
    const Plotly = {
        async update(target, data, layout, indices) {
            counters.update += 1;
            indices.forEach((index, order) => {
                for (const [field, values] of Object.entries(data)) target.data[index][field] = values[order];
            });
            // Plotly's trace-data update re-infers numeric durations as a linear
            // axis; only the atomic layout part keeps the explicit date axis.
            target.layout.xaxis.type = 'linear';
            for (const [key, value] of Object.entries(layout)) {
                const [axis, field] = key.split('.');
                target.layout[axis][field] = value;
            }
            emit('plotly_relayout', layout);
            emit('plotly_afterplot');
        },
        async restyle(target, update, indices) {
            counters.restyle += 1;
            indices.forEach((index, order) => {
                for (const [field, values] of Object.entries(update)) target.data[index][field] = values[order];
            });
            emit('plotly_afterplot');
        },
        async relayout(target, update) {
            counters.relayout += 1;
            for (const [key, value] of Object.entries(update)) {
                if (key.includes('.')) {
                    const [axis, field] = key.split('.');
                    target.layout[axis][field] = value;
                } else target.layout[key] = value;
            }
            emit('plotly_relayout', update);
            emit('plotly_afterplot');
        },
    };
    let timer = 0;
    const timers = new Map();
    const host = {setTimeout(callback) { timers.set(++timer, callback); return timer; }, clearTimeout(id) { timers.delete(id); }};
    return {el, Plotly, counters, host, events, wheel, emit};
}

function textNode() {
    const attributes = new Map();
    const children = [];
    let text = '';
    return {
        style: {}, parentNode: {style: {}}, children,
        ownerDocument: {createElementNS(_ns, tag) { return {tagName: tag, textContent: ''}; }},
        get textContent() { return text + children.map(child => child.textContent).join(''); },
        set textContent(value) { text = value; children.length = 0; },
        setAttribute(key, value) { attributes.set(key, String(value)); },
        getAttribute(key) { return attributes.get(key) ?? null; },
        removeAttribute(key) { attributes.delete(key); },
        appendChild(child) { children.push(child); },
        removeChild(child) { children.splice(children.indexOf(child), 1); },
        getComputedTextLength() { return Array.from(text).length * 7; },
        visible() { return text; },
    };
}

test('minimum width keeps fractional dates and is based on original endpoints', () => {
    const bar = runtime.minimumBar('2025-01-02', '2025-01-02', ['2025-01-01', '2025-01-11']);
    assert.equal(bar.width, DAY * 10 * 0.003);
    assert.equal(runtime.utcMillis(bar.base) + bar.width / 2, runtime.utcMillis('2025-01-02'));
    assert.notEqual(bar.base.slice(11, 19), '00:00:00');
    assert.equal(runtime.utcMillis('2025-01-01 12:30:00'), Date.UTC(2025, 0, 1, 12, 30));
    const original = runtime.minimumBar('2025-01-02', '2025-01-03', ['2025-01-01', '2025-01-11']);
    assert.equal(original.width, DAY);
    assert.equal(original.base, '2025-01-02T00:00:00.000Z');
});

test('year-one dates stay in the supported Python calendar', () => {
    const bar = runtime.minimumBar('0001-01-01', '0001-01-01', ['0001-01-01', '0001-02-01']);
    assert.equal(bar.base, '0001-01-01T00:00:00.000Z');
    const bands = runtime.timeline(['0001-01-01', '0001-05-01'], []);
    assert.equal(bands.values[0], '0001-01-15T00:00:00.000Z');
});

test('calendar bands use UTC and preserve arbitrary shapes on every update', () => {
    const custom = {type: 'rect', name: 'external', x0: '2025-01-01'};
    const milestone = {type: 'rect', name: 'ganttify-milestone'};
    const monthly = runtime.timeline(['2025-01-01', '2025-05-01'], [custom, milestone]);
    assert.equal(monthly.mode, 'array');
    assert.equal(monthly.format, '%b %d');
    assert.equal(monthly.values[0], '2025-01-15T00:00:00.000Z');
    assert.equal(monthly.labels[0], 'Jan 15');
    const again = runtime.timeline(['2025-01-01', '2025-05-01'], monthly.shapes);
    assert.equal(again.shapes.length, monthly.shapes.length);
    assert.equal(again.shapes.filter(shape => shape.name === 'external').length, 1);
    assert.equal(again.shapes.filter(shape => shape.name === 'ganttify-milestone').length, 1);
    const weekly = runtime.timeline(['2025-03-09', '2025-03-25'], []);
    assert.equal(weekly.shapes[0].x0, '2025-03-09T00:00:00.000Z');
    assert.equal(runtime.utcMillis(weekly.shapes[0].x1) - runtime.utcMillis(weekly.shapes[0].x0), 7 * DAY);
    assert.equal(runtime.timeline(['2024-01-01', '2028-01-01'], []).format, '%Y');
});

test('range normalization prevents vertical zoom and clamps the viewport', () => {
    assert.deepEqual(runtime.normalizeYRange([90, 110], 100, 20), [80.5, 100.5]);
    assert.deepEqual(runtime.normalizeYRange([-50, -40], 100, 20), [0.5, 20.5]);
    assert.deepEqual(runtime.normalizeYRange([40, 41], 100, 20), [30.5, 50.5]);
    assert.deepEqual(runtime.normalizeYRange([0, 100], 3, 20), [0.5, 3.5]);
});

test('labels preserve full text, indentation, Unicode, bold and one native tooltip', () => {
    const node = textNode();
    const original = '\u00a0\u00a0Long project title 🚄 with all text';
    runtime.fitLabel(node, original, 90, null, true);
    assert.ok(node.visible().startsWith('\u00a0\u00a0'));
    assert.ok(node.visible().endsWith('…'));
    assert.equal(node.children.length, 1);
    assert.equal(node.children[0].textContent, original);
    assert.equal(node.getAttribute('aria-label'), original);
    assert.equal(node.style.fontWeight, 'bold');
    runtime.fitLabel(node, original, 90, null, true);
    assert.equal(node.children.length, 1);
    assert.equal(node.getAttribute('data-ganttify-full-label'), original);
    runtime.fitLabel(node, original, 900, null, true);
    assert.equal(node.visible(), original);
    assert.equal(node.children.length, 0);
    assert.equal(node.getAttribute('aria-label'), null);
});

test('character truncation retains the original string for accessibility', () => {
    const node = textNode();
    runtime.fitLabel(node, 'ABCDE🚄FG', 900, 6, false);
    assert.equal(node.visible(), 'ABCDE…');
    assert.equal(node.children[0].textContent, 'ABCDE🚄FG');
});

test('initial updates are idempotent, synchronize axes and avoid event loops', async () => {
    const f = fixture();
    const controller = runtime.mount(f.el, f.Plotly, f.host);
    assert.equal(runtime.mount(f.el, f.Plotly, f.host), controller);
    await controller.refresh();
    assert.equal(f.counters.update, 1);
    assert.equal(f.counters.relayout, 1);
    assert.equal(f.el.layout.xaxis.type, 'date');
    assert.equal(f.el.layout.xaxis2.type, 'date');
    assert.equal(f.el.layout.xaxis2.tickformat, f.el.layout.xaxis.tickformat);
    const width = f.el.data[0].x[0];
    await controller.refresh();
    assert.equal(f.counters.update, 1);
    assert.equal(f.counters.relayout, 1);
    f.el.layout.xaxis.range = ['2025-01-01', '2025-01-11'];
    await controller.refresh();
    assert.ok(f.el.data[0].x[0] < width);
    assert.equal(f.el.layout.xaxis.type, 'date');
    assert.equal(f.el.layout.xaxis2.type, 'date');
    assert.deepEqual(f.el.layout.xaxis.range, ['2025-01-01', '2025-01-11']);
    assert.equal(f.el.data[0].meta.ganttify.start, '2025-01-02');
    assert.equal(controller.state.lastError, null);
    controller.destroy();
    assert.equal(f.wheel.size, 0);
    assert.equal(f.events.get('plotly_relayout').length, 0);
});

test('wheel scrolling retains row count, clamps, and permits browser zoom gestures', async () => {
    const f = fixture();
    const controller = runtime.mount(f.el, f.Plotly, f.host);
    let prevented = 0;
    f.wheel.get('wheel')({deltaY: 4000, deltaX: 0, deltaMode: 0, preventDefault() { prevented += 1; }});
    await Promise.resolve();
    await Promise.resolve();
    assert.deepEqual(f.el.layout.yaxis.range, [0.5, 20.5]);
    assert.equal(prevented, 1);
    const previous = f.counters.relayout;
    f.wheel.get('wheel')({deltaY: 10, ctrlKey: true, preventDefault() { prevented += 1; }});
    await Promise.resolve();
    assert.equal(f.counters.relayout, previous);
    assert.equal(prevented, 1);
    controller.destroy();
});

test('user vertical zoom is corrected without relayout recursion', async () => {
    const f = fixture();
    const controller = runtime.mount(f.el, f.Plotly, f.host);
    f.el.layout.yaxis.range = [40, 41];
    f.emit('plotly_relayout', {'yaxis.range[0]': 40, 'yaxis.range[1]': 41});
    await Promise.resolve();
    await Promise.resolve();
    assert.deepEqual(f.el.layout.yaxis.range, [30.5, 50.5]);
    assert.ok(f.counters.relayout >= 1);
    controller.destroy();
});

test('visible ticks resolve full text by numeric tick position, including hidden labels', () => {
    const node = textNode();
    node.__data__ = {x: 5};
    const el = {
        layout: {margin: {l: 150}, yaxis: {tickvals: [100, 5, 1]},
            meta: {ganttify: {full_labels: ['Wrong label', '\u00a0\u00a0Actual visible row full name', ''],
                row_kinds: ['wbs', 'activity', 'activity'], label_max_chars: 10}}},
        querySelectorAll() { return [node]; },
    };
    runtime.alignLabels(el);
    assert.equal(node.children[0].textContent, '\u00a0\u00a0Actual visible row full name');
    assert.equal(node.style.fontWeight, '');
    node.__data__.x = 1;
    runtime.alignLabels(el);
    assert.equal(node.visible(), '');
    assert.equal(node.children.length, 0);
});


test('milestone area hover markers follow viewport edges during scrolling', async () => {
    const f = fixture();
    for (const position of ['top', 'middle', 'bottom']) {
        f.el.data.push({x: ['2025-01-01', '2025-01-02'], y: [-1, -1],
            meta: {ganttify: {kind: 'milestone-area', label_position: position}}});
    }
    const controller = runtime.mount(f.el, f.Plotly, f.host);
    await controller.refresh();
    assert.deepEqual(f.el.data[1].y, [100.5, 100.5]);
    assert.deepEqual(f.el.data[2].y, [90.5, 90.5]);
    assert.deepEqual(f.el.data[3].y, [80.5, 80.5]);
    f.wheel.get('wheel')({deltaY: 4000, deltaMode: 0, preventDefault() {}});
    // A wheel relayout invokes the guarded refresh automatically.
    await new Promise(resolve => setImmediate(resolve));
    assert.deepEqual(f.el.data[1].y, [20.5, 20.5]);
    assert.deepEqual(f.el.data[2].y, [10.5, 10.5]);
    assert.deepEqual(f.el.data[3].y, [0.5, 0.5]);
    const changes = f.counters.update;
    await controller.refresh();
    assert.equal(f.counters.update, changes);
    assert.equal(controller.state.lastError, null);
    controller.destroy();
});
