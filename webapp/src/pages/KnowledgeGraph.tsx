import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useKnowledgeBase } from '../contexts/KnowledgeBaseContext';
import { api } from '../lib/api';
import type { KnowledgeGraphNode, KnowledgeGraphEdge, KnowledgeGraphCluster } from '../lib/api';
import { useTranslation } from 'react-i18next';
import {
  Share2,
  Loader2,
  RefreshCw,
  AlertCircle,
  Search,
  X,
  Maximize2,
  LocateFixed,
  Network,
} from 'lucide-react';
import cytoscape from 'cytoscape';
import fcose from 'cytoscape-fcose';

cytoscape.use(fcose);

const MIN_NODE_SIZE = 18;
const MAX_NODE_SIZE = 48;
const MIN_EDGE_WIDTH = 1;
const MAX_EDGE_WIDTH = 4;
const MAX_RENDERED_NODES = 200;
const MAX_RENDERED_EDGES = 400;

function hashToColor(input: string) {
  let hash = 0;
  for (let i = 0; i < input.length; i += 1) {
    hash = input.charCodeAt(i) + ((hash << 5) - hash);
  }
  const hue = Math.abs(hash) % 360;
  return `hsl(${hue}, 70%, 55%)`;
}

function clusterKeyOf(node: Pick<KnowledgeGraphNode, 'cluster' | 'entity_type'>) {
  return node.cluster || node.entity_type || 'concept';
}

function runFcoseLayout(cy: cytoscape.Core) {
  const layout = cy.layout({
    name: 'fcose',
    animate: true,
    randomize: true,
    nodeSeparation: 80,
    idealEdgeLength: 140,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any -- fcose layout options lack typings
  } as any);
  layout.run();
}

interface LegendEntry {
  key: string;
  name: string;
  count: number;
  summary?: string | null;
}

interface NeighborEntry {
  id: string;
  name: string;
  relation: string;
  weight: number;
}

