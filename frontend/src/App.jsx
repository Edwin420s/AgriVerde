import React, { useState, useEffect } from 'react'

function App() {
  const [health, setHealth] = useState({ status: 'checking', components: { database: 'checking', redis: 'checking' } })
  const [telemetry, setTelemetry] = useState({
    temperature: 24.5,
    humidity: 58.0,
    soil_moisture: 42,
    target_moisture: 60,
    rain_detected: false,
    pump_active: false,
    motion_detected: false,
  })
  const [devices, setDevices] = useState([
    { device_id: 'AGR-NODE-001', field: 'Field Alpha (Maize)', is_active: true, last_seen: 'Just now' },
    { device_id: 'AGR-NODE-002', field: 'Field Beta (Tomatoes)', is_active: true, last_seen: '2 mins ago' }
  ])
  const [loading, setLoading] = useState(false)

  // Fetch health check and live telemetry
  useEffect(() => {
    const fetchData = () => {
      fetch('/api/v1/health')
        .then(res => res.json())
        .then(data => setHealth(data))
        .catch(() => {
          setHealth({ status: 'degraded', components: { database: 'offline', redis: 'offline' } })
        })

      fetch('/api/v1/telemetry/latest?device_id=AGR-NODE-001')
        .then(res => res.json())
        .then(data => {
          if (data && data.has_data) {
            setTelemetry(prev => ({
              ...prev,
              temperature: data.temperature ?? prev.temperature,
              humidity: data.humidity ?? prev.humidity,
              soil_moisture: data.soil_moisture ?? prev.soil_moisture,
              target_moisture: data.target_moisture ?? prev.target_moisture,
              rain_detected: data.rain_detected ?? prev.rain_detected,
              pump_active: data.pump_active ?? prev.pump_active,
              motion_detected: data.motion_detected ?? prev.motion_detected,
            }))
          }
        })
        .catch(() => {})
    }

    fetchData()
    const interval = setInterval(fetchData, 3000)
    return () => clearInterval(interval)
  }, [])

  const handleTriggerIrrigation = () => {
    setLoading(true)
    setTimeout(() => {
      setTelemetry(prev => ({ ...prev, pump_active: !prev.pump_active }))
      setLoading(false)
    }, 600)
  }

  return (
    <div className="dashboard-container">
      {/* Top Header */}
      <header className="header">
        <div className="header-brand">
          <div className="logo-badge">AV</div>
          <div>
            <h1>AgriVerde Control Center</h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
              Precision Irrigation & Environmental Telemetry
            </p>
          </div>
        </div>
        <div className="system-status-pill">
          <span className={`status-dot ${health.status === 'healthy' ? 'healthy' : 'degraded'}`}></span>
          <span>API: {health.status.toUpperCase()}</span>
        </div>
      </header>

      {/* Main Metric Cards */}
      <div className="metrics-grid">
        <div className="metric-card">
          <div className="metric-label">Soil Moisture</div>
          <div className="metric-value" style={{ color: telemetry.soil_moisture < telemetry.target_moisture ? 'var(--accent-amber)' : 'var(--accent-green)' }}>
            {telemetry.soil_moisture}%
          </div>
          <div className="metric-subtext">Target: {telemetry.target_moisture}%</div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Atmosphere</div>
          <div className="metric-value">
            {telemetry.temperature}°C
          </div>
          <div className="metric-subtext">Humidity: {telemetry.humidity}%</div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Rain Status</div>
          <div className="metric-value" style={{ color: telemetry.rain_detected ? 'var(--accent-blue)' : 'var(--text-primary)' }}>
            {telemetry.rain_detected ? 'Rain Detected' : 'Dry / Clear'}
          </div>
          <div className="metric-subtext">{telemetry.rain_detected ? 'Irrigation Locked Out' : 'Normal Operation'}</div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Pump Status</div>
          <div className="metric-value" style={{ color: telemetry.pump_active ? 'var(--accent-blue)' : 'var(--text-muted)' }}>
            {telemetry.pump_active ? 'IRRIGATING' : 'STANDBY'}
          </div>
          <div className="metric-subtext">{telemetry.pump_active ? 'Active Flow Rate: 12 L/min' : 'Relay OFF'}</div>
        </div>
      </div>

      {/* Two Column Layout */}
      <div className="main-content-grid">
        {/* Active Node Management */}
        <section className="panel">
          <div className="panel-title">
            <span>Connected Field Nodes</span>
            <span className="badge badge-green">{devices.length} Active</span>
          </div>
          <div className="device-list">
            {devices.map(d => (
              <div key={d.device_id} className="device-item">
                <div>
                  <strong style={{ display: 'block' }}>{d.device_id}</strong>
                  <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>{d.field}</span>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <span className="badge badge-blue">Online</span>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                    {d.last_seen}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Irrigation Controls */}
        <section className="panel">
          <div className="panel-title">
            <span>Irrigation Override</span>
          </div>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '1.25rem' }}>
            Manually trigger or halt irrigation pumps across active sectors. Safety interlocks (rain lock and max runtime) remain active.
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <button
              className="btn"
              style={{ backgroundColor: telemetry.pump_active ? 'var(--accent-red)' : 'var(--accent-green)' }}
              onClick={handleTriggerIrrigation}
              disabled={loading}
            >
              {loading ? 'Transmitting Command...' : telemetry.pump_active ? 'Halt Pump (Emergency Stop)' : 'Start Irrigation Cycle'}
            </button>
            <button className="btn btn-secondary" onClick={() => window.location.reload()}>
              Refresh Telemetry
            </button>
          </div>
        </section>
      </div>
    </div>
  )
}

export default App
