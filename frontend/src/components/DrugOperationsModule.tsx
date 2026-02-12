import React, { useState } from 'react'
import { Search, Calculator, Shuffle, AlertTriangle, ShieldCheck, TestTube } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { toast } from "sonner"

// ============================================================================
// Types
// ============================================================================
interface SafetyProfile {
    matrix: {
        pregnancy: "RED" | "YELLOW" | "GREEN" | "GRAY"
        lactation: "RED" | "YELLOW" | "GREEN" | "GRAY"
        geriatric: "RED" | "YELLOW" | "GREEN" | "GRAY"
        pediatric: "RED" | "YELLOW" | "GREEN" | "GRAY"
    }
    bbw: string | null
    counseling: {
        purpose: string
        administration: string
        red_flags: string
    }
}

// ============================================================================
// Sub-Components
// ============================================================================

const SafetyMatrix = ({ data }: { data: SafetyProfile }) => (
    <div className="grid grid-cols-4 gap-2 mb-4">
        {Object.entries(data.matrix).map(([cat, risk]) => (
            <div key={cat} className={`flex flex-col items-center justify-center p-2 rounded border ${
                risk === 'RED' ? 'bg-red-50 border-red-200 text-red-700' :
                risk === 'YELLOW' ? 'bg-yellow-50 border-yellow-200 text-yellow-700' :
                risk === 'GREEN' ? 'bg-emerald-50 border-emerald-200 text-emerald-700' :
                'bg-slate-50 border-slate-200 text-slate-400'
            }`}>
                <span className="text-xs font-semibold uppercase">{cat}</span>
                <ShieldCheck className={`w-6 h-6 mt-1 ${
                     risk === 'RED' ? 'fill-red-100' :
                     risk === 'YELLOW' ? 'fill-yellow-100' :
                     risk === 'GREEN' ? 'fill-emerald-100' :
                     'fill-slate-100'
                }`} />
            </div>
        ))}
    </div>
)

const DoseCalculator = () => {
    const [stats, setStats] = useState({ age: "", weight: "", height: "", scr: "", sex: "male" })
    const [result, setResult] = useState<any>(null)
    const [loading, setLoading] = useState(false)

    const calculate = async () => {
        setLoading(true)
        try {
            const res = await fetch("http://localhost:8000/clinical/calculate-crcl", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    age: parseInt(stats.age),
                    weight_kg: parseFloat(stats.weight),
                    height_cm: parseFloat(stats.height),
                    scr: parseFloat(stats.scr),
                    sex: stats.sex
                })
            })
            const data = await res.json()
            setResult(data)
        } catch (e) {
            toast.error("Calculation failed")
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="grid md:grid-cols-2 gap-6">
            <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                        <Label>Age (years)</Label>
                        <Input type="number" value={stats.age} onChange={e => setStats({...stats, age: e.target.value})} />
                    </div>
                    <div className="space-y-2">
                        <Label>Sex</Label>
                        <select 
                            className="flex h-10 w-full items-center justify-between rounded-md border border-slate-200 bg-white px-3 py-2 text-sm ring-offset-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-950 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                            value={stats.sex}
                            onChange={e => setStats({...stats, sex: e.target.value})}
                        >
                            <option value="male">Male</option>
                            <option value="female">Female</option>
                        </select>
                    </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                     <div className="space-y-2">
                        <Label>Weight (kg)</Label>
                        <Input type="number" value={stats.weight} onChange={e => setStats({...stats, weight: e.target.value})} />
                    </div>
                    <div className="space-y-2">
                        <Label>Height (cm)</Label>
                        <Input type="number" value={stats.height} onChange={e => setStats({...stats, height: e.target.value})} />
                    </div>
                </div>
                <div className="space-y-2">
                    <Label>Serum Creatinine (mg/dL)</Label>
                    <Input type="number" step="0.1" value={stats.scr} onChange={e => setStats({...stats, scr: e.target.value})} />
                </div>
                <Button onClick={calculate} disabled={loading} className="w-full">
                    {loading ? "Calculating..." : "Calculate CrCl"}
                </Button>
            </div>

            {result && (
                <div className="bg-slate-900 text-white p-6 rounded-lg flex flex-col justify-center items-center">
                    <span className="text-slate-400 text-sm uppercase tracking-wider mb-2">Creatinine Clearance</span>
                    <div className="text-5xl font-bold mb-2">{result.crcl}</div>
                    <span className="text-xl text-slate-300">{result.unit}</span>
                    
                    <div className="mt-6 pt-6 border-t border-slate-700 w-full text-center">
                        <span className="text-emerald-400 font-medium">{result.weight_used} Used</span>
                        <p className="text-slate-400 text-sm mt-2">Cockcroft-Gault Equation</p>
                    </div>
                </div>
            )}
        </div>
    )
}

