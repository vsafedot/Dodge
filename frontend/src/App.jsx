import { useState, useRef, useCallback, useEffect } from 'react'
import ForceGraph2D from 'react-force-graph-2d'
import ReactMarkdown from 'react-markdown'
import { Bot, Network, X, Send, ChevronRight, Activity, Search } from 'lucide-react'
import './App.css'

// Point to local FastAPI in dev, but live Railway API in production Vercel
const API_URL = import.meta.env.DEV ? 'http://localhost:8000' : 'https://web-production-44d0b.up.railway.app'

// Modern refined color palette
const GROUP_COLORS = {
  Customer: '#f43f5e',
  SalesOrder: '#3b82f6',
  SalesOrderItem: '#6366f1',
  Product: '#f59e0b',
  Delivery: '#10b981',
  DeliveryItem: '#0ea5e9',
  Invoice: '#8b5cf6',
  InvoiceItem: '#c084fc',
  JournalEntry: '#ec4899',
}

const GROUP_SIZES = {
  Customer: 8,
  SalesOrder: 7,
  Product: 6,
  Delivery: 7,
  Invoice: 7,
  JournalEntry: 6,
  SalesOrderItem: 5,
  DeliveryItem: 5,
  InvoiceItem: 5,
}

const SAMPLE_QUERIES = [
  "What is the total billing amount for all sales orders?",
  "Which customer has the most sales orders?",
  "Show me the delivery for sales order 740556",
  "List all cancelled billing documents",
  "What products appear most in sales orders?",
]

