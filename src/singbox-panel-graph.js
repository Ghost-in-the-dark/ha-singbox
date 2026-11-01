/**
 * Traffic chart for the sing-box panel card.
 *
 * Drawn as inline SVG inside the card's shadow DOM: no canvas sizing dance,
 * no extra dependency, and the colours come from Home Assistant CSS variables
 * so light/dark themes work without extra code.
 *
 * Two details matter for correctness:
 *
 *  * Every SVG element is built with Lit's `svg` tag. Nested `html` templates
 *    inside an <svg> create XHTML-namespaced elements in the wrong namespace —
 *    they parse, are present in the DOM, and are simply never painted.
 *  * The viewBox is a normalized 0..100 square and the SVG is stretched to the
 *    card width with preserveAspectRatio="none", so every stroked element sets
 *    vector-effect="non-scaling-stroke" to keep the line width honest.
 */

import { svg } from "lit";

// Horizontal grid lines (y in the 0..100 viewBox): baseline, quarter, half, top.
const GRID_LINES = [0, 25, 50, 75, 100];

function clamp(value, min, max) {
    return Math.min(Math.max(Number(value) || 0, min), max);
}

/**
 * Round the scale ceiling up to a readable value (1, 2, 2.5 or 5 × 10^n).
 *
 * Scaling to the raw peak makes every sample touch the top of the plot and a
 * single spike flatten the rest. A rounded ceiling leaves headroom and keeps
 * the grid meaningful, which matters most on a link that is mostly idle.
 */
export function niceCeiling(peak) {
    if (!(peak > 0)) return 1;
    const magnitude = 10 ** Math.floor(Math.log10(peak));
    const normalized = peak / magnitude;
    const step = normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 2.5 ? 2.5 : normalized <= 5 ? 5 : 10;
    return step * magnitude;
}

/** Map a series to "x,y x,y ..." points in the 0..100 viewBox. */
function linePoints(samples, startMs, endMs, max) {
    const span = Math.max(endMs - startMs, 1);
    return samples
        .map((s) => {
            const x = clamp(((s.t - startMs) / span) * 100, 0, 100);
            const y = 100 - (clamp(s.v, 0, max) / max) * 100;
            return `${x.toFixed(2)},${y.toFixed(2)}`;
        })
        .join(" ");
}

/** Same series, closed on the baseline, for the filled area under the line. */
function fillPoints(samples, startMs, endMs, max) {
    if (samples.length === 0) return "";
    const span = Math.max(endMs - startMs, 1);
    const first = samples[0];
    const last = samples[samples.length - 1];
    const x0 = clamp(((first.t - startMs) / span) * 100, 0, 100);
    const x1 = clamp(((last.t - startMs) / span) * 100, 0, 100);
    const body = linePoints(samples, startMs, endMs, max);
    return `${x0.toFixed(2)},100 ${body} ${x1.toFixed(2)},100`;
}

/**
 * Render the traffic chart.
 *
 * @param {object} options
 * @param {Array<{t:number, up:number, down:number}>} options.samples samples in window order
 * @param {number} options.startMs window start (epoch ms)
 * @param {number} options.endMs window end (epoch ms)
 * @param {string} options.emptyText message shown while there is no history yet
 * @param {string} options.peakText caption rendered above the chart
 * @returns {import("lit").TemplateResult}
 */
export function renderTrafficChart({
    samples,
    startMs,
    endMs,
    emptyText,
    peakText,
    scaleText = "",
}) {
    // One point is a dot with no line — treat it as "not enough history yet"
    // so the card does not flash a chart on the very first sample.
    const hasData = samples.length > 1;
    const peak = samples.reduce(
        (acc, s) => Math.max(acc, s.up || 0, s.down || 0),
        0
    );
    // An idle link is flat zero; without a floor the scale would divide by zero.
    const max = niceCeiling(peak);
    const upSeries = samples.map((s) => ({ t: s.t, v: s.up || 0 }));
    const downSeries = samples.map((s) => ({ t: s.t, v: s.down || 0 }));

    return svg`
        <div class="chart">
            <div class="chart-head">
                <span class="chart-peak">${peakText}</span>
                ${hasData && scaleText
                    ? svg`<span class="chart-scale">${scaleText}</span>`
                    : ""}
            </div>
            <svg
                class="chart-svg"
                viewBox="0 0 100 100"
                preserveAspectRatio="none"
                role="img"
                aria-label=${peakText}
            >
                ${GRID_LINES.map(
                    (y) => svg`<line
                        class="chart-grid"
                        x1="0"
                        y1=${y}
                        x2="100"
                        y2=${y}
                        vector-effect="non-scaling-stroke"
                    ></line>`
                )}
                ${hasData
                    ? svg`
                          <polygon
                              class="chart-fill down"
                              points=${fillPoints(
                                  downSeries,
                                  startMs,
                                  endMs,
                                  max
                              )}
                          ></polygon>
                          <polyline
                              class="chart-line down"
                              points=${linePoints(
                                  downSeries,
                                  startMs,
                                  endMs,
                                  max
                              )}
                              vector-effect="non-scaling-stroke"
                          ></polyline>
                          <polygon
                              class="chart-fill up"
                              points=${fillPoints(upSeries, startMs, endMs, max)}
                          ></polygon>
                          <polyline
                              class="chart-line up"
                              points=${linePoints(
                                  upSeries,
                                  startMs,
                                  endMs,
                                  max
                              )}
                              vector-effect="non-scaling-stroke"
                          ></polyline>
                      `
                    : ""}
            </svg>
            ${hasData ? "" : svg`<div class="chart-empty">${emptyText}</div>`}
        </div>
    `;
}