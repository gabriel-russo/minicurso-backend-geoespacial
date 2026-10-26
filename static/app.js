"use strict";

const CORES = {
  Point: "#e11d48",
  LineString: "#2563eb",
  Polygon: "#16a34a",
};

const NOMES = {
  Point: "Ponto",
  LineString: "Linha",
  Polygon: "Polígono",
};

// Tradução dos textos da barra de desenho do Leaflet.draw.
L.drawLocal.draw.toolbar.actions.text = "Cancelar";
L.drawLocal.draw.toolbar.finish.text = "Finalizar";
L.drawLocal.draw.toolbar.undo.text = "Desfazer";
L.drawLocal.draw.toolbar.buttons.marker = "Adicionar ponto";
L.drawLocal.draw.toolbar.buttons.polyline = "Adicionar linha";
L.drawLocal.draw.toolbar.buttons.polygon = "Adicionar polígono";

const mapa = L.map("mapa", { zoomControl: true }).setView(
  [-8.7612, -63.9039],
  12
);

L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution:
    '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
}).addTo(mapa);

const camadasPorId = new Map();
const contador = document.getElementById("contador");
const status = document.getElementById("status");

function estilo(feature) {
  const cor = CORES[feature.geometry?.type] || "#7c3aed";
  return {
    color: cor,
    weight: 3,
    fillColor: cor,
    fillOpacity: 0.2,
  };
}

function criarPonto(feature, latlng) {
  return L.circleMarker(latlng, {
    ...estilo(feature),
    radius: 8,
    weight: 2,
    fillOpacity: 0.85,
  });
}

function dataLegivel(valor) {
  if (!valor) return "—";
  return String(valor).replace("T", " ").replace("Z", "");
}

function popupHtml(feature) {
  const tipo = NOMES[feature.geometry?.type] || "Geometria";
  return `
    <div class="popup">
      <h3>${tipo} #${feature.id}</h3>
      <p>Criado em: ${dataLegivel(feature.properties?.criado_em)}</p>
      <button type="button" onclick="excluirGeometria(${feature.id})">
        Excluir geometria
      </button>
    </div>
  `;
}

function atualizarContador() {
  const total = camadasPorId.size;
  contador.textContent = `${total} ${total === 1 ? "geometria" : "geometrias"}`;
}

function adicionarFeature(feature) {
  if (camadasPorId.has(feature.id)) return;

  const camada = L.geoJSON(feature, {
    style: () => estilo(feature),
    pointToLayer: (f, latlng) => criarPonto(f, latlng),
    onEachFeature: (f, layer) => layer.bindPopup(popupHtml(feature)),
  }).addTo(mapa);

  camadasPorId.set(feature.id, camada);
  atualizarContador();
}

function removerFeature(id) {
  const camada = camadasPorId.get(id);
  if (!camada) return;

  mapa.removeLayer(camada);
  camadasPorId.delete(id);
  atualizarContador();
}

function limparFeatures() {
  camadasPorId.forEach((camada) => mapa.removeLayer(camada));
  camadasPorId.clear();
  atualizarContador();
}

function definirStatus(online, texto) {
  status.textContent = texto;
  status.classList.toggle("online", online);
  status.classList.toggle("offline", !online);
}

async function mensagemDeErro(resposta) {
  try {
    const corpo = await resposta.json();
    return corpo.detail || resposta.statusText;
  } catch {
    return resposta.statusText;
  }
}

// Usada pelo botão dentro do popup.
window.excluirGeometria = async function (id) {
  if (!window.confirm(`Excluir a geometria #${id}?`)) return;

  const resposta = await fetch(`/api/features/${id}`, { method: "DELETE" });

  if (resposta.ok || resposta.status === 404) {
    removerFeature(id);
    return;
  }

  window.alert(`Não foi possível excluir: ${await mensagemDeErro(resposta)}`);
};

const desenho = new L.Control.Draw({
  position: "topleft",
  draw: {
    marker: true,
    polyline: {
      shapeOptions: { color: CORES.LineString, weight: 3 },
    },
    polygon: {
      allowIntersection: false,
      showArea: true,
      shapeOptions: { color: CORES.Polygon, weight: 3 },
    },
    rectangle: false,
    circle: false,
    circlemarker: false,
  },
  edit: false,
});

mapa.addControl(desenho);

mapa.on(L.Draw.Event.CREATED, async (evento) => {
  const geojson = evento.layer.toGeoJSON();

  try {
    const resposta = await fetch("/api/features", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        type: "Feature",
        geometry: geojson.geometry,
        properties: {},
      }),
    });

    if (!resposta.ok) {
      window.alert(`Não foi possível salvar: ${await mensagemDeErro(resposta)}`);
      return;
    }

    const feature = await resposta.json();
    adicionarFeature(feature);
  } catch (erro) {
    window.alert("Falha de rede ao salvar a geometria.");
  }
});

// Carrega o estado atual por REST. O WebSocket também envia um snapshot ao
// conectar; a deduplicação por id evita geometrias repetidas.
async function carregarFeatures() {
  try {
    const resposta = await fetch("/api/features");
    if (!resposta.ok) return;

    const colecao = await resposta.json();
    colecao.features.forEach(adicionarFeature);
  } catch (erro) {
    // Sem conexão: o WebSocket tentará novamente.
  }
}

let socket = null;

function conectarWebSocket() {
  const protocolo = window.location.protocol === "https:" ? "wss" : "ws";
  socket = new WebSocket(`${protocolo}://${window.location.host}/ws`);

  socket.addEventListener("open", () => {
    definirStatus(true, "ao vivo");
  });

  socket.addEventListener("message", (evento) => {
    let mensagem;

    try {
      mensagem = JSON.parse(evento.data);
    } catch {
      return;
    }

    if (mensagem.type === "snapshot") {
      limparFeatures();
      mensagem.features.forEach(adicionarFeature);
    } else if (mensagem.type === "feature_added") {
      adicionarFeature(mensagem.feature);
    } else if (mensagem.type === "feature_removed") {
      removerFeature(mensagem.id);
    }
  });

  socket.addEventListener("close", () => {
    definirStatus(false, "reconectando…");
    window.setTimeout(conectarWebSocket, 2000);
  });

  socket.addEventListener("error", () => {
    socket.close();
  });
}

carregarFeatures();
conectarWebSocket();
atualizarContador();
