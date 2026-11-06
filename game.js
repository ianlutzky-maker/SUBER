"use strict";

const $ = (id) => document.getElementById(id);
const { routes, streets, avenues, boundary, coastMap } = window.suberData;
const prize = window.premioSubeR;
const roundMix = { colectivo: 6, tren: 2, subte: 2 };
const rounds = Object.values(roundMix).reduce((total, count) => total + count, 0);
const catalog = Object.fromEntries(Object.keys(roundMix).map((mode) => [
  mode, routes.filter((entry) => entry.modo === mode)
]));
const soundtrack = $("soundtrack");
let musicEnabled = true;
soundtrack.volume = 0.5;
const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)");
const canvas = $("map");
const context = canvas.getContext("2d");
const fingers = new Map();
let deck, positions, index, answers, route, phase;
let view, animation, width, height, pixelRatio, fraction;
let pathSections, totalLength;

function shuffle(values) {
  const result = [...values];
  for (let i = result.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [result[i], result[j]] = [result[j], result[i]];
  }
  return result;
}

function updateMusic() {
  $("music-toggle").setAttribute("aria-pressed", String(musicEnabled));
  $("music-toggle").textContent = musicEnabled ? "♫ Música" : "♫ Silenciada";
}

function playMusic() {
  if (!musicEnabled) return;
  soundtrack.play().catch((error) => {
    if (error.name === "AbortError" || $("game").hidden || !musicEnabled) return;
    musicEnabled = false;
    updateMusic();
  });
}

function start() {
  deck = shuffle(Object.entries(roundMix).flatMap(([mode, count]) => shuffle(catalog[mode]).slice(0, count)));
  positions = shuffle([0, 1, 2, 3, 0, 1, 2, 3, ...shuffle([0, 1, 2, 3]).slice(0, 2)]);
  index = 0;
  answers = [];
  $("home").hidden = true;
  $("result").hidden = true;
  $("game").hidden = false;
  updateMusic();
  playMusic();
  showRound();
}

function renderProgress() {
  $("round").textContent = `Ronda ${index + 1} de ${rounds}`;
  $("score").textContent = `Aciertos ${answers.filter(Boolean).length}/${rounds}`;
  $("progress").replaceChildren(...Array.from({ length: rounds }, (_, i) => {
    const segment = document.createElement("i");
    segment.className = i < answers.length ? (answers[i] ? "hit" : "miss") : i === index ? "current" : "";
    return segment;
  }));
}

function showRound() {
  route = deck[index];
  phase = "drawing";
  fraction = 0;
  renderProgress();
  $("question").focus({ preventScroll: true });
  $("status").textContent = "";
  $("map-status").textContent = "Dibujando recorrido";
  $("next").firstChild.textContent = index === rounds - 1 ? "Ver resultado " : "Siguiente recorrido ";
  $("next").disabled = true;
  const choices = shuffle(catalog[route.modo].filter((entry) => entry.linea !== route.linea)).slice(0, 3);
  choices.splice(positions[index], 0, route);
  $("options").replaceChildren(...choices.map(({ linea }) => {
    const button = document.createElement("button");
    button.className = "option";
    if (route.modo === "tren" || linea === "Premetro") button.classList.add("named-option");
    button.dataset.linea = String(linea);
    button.disabled = true;
    button.setAttribute("aria-label", choiceLabel(linea));
    button.textContent = linea;
    button.addEventListener("click", () => answer(linea));
    return button;
  }));
  totalLength = 0;
  pathSections = route.geometry.coordinates.map((line) => line.map(([lon, lat], i) => {
    const x = (lon + 58.55) * 91650;
    const y = (-34.51 - lat) * 111320;
    if (i) totalLength += Math.hypot(x - (line[i - 1][0] + 58.55) * 91650, y - (-34.51 - line[i - 1][1]) * 111320);
    return { x, y, distance: totalLength };
  }));
  resize();
  cancelAnimationFrame(animation);
  const duration = reducedMotion.matches ? 0 : 2600;
  const began = performance.now();
  function advance(now) {
    fraction = duration ? Math.min(1, (now - began) / duration) : 1;
    draw();
    if (fraction < 1) {
      animation = requestAnimationFrame(advance);
      return;
    }
    phase = "ready";
    $("map-status").textContent = "Recorrido completo";
    for (const button of $("options").children) button.disabled = false;
  }
  animation = requestAnimationFrame(advance);
}