function App() {
  const [graphData, setGraphData] = useState({ nodes: [], links: [] })
  
  // Chat state
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  
  // UI Panels state
  const [selectedNode, setSelectedNode] = useState(null)
  
  const messagesEndRef = useRef(null)
  const graphRef = useRef()

  // Fetch full graph graph data on mount
  useEffect(() => {
    fetch(`${API_URL}/api/graph`)
      .then(res => res.json())
      .then(data => {
        const g = data.graph
        setGraphData({
          nodes: g.nodes,
          links: g.edges.map(e => ({ source: e.source, target: e.target, label: e.label }))
        })
      })
      .catch(err => console.error('Failed to load graph:', err))
  }, [])

  // Auto-scroll chat
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const handleSend = async (text) => {
    const query = text || input
    if (!query.trim()) return

    const userMsg = { role: 'user', content: query }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const res = await fetch(`${API_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query })
      })
      const data = await res.json()
      setMessages(prev => [...prev, { role: 'assistant', content: data.response }])
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: '🚨 **Error**: Could not reach the backend. Ensure FastAPI is running.' }])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // Draw nodes gracefully
  const nodeCanvasObject = useCallback((node, ctx, globalScale) => {
    const size = GROUP_SIZES[node.group] || 4
    const color = GROUP_COLORS[node.group] || '#888'
    const isSelected = selectedNode && selectedNode.id === node.id
    
    // Node styling
    ctx.shadowBlur = isSelected ? 16 : 8
    ctx.shadowColor = isSelected ? color : 'rgba(0,0,0,0.1)'
    ctx.beginPath()
    ctx.arc(node.x, node.y, isSelected ? size + 2 : size, 0, 2 * Math.PI)
    ctx.fillStyle = color
    ctx.fill()
    ctx.shadowBlur = 0
    ctx.lineWidth = isSelected ? 2.5 : 1.5;
    ctx.strokeStyle = '#ffffff';
    ctx.stroke();

    // Node labels on zoom
    if (globalScale > 1.2) {
      const label = node.label || ''
      ctx.font = `500 ${Math.max(10 / globalScale, 2)}px Outfit, sans-serif`
      ctx.fillStyle = '#475569'
      ctx.textAlign = 'center'
      ctx.fillText(label, node.x, node.y + size + 8 / globalScale)
    }
  }, [selectedNode])

  // Center Graph
  const handleRecenter = () => {
    if (graphRef.current) {
      graphRef.current.zoomToFit(400, 20);
    }
  }

  return (
    <div id="root">
      
      {/* 1. LAYER ONE: THE GRAPH FULLSCREEN */}
      <div className="graph-container">
        <ForceGraph2D
          ref={graphRef}
          graphData={graphData}
          nodeCanvasObject={nodeCanvasObject}
          nodeRelSize={6}
          linkColor={() => 'rgba(148, 163, 184, 0.35)'}
          linkWidth={1}
          linkDirectionalArrowLength={3.5}
          linkDirectionalArrowRelPos={1}
          onNodeClick={(node) => {
            setSelectedNode(node)
            graphRef.current.centerAt(node.x, node.y, 1000)
            graphRef.current.zoom(2.5, 1000)
          }}
          cooldownTicks={100}
          d3AlphaDecay={0.02}
          d3VelocityDecay={0.2}
          backgroundColor="#f8fafc"
          // Custom tooltip format via standard title attr handling is limited, utilizing standard hovering internally or via CSS.
        />
      </div>

      {/* 2. LAYER TWO: THE HUD */}
      <div className="hud-container">
        
        {/* Top Header Card */}
        <div className="header-card hud-element">
          <div className="brand">
            <div className="brand-icon">
              <Network size={18} />
            </div>
            <h1>NexusGraph O2C</h1>
          </div>
          <div className="stats-group">
            <div className="stat-chip">
              <span className="dot blue"></span>
              {graphData.nodes.length} Nodes
            </div>
            <div className="stat-chip">
              <span className="dot green"></span>
              {graphData.links.length} Edges
            </div>
          </div>
        </div>

        {/* Bottom Area (Legend & Sidebars side-by-side) */}
        <div className="bottom-area">
          
          {/* Left: Legend & Controls */}
          <div className="legend-section hud-element">
            <div className="legend-card">
              {Object.entries(GROUP_COLORS).map(([group, color]) => (
                <div className="legend-item" key={group}>
                  <div className="legend-color" style={{ background: color }}></div>
                  {group}
                </div>
              ))}
            </div>
            
            <div className="graph-controls">
              <button className="control-btn" onClick={handleRecenter} title="Reset View">
                <Activity size={18} />
              </button>
            </div>
          </div>

          {/* Right: Sidebars Group */}
          <div className="sidebars-group">
            
            {/* Active Node Detail Panel */}
            {selectedNode && (
               <div className="sidebar-panel hud-element">
                 <div className="panel-header">
                    <div className="panel-title-wrapper">
                      <div className="panel-header-title">
                        <Search size={18} /> Node Details
                      </div>
                      <div className="panel-subtitle">{selectedNode.group}</div>
                    </div>
                    <button className="panel-close" onClick={() => setSelectedNode(null)}>
                      <X size={20} />
                    </button>
                 </div>
                 
                 <div className="details-content">
                    <div className="detail-row">
                      <div className="detail-label">ID / Reference</div>
                      <div className="detail-value">{selectedNode.id}</div>
                    </div>
                    <div className="detail-row">
                      <div className="detail-label">Primary Label</div>
                      <div className="detail-value">{selectedNode.label}</div>
                    </div>
                    
                    {/* Render arbitrary properties dynamically */}
                    {Object.entries(selectedNode).filter(([key]) => !['id', 'label', 'group', 'x', 'y', 'vx', 'vy', 'index', 'color'].includes(key)).map(([key, value]) => (
                      <div className="detail-row" key={key}>
                        <div className="detail-label">{key}</div>
                        <div className="detail-value">{value?.toString() || 'N/A'}</div>
                      </div>
                    ))}
                 </div>
               </div>
            )}

            {/* AI Assistant Chat Panel */}
            <div className="sidebar-panel hud-element">
              <div className="panel-header">
                <div className="panel-title-wrapper">
                  <div className="panel-header-title">
                    <Bot size={20} /> AI Assistant
                  </div>
                  <div className="panel-subtitle">Powered by AI</div>
                </div>
              </div>

              <div className="chat-messages">
                {messages.length === 0 && (
                  <div className="sample-queries-list">
                    <p>Try asking...</p>
                    {SAMPLE_QUERIES.map((q, i) => (
                      <button key={i} className="btn-suggest" onClick={() => handleSend(q)}>
                        {q} <ChevronRight size={16} />
                      </button>
                    ))}
                  </div>
                )}
                
                {messages.map((msg, i) => (
                  <div key={i} className={`msg-wrapper ${msg.role}`}>
                    <div className="msg-bubble">
                       <div className="markdown-content">
                         <ReactMarkdown>{msg.content}</ReactMarkdown>
                       </div>
                    </div>
                  </div>
                ))}
                
                {loading && (
                  <div className="msg-loading">
                    <div className="loading-dot"></div>
                    <div className="loading-dot"></div>
                    <div className="loading-dot"></div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              <div className="chat-input-area">
                <div className="input-box">
                  <input
                    type="text"
                    placeholder="Ask about orders, invoices..."
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    disabled={loading}
                  />
                  <button className="btn-send" onClick={() => handleSend()} disabled={loading || !input.trim()}>
                    <Send size={16} />
                  </button>
                </div>
              </div>
            </div>
            
          </div>
        </div>

      </div>
    </div>
  )
}

export default App
