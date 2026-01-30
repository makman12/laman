// =============================================================================
// Network Visualization Module
// =============================================================================

(function() {
    'use strict';

    // -------------------------------------------------------------------------
    // State
    // -------------------------------------------------------------------------
    let currentTab = 'names';
    let selectedItems = [];
    let bulkLabel = null; // e.g. "CTH 1-20" when added via interval
    let degree = 1;
    let colorMode = 'type';
    let showLabels = true;
    let simulation = null;
    let currentData = null;

    // -------------------------------------------------------------------------
    // Constants
    // -------------------------------------------------------------------------
    const LARGE_THRESHOLD = 150;
    const VERY_LARGE_THRESHOLD = 400;
    const FETCH_DEBOUNCE_MS = 400;
    const SEARCH_DEBOUNCE_MS = 200;

    const TYPE_COLORS = {
        'person': '#3498db',
        'deity': '#9b59b6',
        'place': '#27ae60',
        'unknown': '#95a5a6'
    };

    const COMMUNITY_COLORS = [
        '#e6194B', '#3cb44b', '#ffe119', '#4363d8', '#f58231',
        '#911eb4', '#42d4f4', '#f032e6', '#bfef45', '#fabed4',
        '#469990', '#dcbeff', '#9A6324', '#fffac8', '#800000',
        '#aaffc3', '#808000', '#ffd8b1', '#000075', '#a9a9a9'
    ];

    // -------------------------------------------------------------------------
    // Tab configuration
    // -------------------------------------------------------------------------
    const TAB_CONFIG = {
        names: {
            searchUrl: '/api/name/search/',
            searchParam: 'q',
            resultKey: 'results',
            labelFn: function(item) { return item.name; },
            idFn: function(item) { return String(item.id); },
            buildParams: function(items, opts) {
                var ids = items.map(function(i) { return i.id; }).join(',');
                return 'mode=names&ids=' + ids + '&degree=' + opts.degree;
            },
            showDegree: true,
            placeholder: 'Search names...',
        },
        fragments: {
            searchUrl: '/api/fragment/search/',
            searchParam: 'q',
            resultKey: 'fragments',
            labelFn: function(item) { return item.text; },
            idFn: function(item) { return String(item.id); },
            buildParams: function(items) {
                var ids = items.map(function(i) { return i.id; }).join(',');
                return 'mode=fragments&ids=' + ids;
            },
            showDegree: false,
            placeholder: 'Search fragments (e.g. KBo 4.2)...',
        },
        volumes: {
            searchUrl: '/api/volume/search/',
            searchParam: 'q',
            resultKey: 'results',
            labelFn: function(item) { return item.label; },
            idFn: function(item) { return item.series_id + '_' + item.volume; },
            buildParams: function(items) {
                var parts = items.map(function(i) {
                    return 'series_id=' + i.series_id + '&volume=' + encodeURIComponent(i.volume);
                }).join('&');
                return 'mode=volumes&' + parts;
            },
            showDegree: false,
            placeholder: 'Search volumes (e.g. KBo 4)...',
        },
        cth: {
            searchUrl: '/api/cth/search/',
            searchParam: 'q',
            resultKey: 'results',
            labelFn: function(item) { return item.label; },
            idFn: function(item) { return item.cth; },
            buildParams: function(items) {
                var ids = items.map(function(i) { return i.cth; }).join(',');
                return 'mode=cth&ids=' + ids;
            },
            showDegree: false,
            placeholder: 'Search CTH numbers (e.g. 381)...',
        },
    };

    // -------------------------------------------------------------------------
    // DOM references
    // -------------------------------------------------------------------------
    var svgEl, containerEl, searchInput, autocompleteEl, chipsEl,
        degreeContainer, statsBar, loadingEl, emptyEl, tooltipEl, networkPage, clearBtn;

    // Cached autocomplete results for click handling
    var lastAutocompleteResults = [];

    // -------------------------------------------------------------------------
    // Initialization
    // -------------------------------------------------------------------------
    function init() {
        svgEl = d3.select('#network-svg');
        containerEl = document.getElementById('network-container');
        searchInput = document.getElementById('network-search');
        autocompleteEl = document.getElementById('network-autocomplete');
        chipsEl = document.getElementById('network-chips');
        degreeContainer = document.getElementById('degree-container');
        statsBar = document.getElementById('network-stats-bar');
        loadingEl = document.getElementById('network-loading');
        emptyEl = document.getElementById('network-empty');
        tooltipEl = d3.select('#network-tooltip');
        networkPage = document.getElementById('network-page');
        clearBtn = document.getElementById('clear-btn');

        // Clear button
        clearBtn.addEventListener('click', function() {
            selectedItems = [];
            bulkLabel = null;
            renderChips();
            clearNetwork();
        });

        // Tab clicks
        document.querySelectorAll('.network-tab').forEach(function(tab) {
            tab.addEventListener('click', function() {
                switchTab(tab.dataset.tab);
            });
        });

        // Search input
        var searchTimer = null;
        searchInput.addEventListener('input', function() {
            var q = searchInput.value.trim();
            if (searchTimer) clearTimeout(searchTimer);
            if (q.length < 1) {
                autocompleteEl.style.display = 'none';
                return;
            }
            searchTimer = setTimeout(function() { fetchAutocomplete(q); }, SEARCH_DEBOUNCE_MS);
        });

        // Close autocomplete on outside click
        document.addEventListener('click', function(e) {
            if (!e.target.closest('.network-search-container')) {
                autocompleteEl.style.display = 'none';
            }
        });

        // Degree buttons
        document.querySelectorAll('.degree-btn').forEach(function(btn) {
            btn.addEventListener('click', function() {
                degree = parseInt(btn.dataset.degree);
                document.querySelectorAll('.degree-btn').forEach(function(b) { b.classList.remove('active'); });
                btn.classList.add('active');
                scheduleNetworkUpdate();
            });
        });

        // Color mode
        document.querySelectorAll('input[name="color-mode"]').forEach(function(radio) {
            radio.addEventListener('change', function(e) {
                colorMode = e.target.value;
                scheduleNetworkUpdate();
            });
        });

        // Labels toggle
        document.getElementById('toggle-labels').addEventListener('change', function(e) {
            showLabels = e.target.checked;
            svgEl.selectAll('.labels text').style('display', showLabels ? 'block' : 'none');
        });

        // Fullscreen
        document.getElementById('fullscreen-btn').addEventListener('click', toggleFullscreen);
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && networkPage.classList.contains('fullscreen')) {
                networkPage.classList.remove('fullscreen');
                setTimeout(onResize, 300);
            }
        });

        // Window resize
        window.addEventListener('resize', onResize);

        // Initialize with names tab
        switchTab('names');
    }

    // -------------------------------------------------------------------------
    // Tab switching
    // -------------------------------------------------------------------------
    function switchTab(tab) {
        currentTab = tab;
        selectedItems = [];
        bulkLabel = null;
        searchInput.value = '';
        autocompleteEl.style.display = 'none';

        document.querySelectorAll('.network-tab').forEach(function(t) { t.classList.remove('active'); });
        document.querySelector('.network-tab[data-tab="' + tab + '"]').classList.add('active');

        searchInput.placeholder = TAB_CONFIG[tab].placeholder;
        degreeContainer.style.display = TAB_CONFIG[tab].showDegree ? 'flex' : 'none';

        renderChips();
        clearNetwork();
    }

    // -------------------------------------------------------------------------
    // Autocomplete
    // -------------------------------------------------------------------------
    function fetchAutocomplete(q) {
        var config = TAB_CONFIG[currentTab];
        var url = config.searchUrl + '?' + config.searchParam + '=' + encodeURIComponent(q);

        fetch(url)
            .then(function(resp) { return resp.json(); })
            .then(function(data) {
                var results = data[config.resultKey] || [];
                var selectedIds = {};
                selectedItems.forEach(function(i) { selectedIds[config.idFn(i)] = true; });
                var filtered = results.filter(function(r) { return !selectedIds[config.idFn(r)]; });

                lastAutocompleteResults = filtered;

                if (filtered.length === 0) {
                    autocompleteEl.innerHTML = '<div class="autocomplete-item text-muted">No results</div>';
                } else {
                    var html = '';
                    // Show "Add all (N)" option when there are multiple results (useful for CTH intervals)
                    if (filtered.length > 1) {
                        html += '<div class="autocomplete-item autocomplete-add-all"><strong>Add all (' + filtered.length + ')</strong></div>';
                    }
                    html += filtered.map(function(r, idx) {
                        return '<div class="autocomplete-item" data-index="' + idx + '">' + escapeHtml(config.labelFn(r)) + '</div>';
                    }).join('');
                    autocompleteEl.innerHTML = html;
                }
                autocompleteEl.style.display = 'block';
            })
            .catch(function(err) {
                console.error('Autocomplete error:', err);
            });
    }

    // Delegate click on autocomplete items
    document.addEventListener('click', function(e) {
        // "Add all" button
        if (e.target.closest('.autocomplete-add-all')) {
            var query = searchInput.value.trim();
            // Set a summary label for bulk additions (e.g. "CTH 1-20" or "KBo 1-100")
            if (lastAutocompleteResults.length > 3) {
                bulkLabel = query;
            }
            lastAutocompleteResults.forEach(function(r) { addItem(r); });
            return;
        }
        var item = e.target.closest('.autocomplete-item[data-index]');
        if (item) {
            var idx = parseInt(item.dataset.index);
            if (lastAutocompleteResults[idx]) {
                addItem(lastAutocompleteResults[idx]);
            }
        }
    });

    function escapeHtml(str) {
        var div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    // -------------------------------------------------------------------------
    // Item management (chips)
    // -------------------------------------------------------------------------
    function addItem(item) {
        var config = TAB_CONFIG[currentTab];
        var id = config.idFn(item);
        var alreadySelected = selectedItems.some(function(i) { return config.idFn(i) === id; });
        if (!alreadySelected) {
            item._label = config.labelFn(item);
            selectedItems.push(item);
            renderChips();
            scheduleNetworkUpdate();
        }
        searchInput.value = '';
        autocompleteEl.style.display = 'none';
        searchInput.focus();
    }

    function removeItem(index) {
        selectedItems.splice(index, 1);
        if (selectedItems.length <= 5) bulkLabel = null;
        renderChips();
        scheduleNetworkUpdate();
    }

    function renderChips() {
        // Toggle clear button
        if (clearBtn) {
            clearBtn.style.display = selectedItems.length > 0 ? 'inline-block' : 'none';
        }

        if (selectedItems.length === 0) {
            chipsEl.innerHTML = '';
            return;
        }

        // If bulk label is set and there are many items, show a summary chip
        if (bulkLabel && selectedItems.length > 5) {
            chipsEl.innerHTML = '<span class="network-chip">' +
                escapeHtml(bulkLabel) + ' (' + selectedItems.length + ' items)' +
                '<button type="button" class="chip-remove chip-clear-all">&times;</button>' +
                '</span>';
            chipsEl.querySelector('.chip-clear-all').addEventListener('click', function() {
                selectedItems = [];
                bulkLabel = null;
                renderChips();
                scheduleNetworkUpdate();
            });
            return;
        }

        chipsEl.innerHTML = selectedItems.map(function(item, idx) {
            return '<span class="network-chip">' +
                escapeHtml(item._label) +
                '<button type="button" class="chip-remove" data-index="' + idx + '">&times;</button>' +
                '</span>';
        }).join('');

        chipsEl.querySelectorAll('.chip-remove[data-index]').forEach(function(btn) {
            btn.addEventListener('click', function() {
                removeItem(parseInt(btn.dataset.index));
            });
        });
    }

    // -------------------------------------------------------------------------
    // Network fetch (debounced, auto-triggered)
    // -------------------------------------------------------------------------
    var fetchTimer = null;

    function scheduleNetworkUpdate() {
        if (fetchTimer) clearTimeout(fetchTimer);
        if (selectedItems.length === 0) {
            clearNetwork();
            return;
        }
        fetchTimer = setTimeout(fetchAndRender, FETCH_DEBOUNCE_MS);
    }

    function fetchAndRender() {
        if (selectedItems.length === 0) return;

        loadingEl.style.display = 'flex';
        emptyEl.style.display = 'none';

        var config = TAB_CONFIG[currentTab];
        var paramStr = config.buildParams(selectedItems, { degree: degree });
        if (colorMode === 'community') {
            paramStr += '&communities=true';
        }

        fetch('/api/network/?' + paramStr)
            .then(function(resp) { return resp.json(); })
            .then(function(data) {
                currentData = data;
                renderNetwork(data);
            })
            .catch(function(err) {
                console.error('Network fetch error:', err);
                emptyEl.style.display = 'flex';
                emptyEl.innerHTML = '<p>Error loading network data.</p>';
            })
            .finally(function() {
                loadingEl.style.display = 'none';
            });
    }

    // -------------------------------------------------------------------------
    // D3 rendering
    // -------------------------------------------------------------------------
    function renderNetwork(data) {
        svgEl.selectAll('*').remove();
        if (simulation) { simulation.stop(); simulation = null; }

        if (!data.nodes.length) {
            emptyEl.style.display = 'flex';
            emptyEl.innerHTML = '<p>No connections found for the selected filters.</p>';
            statsBar.style.display = 'none';
            return;
        }

        emptyEl.style.display = 'none';
        updateStats(data);

        var nodeCount = data.nodes.length;
        var isLarge = nodeCount >= LARGE_THRESHOLD;
        var isVeryLarge = nodeCount >= VERY_LARGE_THRESHOLD;

        var width = containerEl.clientWidth;
        var height = containerEl.clientHeight;
        svgEl.attr('width', width).attr('height', height);

        var nodeById = new Map(data.nodes.map(function(d) { return [d.id, d]; }));
        var links = data.edges.map(function(e) {
            return {
                source: nodeById.get(e.source),
                target: nodeById.get(e.target),
                weight: e.weight
            };
        }).filter(function(l) { return l.source && l.target; });

        var maxConnections = Math.max.apply(null, data.nodes.map(function(n) { return n.connections; }).concat([1]));

        function getNodeSize(d) {
            var size = 8 + (d.connections / maxConnections) * 16;
            if (d.is_ego) size *= 1.5;
            return size;
        }

        // Auto-adjust force parameters
        var linkDist = isVeryLarge ? 40 : isLarge ? 60 : 80;
        var charge = isVeryLarge ? -80 : isLarge ? -150 : -200;

        simulation = d3.forceSimulation(data.nodes)
            .force('link', d3.forceLink(links).id(function(d) { return d.id; }).distance(linkDist))
            .force('charge', d3.forceManyBody().strength(charge))
            .force('center', d3.forceCenter(width / 2, height / 2))
            .force('collision', d3.forceCollide().radius(function(d) { return getNodeSize(d) + 3; }));

        var g = svgEl.append('g');

        svgEl.call(d3.zoom()
            .scaleExtent([0.1, 10])
            .on('zoom', function(event) { g.attr('transform', event.transform); }));

        var maxWeight = Math.max.apply(null, links.map(function(l) { return l.weight; }).concat([1]));
        var strokeScale = d3.scaleLinear().domain([1, maxWeight]).range([0.5, 4]);

        var edgeOpacity = isVeryLarge ? 0.3 : isLarge ? 0.5 : 0.8;

        var link = g.append('g').attr('class', 'links')
            .selectAll('line').data(links).enter().append('line')
            .attr('stroke', 'var(--text-muted)')
            .attr('stroke-opacity', edgeOpacity)
            .attr('stroke-width', function(d) { return strokeScale(d.weight); });

        var node = g.append('g').attr('class', 'nodes')
            .selectAll('circle').data(data.nodes).enter().append('circle')
            .attr('r', getNodeSize)
            .attr('fill', function(d) { return getNodeColor(d); })
            .attr('stroke', '#fff')
            .attr('stroke-width', function(d) { return d.is_ego ? 3 : 1.5; })
            .style('cursor', 'pointer')
            .call(d3.drag()
                .on('start', function(e, d) { if (!e.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
                .on('drag', function(e, d) { d.fx = e.x; d.fy = e.y; })
                .on('end', function(e, d) { if (!e.active) simulation.alphaTarget(0); d.fx = null; d.fy = null; }));

        // Tooltip
        node.on('mouseover', function(event, d) {
            var html = '<strong>' + escapeHtml(d.name) + '</strong>';
            if (d.is_ego) html += ' <span style="color:#e74c3c">(selected)</span>';
            html += '<br>Type: ' + escapeHtml(d.name_type);
            html += '<br>Connections: ' + d.connections;
            html += '<br>Attestations: ' + d.attestations;
            if (d.community !== undefined) html += '<br>Community: ' + (d.community + 1);
            tooltipEl.style('display', 'block').html(html);
        })
        .on('mousemove', function(event) {
            tooltipEl.style('left', (event.pageX + 10) + 'px').style('top', (event.pageY - 10) + 'px');
        })
        .on('mouseout', function() { tooltipEl.style('display', 'none'); })
        .on('click', function(event, d) { window.open('/name/' + d.id + '/', '_blank'); });

        // Labels — in large graphs, only label nodes above a size threshold
        var labelSizeThreshold = 0;
        if (isLarge) {
            // Sort node sizes descending, label the top ~30% or at least ego nodes
            var sizes = data.nodes.map(function(d) { return getNodeSize(d); }).sort(function(a, b) { return b - a; });
            var cutoffIndex = Math.max(1, Math.floor(sizes.length * 0.3));
            labelSizeThreshold = sizes[Math.min(cutoffIndex, sizes.length - 1)];
        }

        var labels = g.append('g').attr('class', 'labels')
            .selectAll('text').data(data.nodes).enter().append('text')
            .text(function(d) { return d.name; })
            .attr('font-size', function(d) { return d.is_ego ? '12px' : '10px'; })
            .attr('font-weight', function(d) { return d.is_ego ? 'bold' : 'normal'; })
            .attr('fill', 'var(--text-color)')
            .attr('dx', function(d) { return getNodeSize(d) + 3; })
            .attr('dy', 3)
            .style('pointer-events', 'none')
            .style('display', function(d) {
                if (!showLabels) return 'none';
                if (!isLarge) return 'block';
                // In large graphs, show label if node is large enough or is ego
                return (d.is_ego || getNodeSize(d) >= labelSizeThreshold) ? 'block' : 'none';
            });

        simulation.on('tick', function() {
            link.attr('x1', function(d) { return d.source.x; }).attr('y1', function(d) { return d.source.y; })
                .attr('x2', function(d) { return d.target.x; }).attr('y2', function(d) { return d.target.y; });
            node.attr('cx', function(d) { return d.x; }).attr('cy', function(d) { return d.y; });
            labels.attr('x', function(d) { return d.x; }).attr('y', function(d) { return d.y; });
        });
    }

    function getNodeColor(d) {
        if (d.is_ego) return '#e74c3c';
        if (colorMode === 'community' && d.community !== undefined) {
            return COMMUNITY_COLORS[d.community % COMMUNITY_COLORS.length];
        }
        var key = (d.name_type || 'unknown').toLowerCase();
        return TYPE_COLORS[key] || TYPE_COLORS['unknown'];
    }

    function clearNetwork() {
        svgEl.selectAll('*').remove();
        currentData = null;
        if (simulation) { simulation.stop(); simulation = null; }
        emptyEl.style.display = 'flex';
        emptyEl.innerHTML = '<p>Select items above to generate a network.</p><p class="text-muted">Names that appear together on the same fragments will be connected.</p>';
        statsBar.style.display = 'none';
    }

    function updateStats(data) {
        document.getElementById('stat-nodes').textContent = data.stats.total_nodes;
        document.getElementById('stat-edges').textContent = data.stats.total_edges;
        var commSpan = document.getElementById('stat-communities');
        var commContainer = document.getElementById('stat-communities-container');
        if (data.stats.num_communities > 0) {
            commContainer.style.display = 'inline';
            commSpan.textContent = data.stats.num_communities;
        } else {
            commContainer.style.display = 'none';
        }
        statsBar.style.display = 'flex';
    }

    // -------------------------------------------------------------------------
    // Fullscreen + resize
    // -------------------------------------------------------------------------
    function toggleFullscreen() {
        networkPage.classList.toggle('fullscreen');
        setTimeout(onResize, 300);
    }

    function onResize() {
        if (!currentData) return;
        var w = containerEl.clientWidth;
        var h = containerEl.clientHeight;
        svgEl.attr('width', w).attr('height', h);
        if (simulation) {
            simulation.force('center', d3.forceCenter(w / 2, h / 2));
            simulation.alpha(0.3).restart();
        }
    }

    // -------------------------------------------------------------------------
    // Boot
    // -------------------------------------------------------------------------
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
