import { Card, CardContent } from "@/components/ui/card"
import { AlertTriangle, CheckCircle, XCircle, ExternalLink, Search } from "lucide-react"
import { cn } from "@/lib/utils"

// Types (should be shared, maybe in types.ts later, but duplicated for now/locally defined)
export interface SafetyFlag {
  severity: "info" | "warning" | "critical"
  category: string
  message: string
  source: string
  citation?: string
}

export interface Verdict {
  status: "green" | "yellow" | "red"
  flags: SafetyFlag[]
  recommendation?: string
  confidence_score?: number
}

interface SafetyAnalysisProps {
  isProcessing: boolean
  verdict: Verdict | null
}

export function SafetyAnalysis({ isProcessing, verdict }: SafetyAnalysisProps) {
  return (
    <div className="space-y-6">
        {isProcessing ? (
            <div className="space-y-4 animate-pulse">
                <div className="h-32 rounded-lg bg-slate-200"></div>
                <div className="h-16 rounded-lg bg-slate-200"></div>
                <div className="h-16 rounded-lg bg-slate-200"></div>
            </div>
        ) : verdict ? (
            <div className="space-y-6">
                {/* VERDICT BADGE */}
                <div className={cn(
                    "flex items-center gap-4 rounded-xl p-6 text-white shadow-lg",
                    verdict.status === "green" ? "bg-emerald-500" :
                    verdict.status === "yellow" ? "bg-amber-500" : "bg-rose-500"
                )}>
                    {verdict.status === "green" ? <CheckCircle className="h-12 w-12" /> :
                     verdict.status === "yellow" ? <AlertTriangle className="h-12 w-12" /> :
                     <XCircle className="h-12 w-12" />}
                    <div>
                        <h2 className="text-2xl font-bold uppercase tracking-wide">
                            {verdict.status === "green" ? "Approved" :
                             verdict.status === "yellow" ? "Caution Required" : "Rejected"}
                        </h2>
                        <p className="opacity-90">
                            {verdict.status === "green" ? "No safety concerns detected." :
                             "Please review the flags below before proceeding."}
                        </p>
                        {verdict.confidence_score !== undefined && (
                            <div className="mt-2 inline-flex items-center rounded-full bg-black/20 px-3 py-1 text-xs font-medium backdrop-blur-sm">
                                {Math.round(verdict.confidence_score * 100)}% Confidence
                            </div>
                        )}
                    </div>
                </div>

                {/* FLAGS LIST */}
                <div className="space-y-3">
                    {verdict.flags.map((flag, i) => (
                        <Card key={i} className="border-l-4 border-l-slate-300 overflow-hidden">
                            <CardContent className="p-4 flex gap-4">
                                 <div className={cn(
                                    "mt-1 rounded-full p-1",
                                    flag.severity === "critical" ? "text-rose-600 bg-rose-50" :
                                    flag.severity === "warning" ? "text-amber-600 bg-amber-50" : "text-blue-600 bg-blue-50"
                                 )}>
                                    <AlertTriangle className="h-5 w-5" />
                                 </div>
                                 <div className="flex-1">
                                    <div className="flex justify-between items-start">
                                        <h4 className="font-semibold text-slate-900">{flag.message}</h4>
                                        <span className="text-xs font-mono text-slate-400 uppercase">{flag.source}</span>
                                    </div>
                                    <p className="text-sm text-slate-600 mt-1">
                                        Category: <span className="font-medium text-slate-700">{flag.category}</span>
                                    </p>
                                    {flag.citation && (
                                        <a href={flag.citation} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 mt-2 text-xs font-medium text-teal-600 hover:underline">
                                            View Source <ExternalLink className="h-3 w-3" />
                                        </a>
                                    )}
                                 </div>
                            </CardContent>
                        </Card>
                    ))}
                </div>
            </div>
        ) : (
            <div className="flex h-full flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50 p-12 text-center text-slate-400">
                <div className="mb-4 rounded-full bg-white p-4 shadow-sm">
                    <Search className="h-8 w-8 opacity-50" />
                </div>
                <h3 className="text-lg font-medium text-slate-600">No Analysis Yet</h3>
                <p>Submit a prescription request to see real-time safety auditing.</p>
            </div>
        )}
    </div>
  )
}
