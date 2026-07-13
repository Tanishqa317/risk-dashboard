import React from 'react'

type AgentResult = {
  name: string
  risk_score: number
  reasoning: string
}

type OracleSwarmPanelProps = {
  agentResults: AgentResult[]
}

const agentStyles: Record<string, string> = {
  Aggressive: 'bg-red-900/80 border-red-500 text-red-100',
  Conservative: 'bg-blue-900/80 border-blue-500 text-blue-100',
  Adversarial: 'bg-amber-900/80 border-amber-500 text-amber-100',
}

const OracleSwarmPanel = ({ agentResults }: OracleSwarmPanelProps) => {
  const highCount = agentResults.filter((agent) => agent.risk_score > 70).length
  const consensus = highCount >= 2
  const finalVerdict = consensus ? 'high' : 'low'

  return (
    <section className="space-y-6 rounded-3xl border border-slate-700 bg-slate-950/80 p-6 shadow-xl shadow-black/20">
      <div className="grid gap-4 md:grid-cols-3">
        {agentResults.map((agent) => {
          const style = agentStyles[agent.name] ?? 'bg-slate-800 border-slate-600 text-slate-100'
          return (
            <article
              key={agent.name}
              className={`${style} rounded-3xl border p-5 shadow-lg shadow-black/20`}
            >
              <div className="mb-4 flex items-center justify-between gap-3">
                <h2 className="text-lg font-semibold tracking-wide">{agent.name}</h2>
                <span className="rounded-full bg-white/10 px-3 py-1 text-sm font-medium uppercase tracking-[0.18em] text-slate-100">
                  {agent.risk_score}
                </span>
              </div>
              <div className="rounded-3xl bg-white/5 p-4 text-sm leading-6 text-slate-100/90">
                {agent.reasoning}
              </div>
            </article>
          )
        })}
      </div>

      <div className="rounded-3xl border border-slate-700 bg-slate-900/90 p-4 text-center">
        <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Consensus Status</p>
        <p className="mt-2 text-2xl font-semibold text-slate-100">CONSENSUS REACHED</p>
        <p className="mt-1 text-sm text-slate-400">
          Final verdict: <span className="font-semibold text-white">{finalVerdict.toUpperCase()}</span>
        </p>
      </div>
    </section>
  )
}

export default OracleSwarmPanel