function choiceLabel(linea) {
  if (route.modo === "tren") return linea === "Tren de la Costa" ? linea : `Tren ${linea}`;
  if (linea === "Premetro") return linea;
  return `Línea ${linea}`;
}

function answer(linea) {
  if (phase !== "ready") return;
  phase = "answered";
  const hit = linea === route.linea;
  answers.push(hit);
  for (const button of $("options").children) {
    const value = button.dataset.linea;
    button.disabled = true;
    if (value === String(route.linea)) mark(button, value, "right", "✓", hit ? "Correcta" : "Era esta");
    else if (value === String(linea)) mark(button, value, "wrong", "×", "Tu opción");
  }
  $("status").textContent = hit ? "¡Acertaste!" : `Era ${choiceLabel(route.linea)}.`;
  renderProgress();
  $("next").disabled = false;
  $("next").focus({ preventScroll: true });
}

function mark(button, number, style, icon, label) {
  button.classList.add(style);
  button.setAttribute("aria-label", `${choiceLabel(number)}. ${label}`);
  const badge = document.createElement("small");
  const symbol = document.createElement("b");
  symbol.textContent = icon;
  symbol.setAttribute("aria-hidden", "true");
  badge.append(symbol, ` ${label}`);
  button.append(badge);
}

function next() {
  if (phase !== "answered") return;
  if (++index < rounds) showRound();
  else showResult();
}

function showResult() {
  phase = "finished";
  $("game").hidden = true;
  soundtrack.pause();
  soundtrack.currentTime = 0;
  const score = answers.filter(Boolean).length;
  const won = score === rounds;
  $("result").hidden = false;
  $("result-icon").textContent = `${score}/10`;
  $("result-title").textContent = won ? "¡Sos un capo de la SubeR!" : `Pegaste ${score} de 10`;
  $("reward").hidden = !won;
  const code = won ? prize.codigoConfirmado.trim() : "";
  $("coupon").hidden = !code;
  $("code").textContent = code;
  $("reward-details").textContent = won ? [prize.monto, prize.vigencia, prize.condiciones].filter(Boolean).join(" · ") : "";
  $("copy-status").textContent = "";
  $("result-title").focus();
}

const minorRoads = new Path2D(streets);
const majorRoads = new Path2D(avenues);
const city = new Path2D(boundary);
const coastRoads = new Path2D(coastMap.streets);
const coastAvenues = new Path2D(coastMap.avenues);

function resize() {
  const bounds = canvas.getBoundingClientRect();
  if (!bounds.width || !route) return;
  width = bounds.width;
  height = bounds.height;
  pixelRatio = Math.min(devicePixelRatio || 1, 2);
  canvas.width = Math.round(width * pixelRatio);
  canvas.height = Math.round(height * pixelRatio);
  fit();
}

function fit() {
  const points = pathSections.flat();
  const xs = points.map((point) => point.x);
  const ys = points.map((point) => point.y);
  const [left, right, top, bottom] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
  const scale = Math.min((width - 96) / Math.max(1, right - left), (height - 84) / Math.max(1, bottom - top), .8);
  view = { scale, base: scale, x: width / 2 - scale * (left + right) / 2, y: height / 2 - scale * (top + bottom) / 2 };
  draw();
}

