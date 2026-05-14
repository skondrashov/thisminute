import { state, COUNTRY_NAME_MAP, _featureDomain, DOMAIN_COLORS } from './state.js';

export function updateEventMapLabels(events, filteredIds) {
  if (!state.map.getSource("events-geo")) return;
  state._lastEventGeo = { type: "FeatureCollection", features: [] };
  state.map.getSource("events-geo").setData(state._lastEventGeo);
}
export function updateCountryPolygons(clouds) {
  if (!state.map.getLayer("country-fill")) return;
  const activeCountries = /* @__PURE__ */ new Map();
  for (const f of clouds.features) {
    const tier = f.properties.tier;
    if (tier !== "small_country" && tier !== "large_country") continue;
    const locName = f.properties.country_name || f.properties.location_name;
    if (!locName) continue;
    const neName = COUNTRY_NAME_MAP[locName] || locName;
    if (!activeCountries.has(neName)) activeCountries.set(neName, { count: 0, categories: {} });
    const entry = activeCountries.get(neName);
    entry.count++;
    const dom = f.properties._domain || _featureDomain(f);
    entry.categories[dom] = (entry.categories[dom] || 0) + 1;
  }
  const countryNames = [...activeCountries.keys()];
  if (countryNames.length === 0) {
    state.map.setFilter("country-fill", ["in", ["get", "NAME"], ["literal", [""]]]);
    state.map.setFilter("country-outline", ["in", ["get", "NAME"], ["literal", [""]]]);
    return;
  }
  const filter = ["in", ["get", "NAME"], ["literal", countryNames]];
  state.map.setFilter("country-fill", filter);
  state.map.setFilter("country-outline", filter);
  const colorCases = ["match", ["get", "NAME"]];
  for (const [name, data] of activeCountries) {
    let maxCat = "general", maxCount = 0;
    for (const [cat, cnt] of Object.entries(data.categories)) {
      if (cnt > maxCount) {
        maxCat = cat;
        maxCount = cnt;
      }
    }
    colorCases.push(name, DOMAIN_COLORS[maxCat] || "#58a6ff");
  }
  colorCases.push("#58a6ff");
  state.map.setPaintProperty("country-fill", "fill-color", colorCases);
  state.map.setPaintProperty("country-outline", "line-color", colorCases);
}
export function addMapLayers(m, srcPrefix) {
  const cloudSrc = srcPrefix + "stories-cloud";
  const countrySrc = srcPrefix + "countries";
  const eventsSrc = srcPrefix + "events-geo";
  m.addSource(cloudSrc, { type: "geojson", data: state.cloudData });
  m.addLayer({
    id: srcPrefix + "cloud-heat",
    type: "heatmap",
    source: cloudSrc,
    filter: [
      "all",
      ["!=", ["get", "tier"], "small_country"],
      ["!=", ["get", "tier"], "large_country"]
    ],
    paint: {
      "heatmap-weight": [
        "interpolate",
        ["linear"],
        ["get", "radius_km"],
        5,
        1,
        50,
        0.6,
        200,
        0.3,
        800,
        0.15
      ],
      "heatmap-intensity": [
        "interpolate",
        ["linear"],
        ["zoom"],
        0,
        0.6,
        3,
        0.8,
        6,
        1.2,
        10,
        1.5
      ],
      "heatmap-radius": [
        "interpolate",
        ["exponential", 2],
        ["zoom"],
        0,
        ["max", 4, ["*", ["get", "radius_km"], 0.015]],
        3,
        ["max", 8, ["*", ["get", "radius_km"], 0.12]],
        6,
        ["max", 15, ["*", ["get", "radius_km"], 1]],
        9,
        ["max", 25, ["*", ["get", "radius_km"], 6]]
      ],
      "heatmap-color": state.lightMode ? [
        "interpolate",
        ["linear"],
        ["heatmap-density"],
        0,
        "rgba(0, 0, 0, 0)",
        0.05,
        "rgba(9, 105, 218, 0.06)",
        0.15,
        "rgba(9, 105, 218, 0.14)",
        0.3,
        "rgba(9, 105, 218, 0.22)",
        0.5,
        "rgba(31, 111, 235, 0.30)",
        0.7,
        "rgba(31, 111, 235, 0.40)",
        1,
        "rgba(9, 105, 218, 0.55)"
      ] : [
        "interpolate",
        ["linear"],
        ["heatmap-density"],
        0,
        "rgba(0, 0, 0, 0)",
        0.05,
        "rgba(30, 80, 180, 0.08)",
        0.15,
        "rgba(50, 120, 220, 0.18)",
        0.3,
        "rgba(80, 160, 255, 0.30)",
        0.5,
        "rgba(100, 200, 240, 0.42)",
        0.7,
        "rgba(200, 220, 255, 0.55)",
        1,
        "rgba(255, 255, 255, 0.70)"
      ],
      "heatmap-opacity": [
        "interpolate",
        ["linear"],
        ["zoom"],
        0,
        0.9,
        10,
        0.7,
        14,
        0.4
      ]
    }
  });
  m.addLayer({
    id: srcPrefix + "cloud-points",
    type: "circle",
    source: cloudSrc,
    filter: ["==", ["get", "is_primary"], true],
    paint: {
      "circle-radius": ["interpolate", ["linear"], ["zoom"], 0, 3, 6, 5, 10, 7],
      "circle-color": ["to-color", ["get", "blended_color"]],
      "circle-opacity": [
        "interpolate",
        ["linear"],
        ["get", "age_hours"],
        0,
        0.95,
        6,
        0.85,
        24,
        0.6,
        72,
        0.35
      ],
      "circle-stroke-width": 1,
      "circle-stroke-color": state.lightMode ? "rgba(0, 0, 0, 0.15)" : "rgba(255, 255, 255, 0.25)"
    }
  });
  m.addSource(srcPrefix + "proximity-highlight", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
  m.addLayer({
    id: srcPrefix + "proximity-highlight",
    type: "circle",
    source: srcPrefix + "proximity-highlight",
    paint: {
      "circle-radius": ["number", ["get", "radius"], 6],
      "circle-radius-transition": { duration: 100, delay: 0 },
      "circle-color": ["to-color", ["coalesce", ["get", "blended_color"], "#484f58"]],
      "circle-opacity": 0.9,
      "circle-opacity-transition": { duration: 150, delay: 0 },
      "circle-stroke-width": 1.5,
      "circle-stroke-color": state.lightMode ? "rgba(0, 0, 0, 0.3)" : "rgba(255, 255, 255, 0.5)"
    }
  });
  m.addSource(srcPrefix + "hover-highlight", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
  m.addLayer({
    id: srcPrefix + "hover-highlight",
    type: "circle",
    source: srcPrefix + "hover-highlight",
    paint: {
      "circle-radius": ["interpolate", ["linear"], ["zoom"], 0, 5, 6, 8, 10, 12],
      "circle-color": state.lightMode ? "#0969da" : "#58a6ff",
      "circle-opacity": 0.6,
      "circle-stroke-width": 2,
      "circle-stroke-color": state.lightMode ? "#0969da" : "#58a6ff",
      "circle-stroke-opacity": 0.9
    }
  });
  m.addSource(srcPrefix + "pulse-source", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
  m.addLayer({
    id: srcPrefix + "pulse-ring",
    type: "circle",
    source: srcPrefix + "pulse-source",
    paint: {
      "circle-radius": ["interpolate", ["linear"], ["zoom"], 0, 6, 6, 12, 10, 18],
      "circle-color": "transparent",
      "circle-stroke-width": 2,
      "circle-stroke-color": state.lightMode ? "#0969da" : "#58a6ff",
      "circle-stroke-opacity": 0.7
    }
  });
  m.addSource(countrySrc, { type: "geojson", data: "/static/data/countries-110m.json" });
  m.addLayer({
    id: srcPrefix + "country-fill",
    type: "fill",
    source: countrySrc,
    filter: ["in", ["get", "NAME"], ["literal", []]],
    paint: {
      "fill-color": "#58a6ff",
      "fill-opacity": state.lightMode ? 0.18 : 0.25
    }
  }, srcPrefix + "cloud-heat");
  m.addLayer({
    id: srcPrefix + "country-outline",
    type: "line",
    source: countrySrc,
    filter: ["in", ["get", "NAME"], ["literal", []]],
    paint: {
      "line-color": "#58a6ff",
      "line-width": 1.2,
      "line-opacity": state.lightMode ? 0.4 : 0.5
    }
  }, srcPrefix + "cloud-heat");
  m.addSource(eventsSrc, { type: "geojson", data: { type: "FeatureCollection", features: [] } });
  m.addLayer({
    id: srcPrefix + "event-labels",
    type: "symbol",
    source: eventsSrc,
    layout: {
      "text-field": ["get", "word"],
      "text-size": ["get", "size"],
      "text-font": ["Open Sans Bold"],
      "text-allow-overlap": false,
      "text-ignore-placement": false,
      "text-anchor": "center",
      "text-padding": 8,
      "text-max-width": 12,
      "text-rotate": ["get", "rotate"],
      "text-letter-spacing": 0.03
    },
    paint: {
      "text-color": state.lightMode ? "rgba(20,30,50,0.95)" : ["get", "color"],
      "text-halo-color": state.lightMode ? "rgba(255,255,255,0.9)" : "rgba(0,0,0,0.9)",
      "text-halo-width": 2,
      "text-opacity": ["interpolate", ["linear"], ["zoom"], 0, 0.55, 3, 0.85, 6, 1]
    }
  });
}