const InteractionSandbox = () => {
    const [navText, setNavText] = useState("")
    const [analysis, setAnalysis] = useState<any>(null)
    const [loading, setLoading] = useState(false)

    const analyze = async () => {
        if (!navText) return
        setLoading(true)
        const drugs = navText.split(',').map(d => d.trim()).filter(Boolean)
        
        try {
            const res = await fetch("http://localhost:8000/clinical/interactions", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ drugs })
            })
            const data = await res.json()
            setAnalysis(data)
        } catch (e) {
            toast.error("Analysis failed")
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="space-y-4">
             <div className="flex gap-2">
                <Input 
                    placeholder="Enter drugs separated by comma (e.g. Warfarin, Aspirin, Lisinopril)..." 
                    value={navText}
                    onChange={e => setNavText(e.target.value)}
                />
                <Button onClick={analyze} disabled={loading}>
                    {loading ? "Analyzing..." : "Check Interactions"}
                </Button>
            </div>
            
            {analysis && (
                <div className="mt-4 space-y-4 animate-in fade-in slide-in-from-top-2">
                   {/* Render dynamic JSON usage from backend */}
                   <div className="p-4 bg-white border rounded-md shadow-sm">
                       <pre className="whitespace-pre-wrap text-sm text-slate-700 font-mono">
                           {JSON.stringify(analysis, null, 2)}
                       </pre>
                   </div>
                </div>
            )}
        </div>
    )
}