function draw() {
  context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
  const onCoast = route.mapa === "costa";
  context.fillStyle = onCoast ? "#fff" : "#f0f2f3";
  context.fillRect(0, 0, width, height);
  context.translate(view.x, view.y);
  context.scale(view.scale, view.scale);
  context.fillStyle = "#ffffff";
  if (!onCoast) context.fill(city, "evenodd");
  context.strokeStyle = "#e0e2e4";
  context.lineWidth = 0.8 / view.scale;
  context.stroke(onCoast ? coastRoads : minorRoads);
  context.strokeStyle = "#33363a";
  context.lineWidth = 0.65 / view.scale;
  context.stroke(onCoast ? coastAvenues : majorRoads);

  const limit = fraction * totalLength;
  let head = pathSections[0][0];
  context.beginPath();
  for (const line of pathSections) {
    if (line[0].distance > limit) break;
    context.moveTo(line[0].x, line[0].y);
    head = line[0];
    for (const point of line.slice(1)) {
      if (point.distance > limit) {
        const amount = (limit - head.distance) / (point.distance - head.distance);
        head = { x: head.x + (point.x - head.x) * amount, y: head.y + (point.y - head.y) * amount };
        context.lineTo(head.x, head.y);
        break;
      }
      head = point;
      context.lineTo(head.x, head.y);
    }
  }
  context.lineJoin = "round";
  context.lineCap = "round";
  context.strokeStyle = "#fff";
  context.lineWidth = 10 / view.scale;
  context.stroke();
  context.strokeStyle = route.color;
  context.lineWidth = 6 / view.scale;
  context.stroke();
  context.beginPath();
  context.arc(head.x, head.y, (fraction < 1 ? 6 : 4) / view.scale, 0, Math.PI * 2);
  context.fillStyle = route.color;
  context.fill();
  context.lineWidth = 2 / view.scale;
  context.strokeStyle = "#fff";
  context.stroke();
}

function zoom(multiplier, x = width / 2, y = height / 2) {
  const scale = Math.min(view.base * 12, Math.max(view.base * .55, view.scale * multiplier));
  const ratio = scale / view.scale;
  view.x = x - (x - view.x) * ratio;
  view.y = y - (y - view.y) * ratio;
  view.scale = scale;
  draw();
}

function position(event) {
  const bounds = canvas.getBoundingClientRect();
  return { x: event.clientX - bounds.left, y: event.clientY - bounds.top };
}

canvas.addEventListener("pointerdown", (event) => {
  if (fingers.size >= 2 || event.button !== 0) return;
  canvas.setPointerCapture(event.pointerId);
  fingers.set(event.pointerId, position(event));
});
canvas.addEventListener("pointermove", (event) => {
  const old = fingers.get(event.pointerId);
  if (!old) return;
  const point = position(event);
  fingers.set(event.pointerId, point);
  const other = [...fingers.entries()].find(([id]) => id !== event.pointerId)?.[1];
  if (other) {
    const initial = Math.hypot(old.x - other.x, old.y - other.y);
    const distance = Math.hypot(point.x - other.x, point.y - other.y);
    if (initial > 0) zoom(distance / initial, (old.x + other.x) / 2, (old.y + other.y) / 2);
  }
  const factor = other ? .5 : 1;
  view.x += (point.x - old.x) * factor;
  view.y += (point.y - old.y) * factor;
  draw();
});
for (const type of ["pointerup", "pointercancel", "lostpointercapture"]) {
  canvas.addEventListener(type, (event) => fingers.delete(event.pointerId));
}
canvas.addEventListener("wheel", (event) => {
  event.preventDefault();
  const { x, y } = position(event);
  zoom(event.deltaY < 0 ? 1.15 : 1 / 1.15, x, y);
}, { passive: false });
canvas.addEventListener("keydown", (event) => {
  const movement = { ArrowLeft: [35, 0], ArrowRight: [-35, 0], ArrowUp: [0, 35], ArrowDown: [0, -35] }[event.key];
  if (movement) {
    event.preventDefault();
    view.x += movement[0];
    view.y += movement[1];
    draw();
  } else if (["+", "=", "-"].includes(event.key)) {
    event.preventDefault();
    zoom(event.key === "-" ? 1 / 1.3 : 1.3);
  }
});
$("zoom-in").addEventListener("click", () => zoom(1.3));
$("zoom-out").addEventListener("click", () => zoom(1 / 1.3));
$("recenter").addEventListener("click", fit);
new ResizeObserver(() => resize()).observe(canvas);
$("music-toggle").addEventListener("click", () => {
  musicEnabled = !musicEnabled;
  updateMusic();
  if (musicEnabled) playMusic();
  else soundtrack.pause();
});
$("start").addEventListener("click", start);
$("restart").addEventListener("click", start);
$("next").addEventListener("click", next);
$("copy").addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText($("code").textContent);
    $("copy-status").textContent = "Código copiado.";
  } catch {
    const range = document.createRange();
    range.selectNodeContents($("code"));
    window.getSelection()?.removeAllRanges();
    window.getSelection()?.addRange(range);
    $("copy-status").textContent = "Código seleccionado para copiar.";
  }
});
