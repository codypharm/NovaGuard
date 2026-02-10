import { useState } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Upload, Mic, Search, AlertTriangle, CheckCircle, XCircle, ExternalLink } from 'lucide-react'
import { cn } from '@/lib/utils'

// Types for our data
interface SafetyFlag {
  severity: "info" | "warning" | "critical"
  category: string
  message: string
  source: string
  citation?: string
}

interface Verdict {
  status: "green" | "yellow" | "red"
  flags: SafetyFlag[]
  recommendation?: string
}

export function SafetyHUD() {
  const [prescriptionText, setPrescriptionText] = useState("")
  const [isProcessing, setIsProcessing] = useState(false)
  const [verdict, setVerdict] = useState<Verdict | null>(null)

  // Mock processing for UI demo
  const handleProcess = () => {
    setIsProcessing(true)
    setTimeout(() => {
      setIsProcessing(false)
      setVerdict({
        status: "yellow",
        flags: [
          {
            severity: "warning",
            category: "drug_interaction",
            message: "Potential interaction with stored Allergy (Penicillin)",
            source: "Nova Guard",
            citation: "https://dailymed.nlm.nih.gov/dailymed/"
          },
          {
            severity: "info",
            category: "dosage",
            message: "Dosage 10mg is within standard range",
            source: "OpenFDA"
          }
        ]
      })
    }, 1500)
  }

  return (
    <div className="min-h-screen bg-zinc-50 p-8 font-sans text-slate-900">
      <header className="mb-8 flex items-center justify-between">
        <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded bg-teal-600"></div>
            <h1 className="text-xl font-bold tracking-tight text-slate-900">Nova Clinical Guard</h1>
        </div>
        <div className="flex gap-4">
            <Button variant="ghost">History</Button>
            <Button variant="ghost">Settings</Button>
            <div className="h-10 w-10 rounded-full bg-slate-200"></div>
        </div>
      </header>

      <main className="grid grid-cols-1 gap-8 lg:grid-cols-2">
        {/* LEFT PANEL: INPUT */}
        <div className="space-y-6">
            <Card className="border-dashed border-2 bg-white/50 hover:bg-white transition-colors">
                <CardContent className="flex flex-col items-center justify-center py-12 text-center text-slate-500">
                    <div className="mb-4 rounded-full bg-slate-100 p-4">
                        <Upload className="h-8 w-8 text-teal-600" />
                    </div>
                    <h3 className="text-lg font-medium text-slate-900">Drop prescription image here</h3>
                    <p className="text-sm">or click to browse</p>
                </CardContent>
            </Card>

            <div className="relative">
                <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
                    <Search className="h-5 w-5 text-slate-400" />
                </div>
                <textarea 
                    className="block w-full rounded-lg border border-slate-200 bg-white p-4 pl-10 text-sm shadow-sm focus:border-teal-500 focus:ring-teal-500"
                    rows={4}
                    placeholder="Or type prescription details (e.g., 'Lisinopril 10mg daily')..."
                    value={prescriptionText}
                    onChange={(e) => setPrescriptionText(e.target.value)}
                />
                <div className="absolute bottom-3 right-3">
                    <Button size="icon" variant="ghost" className="text-slate-400 hover:text-teal-600">
                        <Mic className="h-5 w-5" />
                    </Button>
                </div>
            </div>

            <Button 
                className="w-full bg-teal-600 hover:bg-teal-700 h-12 text-lg"
                onClick={handleProcess}
                disabled={isProcessing}
            >
                {isProcessing ? "Analyzing Protocol..." : "Run Safety Check"}
            </Button>
        </div>

        {/* RIGHT PANEL: ANALYSIS */}
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
      </main>
    </div>
  )
}