const SubstitutionTable = () => {
    const [query, setQuery] = useState("")
    const [results, setResults] = useState<any>(null)
    const [loading, setLoading] = useState(false)

    const search = async () => {
        if (!query) return
        setLoading(true)
        try {
            const res = await fetch(`http://localhost:8000/clinical/substitutions/${query}`)
            const data = await res.json()
            setResults(data)
        } catch (e) {
             toast.error("Search failed")
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="space-y-4">
            <div className="flex gap-2">
                <Input 
                    placeholder="Enter drug name (e.g. Lipitor)..." 
                    value={query}
                    onChange={e => setQuery(e.target.value)}
                />
                <Button onClick={search} disabled={loading}>
                    {loading ? "Searching..." : "Find Equivalents"}
                </Button>
            </div>

             {results && (
                <div className="mt-4 p-4 bg-white border rounded-md shadow-sm">
                     <pre className="whitespace-pre-wrap text-sm text-slate-700 font-mono">
                           {JSON.stringify(results, null, 2)}
                       </pre>
                </div>
            )}
        </div>
    )
}

/**
 * DrugOperationsModule
 * Extracted from DrugOperationsPage and refactored for integration within SafetyHUD.
 */
export default function DrugOperationsModule() {
    const [searchQuery, setSearchQuery] = useState("")
    const [drugData, setDrugData] = useState<SafetyProfile | null>(null)
    const [loading, setLoading] = useState(false)

    const handleSearch = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!searchQuery.trim()) return

        setLoading(true)
        try {
            const res = await fetch(`http://localhost:8000/clinical/safety-profile/${searchQuery}`)
            if (res.ok) {
                const data = await res.json()
                setDrugData(data) 
            }
        } catch (err) {
            console.error("Search failed", err)
            toast.error("Failed to fetch safety profile")
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="flex flex-col">
            {/* Search Area */}
            <div className="mb-6">
                <form onSubmit={handleSearch} className="flex gap-2 mb-6">
                    <div className="relative flex-1">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 w-5 h-5" />
                        <Input 
                            placeholder="Search clinical drug database (e.g. Lisinopril, Warfarin)..." 
                            className="pl-10 h-12 text-lg"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                        />
                    </div>
                    <Button type="submit" size="lg" disabled={loading} className="bg-teal-600 hover:bg-teal-700">
                        {loading ? "Searching..." : "Analyze Drug"}
                    </Button>
                </form>

                {/* Dynamic Content */}
                {drugData && (
                    <div className="animate-in fade-in slide-in-from-top-4 duration-300 mb-8">
                            {/* Black Box Warning - Sticky Note */}
                        {drugData.bbw && (
                            <div className="mb-6 p-4 bg-slate-900 text-white rounded-lg border-l-4 border-red-500 shadow-lg flex items-start gap-4">
                                <AlertTriangle className="w-6 h-6 text-red-500 shrink-0 mt-1" />
                                <div>
                                    <h3 className="font-bold text-lg text-red-400 uppercase tracking-wider mb-1">Black Box Warning</h3>
                                    <p className="text-slate-100 leading-relaxed font-medium">
                                        {drugData.bbw}
                                    </p>
                                </div>
                            </div>
                        )}

                        {/* Safety Matrix */}
                        {drugData.matrix && <SafetyMatrix data={drugData} />}
                        
                        {/* Counseling Cheat Sheet */}
                        {drugData.counseling && (
                            <div className="grid md:grid-cols-3 gap-4 mt-4">
                                <div className="p-4 bg-teal-50 rounded border border-teal-100">
                                    <h4 className="font-semibold text-teal-900 mb-2">Purpose</h4>
                                    <p className="text-sm text-teal-800">{drugData.counseling.purpose}</p>
                                </div>
                                <div className="p-4 bg-teal-50 rounded border border-teal-100">
                                    <h4 className="font-semibold text-teal-900 mb-2">Administration</h4>
                                    <p className="text-sm text-teal-800">{drugData.counseling.administration}</p>
                                </div>
                                <div className="p-4 bg-rose-50 rounded border border-rose-100">
                                    <h4 className="font-semibold text-rose-900 mb-2">Red Flags</h4>
                                    <p className="text-sm text-rose-800">{drugData.counseling.red_flags}</p>
                                </div>
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* Hub Modules */}
            <Tabs defaultValue="sandbox" className="w-full">
                <TabsList className="grid w-full grid-cols-3 bg-slate-200/50 p-1 mb-6">
                    <TabsTrigger value="sandbox" className="data-[state=active]:bg-white data-[state=active]:text-teal-600 data-[state=active]:shadow-sm">
                        <TestTube className="w-4 h-4 mr-2" />
                        Interaction Sandbox
                    </TabsTrigger>
                    <TabsTrigger value="calculator" className="data-[state=active]:bg-white data-[state=active]:text-teal-600 data-[state=active]:shadow-sm">
                        <Calculator className="w-4 h-4 mr-2" />
                        Clinical Calculators
                    </TabsTrigger>
                    <TabsTrigger value="substitution" className="data-[state=active]:bg-white data-[state=active]:text-teal-600 data-[state=active]:shadow-sm">
                        <Shuffle className="w-4 h-4 mr-2" />
                        Substitutions
                    </TabsTrigger>
                </TabsList>

                <div className="grid gap-6">
                    <TabsContent value="sandbox" className="mt-0">
                        <Card>
                            <CardHeader>
                                <CardTitle>Multidrug Interaction Sandbox</CardTitle>
                                <CardDescription>Analyze CYP450 metabolic pathways interactions without a patient profile.</CardDescription>
                            </CardHeader>
                            <CardContent>
                                <InteractionSandbox />
                            </CardContent>
                        </Card>
                    </TabsContent>

                    <TabsContent value="calculator" className="mt-0">
                        <Card>
                            <CardHeader>
                                <CardTitle>Renal & Hepatic Dosing</CardTitle>
                                <CardDescription>Cockcroft-Gault Creatinine Clearance Calculator.</CardDescription>
                            </CardHeader>
                            <CardContent>
                                <DoseCalculator />
                            </CardContent>
                        </Card>
                    </TabsContent>

                    <TabsContent value="substitution" className="mt-0">
                        <Card>
                            <CardHeader>
                                <CardTitle>Therapeutic Equivalents</CardTitle>
                                <CardDescription>Clinical substitution options for shortages or formulary management.</CardDescription>
                            </CardHeader>
                            <CardContent>
                                <SubstitutionTable />
                            </CardContent>
                        </Card>
                    </TabsContent>
                </div>
            </Tabs>
        </div>
    )
}
