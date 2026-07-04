import { useState, useEffect } from 'react';
import { Shield, ShieldAlert, Activity, AlertTriangle } from 'lucide-react';

function App() {
  const [stats, setStats] = useState({ total_inspections: 0, threats_mitigated: 0, average_latency_ms: 0 });
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const statsRes = await fetch('/admin/stats');
        const statsData = await statsRes.json();
        setStats(statsData);

        const logsRes = await fetch('/admin/logs');
        const logsData = await logsRes.json();
        setLogs(logsData.logs || []);
        
        setLoading(false);
      } catch (err) {
        console.error("Error fetching admin telemetry", err);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen p-8 bg-zinc-950 text-zinc-50 font-sans">
      {/* Header */}
      <header className="flex items-center gap-3 mb-8 pb-4 border-b border-zinc-800">
        <Shield className="w-8 h-8 text-emerald-500" />
        <h1 className="text-2xl font-bold tracking-tight">ZeroTrust.Agent</h1>
        <span className="ml-auto text-xs font-mono px-3 py-1 bg-zinc-900 border border-zinc-700 rounded-full text-zinc-400">
          CISO CONTROL PLANE
        </span>
      </header>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6 flex items-center gap-4 shadow-lg shadow-black/50">
          <div className="p-3 bg-blue-500/10 rounded-lg">
            <Activity className="w-6 h-6 text-blue-400" />
          </div>
          <div>
            <p className="text-sm text-zinc-400 font-medium">Total Inspections</p>
            <p className="text-3xl font-bold">{stats.total_inspections}</p>
          </div>
        </div>

        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6 flex items-center gap-4 shadow-lg shadow-black/50">
          <div className="p-3 bg-red-500/10 rounded-lg">
            <ShieldAlert className="w-6 h-6 text-red-400" />
          </div>
          <div>
            <p className="text-sm text-zinc-400 font-medium">Threats Mitigated</p>
            <p className="text-3xl font-bold text-red-400">{stats.threats_mitigated}</p>
          </div>
        </div>

        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6 flex items-center gap-4 shadow-lg shadow-black/50">
          <div className="p-3 bg-amber-500/10 rounded-lg">
            <AlertTriangle className="w-6 h-6 text-amber-400" />
          </div>
          <div>
            <p className="text-sm text-zinc-400 font-medium">Avg Latency (ms)</p>
            <p className="text-3xl font-bold text-amber-400">
              {stats.average_latency_ms ? stats.average_latency_ms.toFixed(3) : "0.000"}
            </p>
          </div>
        </div>
      </div>

      {/* Event Stream (The Ledger) */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden shadow-lg shadow-black/50">
        <div className="p-4 border-b border-zinc-800 bg-zinc-900/50">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Activity className="w-5 h-5 text-emerald-500" />
            Live Interception Ledger
          </h2>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="text-xs text-zinc-400 uppercase bg-zinc-900 border-b border-zinc-800">
              <tr>
                <th className="px-6 py-4">Timestamp</th>
                <th className="px-6 py-4">Session ID</th>
                <th className="px-6 py-4">Direction</th>
                <th className="px-6 py-4">Action</th>
                <th className="px-6 py-4">Reason</th>
              </tr>
            </thead>
            <tbody>
              {loading && logs.length === 0 ? (
                <tr>
                  <td colSpan="5" className="px-6 py-8 text-center text-zinc-500">
                    Awaiting telemetry stream...
                  </td>
                </tr>
              ) : (
                logs.map((log) => (
                  <tr key={log.id} className="border-b border-zinc-800/50 hover:bg-zinc-800/20 transition-colors font-mono">
                    <td className="px-6 py-3 whitespace-nowrap text-zinc-400">
                      {new Date(log.timestamp * 1000).toLocaleTimeString()}
                    </td>
                    <td className="px-6 py-3 text-zinc-300">
                      {log.session_id}
                    </td>
                    <td className="px-6 py-3">
                      <span className={`px-2 py-1 rounded text-xs ${log.direction === 'inbound' ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30' : 'bg-fuchsia-500/20 text-fuchsia-300 border border-fuchsia-500/30'}`}>
                        {log.direction.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-6 py-3">
                      <span className={`px-2 py-1 rounded text-xs border ${
                        log.action === 'blocked' ? 'bg-red-500/20 text-red-400 border-red-500/30' : 
                        log.action === 'redacted' ? 'bg-orange-500/20 text-orange-400 border-orange-500/30' : 
                        'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
                      }`}>
                        {log.action.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-6 py-3 text-zinc-400 truncate max-w-md" title={log.reason}>
                      {log.reason}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default App;