export default function KnowledgeGraph() {
  const navigate = useNavigate();
  const { isAuthenticated, isLoading: authLoading, accessToken } = useAuth();
  const { selectedKB, isDefaultSelected } = useKnowledgeBase();
  const { t } = useTranslation();

  const [nodes, setNodes] = useState<KnowledgeGraphNode[]>([]);
  const [edges, setEdges] = useState<KnowledgeGraphEdge[]>([]);
  const [clusters, setClusters] = useState<KnowledgeGraphCluster[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [container, setContainer] = useState<HTMLDivElement | null>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);

  const [activeClusterKey, setActiveClusterKey] = useState<string | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [searchMiss, setSearchMiss] = useState(false);

  const jobId = selectedKB && !selectedKB.isDefault ? Number(selectedKB.id) : null;

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      navigate('/login?redirect=/graph');
    }
  }, [authLoading, isAuthenticated, navigate]);

  const loadGraph = useCallback(async () => {
    if (!accessToken || !jobId) return;
    setIsLoading(true);
    setError(null);
    try {
      const [graphResponse, clustersResponse] = await Promise.all([
        api.getKnowledgeGraph(jobId, accessToken),
        api.getKnowledgeGraphClusters(jobId, accessToken).catch(() => ({ clusters: [] })),
      ]);
      setNodes(graphResponse.nodes || []);
      setEdges(graphResponse.edges || []);
      setClusters(
        graphResponse.clusters && graphResponse.clusters.length > 0
          ? graphResponse.clusters
          : clustersResponse.clusters || []
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : t('graph.error_loading'));
    } finally {
      setIsLoading(false);
    }
  }, [accessToken, jobId, t]);

  const runGraph = useCallback(async () => {
    if (!accessToken || !jobId) return;
    setIsRunning(true);
    setError(null);
    try {
      await api.buildKnowledgeGraph(jobId, accessToken);
      await loadGraph();
    } catch (err) {
      setError(err instanceof Error ? err.message : t('graph.error_running'));
    } finally {
      setIsRunning(false);
    }
  }, [accessToken, jobId, loadGraph, t]);

  useEffect(() => {
    if (accessToken && jobId) {
      loadGraph();
    } else {
      setIsLoading(false);
    }
  }, [accessToken, jobId, loadGraph]);

  // Reset transient view state whenever the underlying knowledge base changes.
  useEffect(() => {
    setActiveClusterKey(null);
    setSelectedNodeId(null);
    setSearchTerm('');
    setSearchMiss(false);
  }, [jobId]);

  const renderNodes = useMemo(() => nodes.slice(0, MAX_RENDERED_NODES), [nodes]);
  const renderEdges = useMemo(() => {
    const ids = new Set(renderNodes.map(n => String(n.id)));
    return edges
      .filter(e => ids.has(String(e.source)) && ids.has(String(e.target)))
      .slice(0, MAX_RENDERED_EDGES);
  }, [edges, renderNodes]);

  const degreeMap = useMemo(() => {
    const map = new Map<string, number>();
    renderEdges.forEach(edge => {
      const source = String(edge.source);
      const target = String(edge.target);
      map.set(source, (map.get(source) || 0) + 1);
      map.set(target, (map.get(target) || 0) + 1);
    });
    return map;
  }, [renderEdges]);

  const maxDegree = useMemo(() => {
    let max = 1;
    degreeMap.forEach(value => {
      if (value > max) max = value;
    });
    return max;
  }, [degreeMap]);

  const legendClusters = useMemo<LegendEntry[]>(() => {
    if (clusters.length > 0) {
      return [...clusters]
        .sort((a, b) => b.node_count - a.node_count)
        .map(c => ({ key: c.cluster_id, name: c.name, count: c.node_count, summary: c.summary }));
    }
    const counts = new Map<string, number>();
    nodes.forEach(node => {
      const key = clusterKeyOf(node);
      counts.set(key, (counts.get(key) || 0) + 1);
    });
    return Array.from(counts.entries())
      .map(([key, count]) => ({ key, name: key, count }))
      .sort((a, b) => b.count - a.count);
  }, [clusters, nodes]);

  const nodeById = useMemo(() => {
    const map = new Map<string, KnowledgeGraphNode>();
    renderNodes.forEach(node => map.set(String(node.id), node));
    return map;
  }, [renderNodes]);

  const selectedDetail = useMemo(() => {
    if (!selectedNodeId) return null;
    const node = nodeById.get(selectedNodeId);
    if (!node) return null;

    const neighborBest = new Map<string, NeighborEntry>();
    renderEdges.forEach(edge => {
      const source = String(edge.source);
      const target = String(edge.target);
      let neighborId: string | null = null;
      if (source === selectedNodeId) neighborId = target;
      else if (target === selectedNodeId) neighborId = source;
      if (!neighborId) return;

      const weight = edge.weight ?? 0;
      const existing = neighborBest.get(neighborId);
      if (!existing || weight > existing.weight) {
        neighborBest.set(neighborId, {
          id: neighborId,
          name: nodeById.get(neighborId)?.name || neighborId,
          relation: edge.relation_type,
          weight,
        });
      }
    });

    const top = Array.from(neighborBest.values())
      .sort((a, b) => b.weight - a.weight)
      .slice(0, 5);

    const clusterKey = clusterKeyOf(node);
    const clusterName = legendClusters.find(c => c.key === clusterKey)?.name || clusterKey;

    return {
      node,
      degree: degreeMap.get(selectedNodeId) || 0,
      top,
      clusterName,
    };
  }, [selectedNodeId, nodeById, renderEdges, degreeMap, legendClusters]);

  const selectNode = useCallback((id: string, focus: boolean) => {
    setSelectedNodeId(id);
    if (focus && cyRef.current) {
      const ele = cyRef.current.getElementById(id);
      if (ele && ele.length > 0) {
        cyRef.current.animate(
          { center: { eles: ele }, zoom: Math.max(cyRef.current.zoom(), 1.4) },
          { duration: 300 }
        );
      }
    }
  }, []);

  const clearSelection = useCallback(() => setSelectedNodeId(null), []);

  // Keep latest callbacks available to cytoscape event handlers without
  // forcing the graph-build effect to re-run (and rebuild the instance).
  const selectNodeRef = useRef(selectNode);
  const clearSelectionRef = useRef(clearSelection);
  useEffect(() => {
    selectNodeRef.current = selectNode;
  }, [selectNode]);
  useEffect(() => {
    clearSelectionRef.current = clearSelection;
  }, [clearSelection]);

  // Escape clears the selected node's detail card from anywhere on the page.
  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        clearSelectionRef.current();
      }
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Tear down the cytoscape instance when the container unmounts.
  useEffect(() => {
    if (!container) return;
    return () => {
      if (cyRef.current) {
        cyRef.current.destroy();
        cyRef.current = null;
      }
    };
  }, [container]);

  // Build / update the cytoscape graph whenever the rendered data changes.
  useEffect(() => {
    if (isLoading || !container) return;

    const weightValues = renderEdges.map(e => e.weight ?? 0);
    const minWeight = weightValues.length ? Math.min(...weightValues) : 0;
    const maxWeight = weightValues.length ? Math.max(...weightValues) : 0;
    const weightSpan = maxWeight - minWeight;

    const elements = [
      ...renderNodes.map(node => {
        const id = String(node.id);
        const degree = degreeMap.get(id) || 0;
        const size =
          MIN_NODE_SIZE +
          (MAX_NODE_SIZE - MIN_NODE_SIZE) * (Math.sqrt(degree) / Math.sqrt(maxDegree));
        return {
          data: {
            id,
            label: node.name,
            entityType: node.entity_type,
            cluster: clusterKeyOf(node),
            degree,
            size: Math.round(size),
          },
        };
      }),
      ...renderEdges.map(edge => {
        const weight = edge.weight ?? 0;
        const width =
          weightSpan > 0
            ? MIN_EDGE_WIDTH + ((weight - minWeight) / weightSpan) * (MAX_EDGE_WIDTH - MIN_EDGE_WIDTH)
            : (MIN_EDGE_WIDTH + MAX_EDGE_WIDTH) / 2;
        return {
          data: {
            id: `${edge.source}-${edge.target}-${edge.relation_type}`,
            source: String(edge.source),
            target: String(edge.target),
            relation: edge.relation_type,
            weight,
            width: Number(width.toFixed(2)),
          },
        };
      }),
    ];

    if (!cyRef.current) {
      const cy = cytoscape({
        container,
        elements,
        minZoom: 0.2,
        maxZoom: 3,
        style: [
          {
            selector: 'node',
            style: {
              // eslint-disable-next-line @typescript-eslint/no-explicit-any -- cytoscape style callbacks are untyped
              'background-color': (ele: any) => hashToColor(ele.data('cluster')),
              width: 'data(size)',
              height: 'data(size)',
              label: 'data(label)',
              color: '#e2e8f0',
              'text-outline-width': 2,
              'text-outline-color': '#0f172a',
              'font-size': 10,
              'text-max-width': '90px',
              'text-wrap': 'ellipsis',
              'text-valign': 'bottom',
              'text-margin-y': 6,
              'border-width': 2,
              'border-color': 'rgba(15, 23, 42, 0.55)',
              'transition-property': 'opacity, border-color, border-width',
              'transition-duration': 150,
            },
          },
          {
            selector: 'edge',
            style: {
              width: 'data(width)',
              'line-color': 'rgba(148, 163, 184, 0.22)',
              'curve-style': 'bezier',
              'target-arrow-shape': 'triangle',
              'target-arrow-color': 'rgba(148, 163, 184, 0.28)',
              'arrow-scale': 0.7,
              opacity: 0.9,
              'transition-property': 'opacity, line-color',
              'transition-duration': 150,
            },
          },
          { selector: '.kg-dimmed', style: { opacity: 0.08 } },
          { selector: 'node.kg-dimmed', style: { 'text-opacity': 0.08 } },
          { selector: '.kg-highlighted', style: { opacity: 1 } },
          {
            selector: 'node.kg-selected',
            style: {
              'border-width': 3,
              'border-color': '#f8fafc',
              'overlay-opacity': 0.18,
              'overlay-color': '#38bdf8',
              'overlay-padding': 6,
            },
          },
        ],
      });

      cy.on('tap', 'node', evt => {
        selectNodeRef.current(evt.target.id(), false);
      });
      cy.on('tap', evt => {
        if (evt.target === cy) {
          clearSelectionRef.current();
        }
      });

      cyRef.current = cy;
    } else {
      cyRef.current.json({ elements });
    }

    runFcoseLayout(cyRef.current);
    cyRef.current.resize();
    cyRef.current.fit(undefined, 32);
  }, [renderNodes, renderEdges, degreeMap, maxDegree, isLoading, container]);

  // Dim/highlight elements when a cluster is selected from the legend.
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.batch(() => {
      cy.elements().removeClass('kg-dimmed kg-highlighted');
      if (activeClusterKey) {
        cy.nodes().forEach(node => {
          if (node.data('cluster') === activeClusterKey) {
            node.addClass('kg-highlighted');
          } else {
            node.addClass('kg-dimmed');
          }
        });
        cy.edges().forEach(edge => {
          const sourceCluster = edge.source().data('cluster');
          const targetCluster = edge.target().data('cluster');
          if (sourceCluster === activeClusterKey || targetCluster === activeClusterKey) {
            edge.addClass('kg-highlighted');
          } else {
            edge.addClass('kg-dimmed');
          }
        });
      }
    });
  }, [activeClusterKey, renderNodes, renderEdges]);

  // Outline the currently selected node.
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.nodes().removeClass('kg-selected');
    if (selectedNodeId) {
      cy.getElementById(selectedNodeId).addClass('kg-selected');
    }
  }, [selectedNodeId, renderNodes]);

  const handleZoomToFit = useCallback(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.animate({ fit: { eles: cy.elements(), padding: 32 } }, { duration: 300 });
  }, []);

  const handleRerunLayout = useCallback(() => {
    const cy = cyRef.current;
    if (!cy) return;
    runFcoseLayout(cy);
  }, []);

  const handleLegendClick = useCallback((key: string) => {
    setActiveClusterKey(prev => (prev === key ? null : key));
  }, []);

  const handleSearchSubmit = useCallback(
    (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      const query = searchTerm.trim().toLowerCase();
      if (!query) return;
      const match = renderNodes.find(node => node.name.toLowerCase().includes(query));
      if (match) {
        setSearchMiss(false);
        selectNode(String(match.id), true);
      } else {
        setSearchMiss(true);
      }
    },
    [searchTerm, renderNodes, selectNode]
  );

  if (authLoading || (!isAuthenticated && !authLoading)) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  if (isDefaultSelected || !jobId) {
    return (
      <div className="min-h-screen bg-background p-8">
        <div className="max-w-3xl mx-auto bg-card border border-border rounded-lg p-6">
          <h2 className="text-lg font-semibold text-foreground mb-2">
            {t('graph.select_kb_title')}
          </h2>
          <p className="text-muted-foreground">
            {t('graph.select_kb_desc')}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-6 gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary/10 rounded-lg">
              <Share2 className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-foreground">{t('graph.title')}</h1>
              <p className="text-sm text-muted-foreground">
                {t('graph.subtitle', { name: selectedKB?.name })}
              </p>
            </div>
          </div>
          <button
            onClick={runGraph}
            disabled={isRunning}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50"
          >
            {isRunning ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                {t('graph.running')}
              </>
            ) : (
              <>
                <RefreshCw className="h-4 w-4" />
                {t('graph.run')}
              </>
            )}
          </button>
        </div>

        {error && nodes.length > 0 && (
          <div className="mb-4 bg-destructive/10 border border-destructive/20 rounded-lg p-4 text-destructive flex items-center gap-2">
            <AlertCircle className="h-4 w-4" />
            <span>{error}</span>
          </div>
        )}

        {isLoading ? (
          <div className="bg-card border border-border rounded-lg p-16 flex flex-col items-center justify-center gap-3 text-muted-foreground">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
            <span>{t('graph.loading')}</span>
          </div>
        ) : error && nodes.length === 0 ? (
          <div className="bg-card border border-border rounded-lg p-12 flex flex-col items-center justify-center gap-3 text-center">
            <div className="p-3 bg-destructive/10 rounded-full">
              <AlertCircle className="h-6 w-6 text-destructive" />
            </div>
            <h3 className="font-semibold text-foreground">{t('graph.error_title')}</h3>
            <p className="text-sm text-muted-foreground max-w-md">{error}</p>
            <button
              onClick={loadGraph}
              className="mt-2 flex items-center gap-2 px-4 py-2 bg-secondary text-secondary-foreground rounded-lg hover:bg-secondary/80"
            >
              <RefreshCw className="h-4 w-4" />
              {t('graph.retry')}
            </button>
          </div>
        ) : nodes.length === 0 ? (
          <div className="bg-card border border-border rounded-lg p-12 flex flex-col items-center justify-center gap-3 text-center">
            <div className="p-3 bg-primary/10 rounded-full">
              <Network className="h-6 w-6 text-primary" />
            </div>
            <h3 className="font-semibold text-foreground">{t('graph.empty_title')}</h3>
            <p className="text-sm text-muted-foreground max-w-md">{t('graph.empty_desc')}</p>
            <div className="flex items-center gap-3 mt-2">
              <button
                onClick={runGraph}
                disabled={isRunning}
                className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50"
              >
                {isRunning ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    {t('graph.running')}
                  </>
                ) : (
                  <>
                    <RefreshCw className="h-4 w-4" />
                    {t('graph.run')}
                  </>
                )}
              </button>
              <button
                onClick={() => navigate('/insights')}
                className="flex items-center gap-2 px-4 py-2 border border-border rounded-lg text-foreground hover:bg-secondary/60"
              >
                {t('graph.go_to_insights')}
              </button>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 bg-card border border-border rounded-lg p-4">
              <div className="flex items-center justify-between mb-3 gap-3 flex-wrap">
                <h3 className="font-semibold text-foreground">{t('graph.visual')}</h3>
                <div className="flex items-center gap-2">
                  <form onSubmit={handleSearchSubmit} className="relative">
                    <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
                    <input
                      type="text"
                      value={searchTerm}
                      onChange={(e) => {
                        setSearchTerm(e.target.value);
                        setSearchMiss(false);
                      }}
                      placeholder={t('graph.search_placeholder')}
                      className="pl-8 pr-2 py-1.5 text-sm bg-background border border-border rounded-md w-40 focus:outline-none focus:ring-1 focus:ring-primary"
                    />
                  </form>
                  <button
                    type="button"
                    onClick={handleZoomToFit}
                    title={t('graph.zoom_fit')}
                    aria-label={t('graph.zoom_fit')}
                    className="p-1.5 border border-border rounded-md text-muted-foreground hover:text-foreground hover:bg-secondary/60"
                  >
                    <Maximize2 className="h-4 w-4" />
                  </button>
                  <button
                    type="button"
                    onClick={handleRerunLayout}
                    title={t('graph.rerun_layout')}
                    aria-label={t('graph.rerun_layout')}
                    className="p-1.5 border border-border rounded-md text-muted-foreground hover:text-foreground hover:bg-secondary/60"
                  >
                    <LocateFixed className="h-4 w-4" />
                  </button>
                </div>
              </div>
              {searchMiss && (
                <p className="text-xs text-destructive mb-2">{t('graph.search_not_found')}</p>
              )}
              <div className="relative">
                <div
                  id="graph-view"
                  ref={setContainer}
                  className="bg-background rounded-lg border border-border"
                  style={{ height: 520 }}
                />

                <div className="absolute top-3 left-3 max-w-[220px] bg-card/95 backdrop-blur border border-border rounded-lg shadow-sm p-3 max-h-[70%] overflow-y-auto">
                  <p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wide mb-2">
                    {t('graph.legend_title')}
                  </p>
                  {legendClusters.length === 0 ? (
                    <p className="text-xs text-muted-foreground">{t('graph.legend_empty')}</p>
                  ) : (
                    <ul className="space-y-1">
                      {legendClusters.map(cluster => (
                        <li key={cluster.key}>
                          <button
                            type="button"
                            onClick={() => handleLegendClick(cluster.key)}
                            title={cluster.summary || cluster.name}
                            className={`w-full flex items-center gap-2 text-left px-1.5 py-1 rounded-md text-xs transition-colors ${
                              activeClusterKey === cluster.key
                                ? 'bg-primary/10 text-foreground'
                                : 'text-muted-foreground hover:bg-secondary/60 hover:text-foreground'
                            }`}
                          >
                            <span
                              className="h-2.5 w-2.5 rounded-full flex-shrink-0"
                              style={{ backgroundColor: hashToColor(cluster.key) }}
                            />
                            <span className="flex-1 truncate">{cluster.name}</span>
                            <span className="text-[10px] text-muted-foreground flex-shrink-0">
                              {cluster.count}
                            </span>
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>

                {selectedDetail && (
                  <div className="absolute bottom-3 right-3 w-72 max-w-[85%] max-h-[70%] overflow-y-auto bg-card/95 backdrop-blur border border-border rounded-lg shadow-sm p-4">
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <div className="min-w-0">
                        <p className="font-semibold text-foreground text-sm truncate">
                          {selectedDetail.node.name}
                        </p>
                        <p className="text-xs text-muted-foreground truncate">
                          {selectedDetail.node.entity_type} · {selectedDetail.clusterName}
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={clearSelection}
                        aria-label={t('graph.detail_close')}
                        className="text-muted-foreground hover:text-foreground flex-shrink-0"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                    <p className="text-xs text-muted-foreground mb-3">
                      {t('graph.connections_count', { count: selectedDetail.degree })}
                    </p>
                    <p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wide mb-1">
                      {t('graph.detail_top_connections')}
                    </p>
                    {selectedDetail.top.length === 0 ? (
                      <p className="text-xs text-muted-foreground">{t('graph.detail_no_connections')}</p>
                    ) : (
                      <ul className="space-y-1.5">
                        {selectedDetail.top.map(neighbor => (
                          <li key={neighbor.id} className="text-xs">
                            <div className="flex items-center justify-between gap-2">
                              <span className="text-foreground truncate">{neighbor.name}</span>
                              <span className="text-muted-foreground flex-shrink-0">
                                {neighbor.weight.toFixed(2)}
                              </span>
                            </div>
                            <div className="text-[10px] text-muted-foreground truncate">
                              {neighbor.relation}
                            </div>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                {t('graph.visual_note')}
              </p>
            </div>
            <div className="bg-card border border-border rounded-lg p-4">
              <div className="flex items-baseline justify-between mb-3">
                <h3 className="font-semibold text-foreground">{t('graph.node_list')}</h3>
                {nodes.length > renderNodes.length && (
                  <span className="text-xs text-muted-foreground">
                    {t('graph.node_list_count', { shown: renderNodes.length, total: nodes.length })}
                  </span>
                )}
              </div>
              <div className="max-h-[480px] overflow-y-auto space-y-2">
                {renderNodes.map((node) => {
                  const id = String(node.id);
                  const degree = degreeMap.get(id) || 0;
                  return (
                    <button
                      key={node.id}
                      type="button"
                      onClick={() => selectNode(id, true)}
                      className={`w-full text-left text-sm text-foreground border rounded-md p-2 transition-colors ${
                        selectedNodeId === id
                          ? 'border-primary bg-primary/5'
                          : 'border-border hover:bg-secondary/40'
                      }`}
                    >
                      <div className="font-medium">{node.name}</div>
                      <div className="text-xs text-muted-foreground">
                        {node.entity_type}
                        {node.cluster ? ` · ${node.cluster}` : ''}
                        {` · ${t('graph.connections_count', { count: degree })}`}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
