document.addEventListener("DOMContentLoaded", function () {
    const container = document.getElementById("graph-container");
    if (!container) return;

    const traceUrl = container.dataset.traceUrl;
    if (!traceUrl) return;

    fetch(traceUrl)
        .then(response => response.json())
        .then(data => {
            const nodes = data.nodes || [];
            const links = data.links || [];

            if (nodes.length === 0) {
                container.innerHTML = "<p><em>Belum ada data pergerakan lot ini.</em></p>";
                return;
            }

            const nodeMap = {};
            nodes.forEach(n => { nodeMap[n.id] = n; });

            const sortedLinks = [...links].sort((a, b) =>
                (a.timestamp || "").localeCompare(b.timestamp || "")
            );

            const orderedNodes = [];
            if (sortedLinks.length > 0) {
                const first = sortedLinks[0];
                const startId = first.source;
                if (nodeMap[startId]) {
                    orderedNodes.push(nodeMap[startId]);
                }

                sortedLinks.forEach(link => {
                    const targetNode = nodeMap[link.target];
                    if (!targetNode) return;
                    if (!orderedNodes.length ||
                        orderedNodes[orderedNodes.length - 1].id !== targetNode.id) {
                        orderedNodes.push(targetNode);
                    }
                });
            } else {
                orderedNodes.push(nodes[0]);
            }

            const wrapper = document.createElement("div");
            wrapper.className = "graph-row";

            orderedNodes.forEach((node, index) => {
                const box = document.createElement("div");
                box.className = "graph-node";

                const nameEl = document.createElement("div");
                nameEl.className = "graph-node-name";
                nameEl.textContent = node.name;

                const typeEl = document.createElement("div");
                typeEl.className = "graph-node-type";
                typeEl.textContent = node.type;

                box.appendChild(nameEl);
                box.appendChild(typeEl);
                wrapper.appendChild(box);

                if (index < orderedNodes.length - 1) {
                    const arrow = document.createElement("div");
                    arrow.className = "graph-arrow";
                    arrow.textContent = "→";
                    wrapper.appendChild(arrow);
                }
            });

            container.innerHTML = "";
            container.appendChild(wrapper);
        })
        .catch(err => {
            console.error("Error memuat trace JSON:", err);
            container.innerHTML = "<p><em>Gagal memuat data graf jalur lot.</em></p>";
        });
});
