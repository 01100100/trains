import { Map, Popup } from "maplibre-gl";
import trainJourney from "./output/train_journeys.json";
import { FeatureCollection, LineString } from "geojson";

const map = new Map({
  container: "map",
  style:
    "https://api.maptiler.com/maps/dataviz-dark/style.json?key=ykqGqGPMAYuYgedgpBOY",
  center: [7.174072, 45.100669],
  zoom: 6,
  minZoom: 5,
  maxPitch: 85,
  attributionControl: false,
});

// Function to convert hex color to HSL
function hexToHSL(hex: string): { h: number, s: number, l: number } {
  let r = 0, g = 0, b = 0;
  if (hex.length == 4) {
    r = parseInt(hex[1] + hex[1], 16);
    g = parseInt(hex[2] + hex[2], 16);
    b = parseInt(hex[3] + hex[3], 16);
  } else if (hex.length == 7) {
    r = parseInt(hex[1] + hex[2], 16);
    g = parseInt(hex[3] + hex[4], 16);
    b = parseInt(hex[5] + hex[6], 16);
  }
  r /= 255;
  g /= 255;
  b /= 255;
  const max = Math.max(r, g, b), min = Math.min(r, g, b);
  let h = 0, s = 0, l = (max + min) / 2;
  if (max != min) {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    switch (max) {
      case r: h = (g - b) / d + (g < b ? 6 : 0); break;
      case g: h = (b - r) / d + 2; break;
      case b: h = (r - g) / d + 4; break;
    }
    h /= 6;
  }
  return { h: h * 360, s: s * 100, l: l * 100 };
}

// Function to generate a color close to a base color using HSL
function generateColor(baseColor: string, identifier: string): string {
  const baseHSL = hexToHSL(baseColor);
  const hash = Array.from(identifier).reduce((acc, char) => acc + char.charCodeAt(0), 0);
  const hueVariation = (hash % 30) - Math.random() * 100;
  const newHue = (baseHSL.h + hueVariation + 360) % 360;
  return `hsl(${newHue}, ${baseHSL.s}%, ${baseHSL.l}%)`;
}

map.on('load', () => {
  const countryColors: { [key: string]: string } = {
    'FR': '#FF0000', // Red for France
    'IT': '#00FF00', // Green for Italy
    'DE': '#0000FF', // Blue for Germany
  };

  // Ensure each feature has a unique id and precompute colors
  (trainJourney as FeatureCollection<LineString>).features.forEach((feature, index) => {
    feature.id = index;
    if (feature.properties) {
      const baseColor = countryColors[feature.properties.dep_country] || '#888';
      feature.properties.color = generateColor(baseColor, feature.properties.train_number);
    }
  });

  map.addSource('trainJourneys', {
    type: 'geojson',
    data: trainJourney as FeatureCollection<LineString>
  });

  map.addLayer({
    id: 'trainJourneysLayer',
    type: 'line',
    source: 'trainJourneys',
    layout: {
      'line-join': 'round',
      'line-cap': 'round'
    },
    paint: {
      'line-color': [
        'case',
        ['boolean', ['feature-state', 'hover'], false],
        '#000000', // Highlight color on hover
        ['get', 'color']
      ],
      'line-width': [
        'case',
        ['boolean', ['feature-state', 'hover'], false],
        7,
        5
      ],
      'line-opacity': [
        'case',
        ['boolean', ['feature-state', 'hover'], false],
        1,
        0.7
      ]
    }
  });

  let popup: Popup | null = null;
  let hoveredFeatureId: number | null = null;

  // Add hover actions and popups
  map.on('mouseenter', 'trainJourneysLayer', (e) => {
    map.getCanvas().style.cursor = 'pointer';

    if (!e.features || e.features.length === 0) return;
    const feature = e.features[0];
    const coordinates = (feature.geometry as LineString).coordinates.slice();
    const properties = feature.properties;

    // Ensure that if the map is zoomed out such that multiple
    // copies of the feature are visible, the popup appears
    // over the copy being pointed to.
    while (Math.abs(e.lngLat.lng - coordinates[0][0]) > 180) {
      coordinates[0][0] += e.lngLat.lng > coordinates[0][0] ? 360 : -360;
    }

    const bikeSpaceRating = '⭐'.repeat(properties.bike_space_rating);

    const popupContent = `
      🚉 <strong>Start Station:</strong> ${properties.start_station}<br>
      🚉 <strong>End Station:</strong> ${properties.end_station}<br>
      🕒 <strong>Start Time:</strong> ${properties.start_time}<br>
      🕒 <strong>End Time:</strong> ${properties.end_time}<br>
      ⏱️ <strong>Delay (mins):</strong> ${properties.delay_mins}<br>
      💶 <strong>Cost (euros):</strong> ${properties.cost_euros}<br>
      🚂 <strong>Train Company:</strong> ${properties.train_company}<br>
      🚆 <strong>Train Number:</strong> ${properties.train_number}<br>
      🚄 <strong>Train Type:</strong> ${properties.train_type}<br>
      📶 <strong>WiFi:</strong> ${properties.wifi}<br>
      🚻 <strong>Toilets:</strong> ${properties.toilets}<br>
      🚲 <strong>Bike Space Rating:</strong> ${bikeSpaceRating}
    `;

    popup = new Popup()
      .setLngLat(e.lngLat)
      .setHTML(popupContent)
      .addTo(map);

    if (hoveredFeatureId !== null) {
      map.setFeatureState(
        { source: 'trainJourneys', id: hoveredFeatureId },
        { hover: false }
      );
    }
    hoveredFeatureId = feature.id as number;
    map.setFeatureState(
      { source: 'trainJourneys', id: hoveredFeatureId },
      { hover: true }
    );
  });

  map.on('mouseleave', 'trainJourneysLayer', () => {
    map.getCanvas().style.cursor = '';
    if (popup) {
      popup.remove();
      popup = null;
    }

    if (hoveredFeatureId !== null) {
      map.setFeatureState(
        { source: 'trainJourneys', id: hoveredFeatureId },
        { hover: false }
      );
    }
    hoveredFeatureId = null;
  });
});