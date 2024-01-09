function initializeMap(mapContainerId, osmId) {
    return new Promise((resolve, reject) => {
        var map = L.map(mapContainerId, {
            dragging: false,
            touchZoom: false,
            scrollWheelZoom: false,
            doubleClickZoom: false,
            boxZoom: false,
            keyboard: false, // Optional: disable keyboard navigation
            zoomControl: false,
        }); // Initial map position

        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            maxZoom: 19,
            attribution: "© OpenStreetMap contributors",
        }).addTo(map);

        // Modified Overpass API URL to fetch both nodes and relations
        var overpassApiUrl =
            "https://overpass-api.de/api/interpreter?data=[out:json];(node(" +
            osmId +
            ");relation(" +
            osmId +
            "););out body;>;out skel qt;";

        // Fetch the data
        fetch(overpassApiUrl)
            .then((response) => response.json())
            .then((data) => {
                var geojsonData = osmtogeojson(data);
                var hasRelation = false;

                var geoJsonLayer = L.geoJSON(geojsonData, {
                    filter: function (feature, layer) {
                        if (feature.geometry.type !== "Point") {
                            hasRelation = true;
                            return true; // Include non-point features
                        }
                        return false; // Exclude point features within relations
                    },
                }).addTo(map);

                if (hasRelation) {
                    map.fitBounds(geoJsonLayer.getBounds()); // Fit map to GeoJSON bounds of the relation
                } else {
                    // If there are no relations, check for standalone nodes
                    data.elements.forEach(function (element) {
                        if (element.type === "node") {
                            // Place a marker for the node
                            L.marker([element.lat, element.lon]).addTo(map);
                            map.setView([element.lat, element.lon], 13); // Adjust the zoom level as needed
                        }
                    });
                }
            })
            .catch((error) => console.error("Error fetching OSM data:", error));
    });
}
