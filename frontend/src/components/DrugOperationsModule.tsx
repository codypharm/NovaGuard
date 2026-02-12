import React, { useState } from 'react'
import { Search, Calculator, Shuffle, ShieldCheck, TestTube, Scale, User, Activity, Info, Trash2, Plus } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { toast } from "sonner"
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

// ============================================================================
// Types
// ============================================================================
// Clinical reports are now handled as Markdown strings

// ============================================================================
// Sub-Components
// ============================================================================

const MarkdownReport = ({ content, invert = false }: { content: string, invert?: boolean }) => (
    <div className={`prose prose-sm max-w-none prose-headings:mb-2 ${
        invert 
            ? 'prose-invert prose-headings:text-white prose-p:text-slate-200 prose-strong:text-teal-300 prose-code:text-teal-300 prose-code:bg-white/10 prose-li:text-slate-200' 
            : 'prose-teal prose-headings:text-slate-900 prose-p:text-slate-700 prose-strong:text-teal-900 prose-code:text-teal-600 prose-code:bg-teal-50 prose-li:text-slate-700'
    } prose-code:px-1 prose-code:rounded`}>
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </div>
)

const DoseCalculator = () => {
    const [stats, setStats] = useState({ age: "", weight: "", height: "", scr: "", sex: "male", drugName: "" })
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
                    sex: stats.sex,
                    drug_name: stats.drugName || null
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
        <div className="grid lg:grid-cols-2 gap-8 items-start">
            {/* Form Side */}
            <div className="space-y-4">
                <div className="p-4 bg-slate-50/50 rounded-xl border border-slate-100 space-y-4">
                    <div className="flex items-center gap-2 mb-2">
                        <TestTube className="w-4 h-4 text-teal-600" />
                        <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Clinical Context</span>
                    </div>
                    <div className="space-y-2">
                        <Label className="text-slate-600">Target Medication (Optional for AI Recommendation)</Label>
                        <Input 
                            placeholder="e.g. Enoxaparin, Gentamicin..." 
                            value={stats.drugName} 
                            onChange={e => setStats({...stats, drugName: e.target.value})} 
                            className="bg-white border-slate-200 focus:border-teal-500 focus:ring-teal-500 h-11" 
                        />
                    </div>
                </div>

                <div className="p-4 bg-slate-50/50 rounded-xl border border-slate-100 space-y-4">
                    <div className="flex items-center gap-2 mb-2">
                        <User className="w-4 h-4 text-slate-400" />
                        <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Patient Information</span>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label className="text-slate-600">Age</Label>
                            <Input type="number" placeholder="Years" value={stats.age} onChange={e => setStats({...stats, age: e.target.value})} className="bg-white border-slate-200 focus:border-teal-500 focus:ring-teal-500" />
                        </div>
                        <div className="space-y-2">
                            <Label className="text-slate-600">Biological Sex</Label>
                            <select 
                                className="flex h-10 w-full items-center justify-between rounded-md border border-slate-200 bg-white px-3 py-2 text-sm ring-offset-white focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                                value={stats.sex}
                                onChange={e => setStats({...stats, sex: e.target.value})}
                            >
                                <option value="male">Male</option>
                                <option value="female">Female</option>
                            </select>
                        </div>
                    </div>
                </div>

                <div className="p-4 bg-slate-50/50 rounded-xl border border-slate-100 space-y-4">
                    <div className="flex items-center gap-2 mb-2">
                        <Scale className="w-4 h-4 text-slate-400" />
                        <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Anthropometrics</span>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                         <div className="space-y-2">
                            <Label className="text-slate-600">Weight (kg)</Label>
                            <Input type="number" placeholder="70" value={stats.weight} onChange={e => setStats({...stats, weight: e.target.value})} className="bg-white border-slate-200 focus:border-teal-500 focus:ring-teal-500" />
                        </div>
                        <div className="space-y-2">
                            <Label className="text-slate-600">Height (cm)</Label>
                            <Input type="number" placeholder="175" value={stats.height} onChange={e => setStats({...stats, height: e.target.value})} className="bg-white border-slate-200 focus:border-teal-500 focus:ring-teal-500" />
                        </div>
                    </div>
                </div>

                <div className="p-4 bg-slate-50/50 rounded-xl border border-slate-100 space-y-4">
                    <div className="flex items-center justify-between mb-1">
                        <div className="flex items-center gap-2">
                            <Activity className="w-4 h-4 text-teal-600" />
                            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Renal Function</span>
                        </div>
                        <Info className="w-3 h-3 text-slate-400 cursor-help" />
                    </div>
                    <div className="space-y-2">
                        <Label className="text-slate-600">Serum Creatinine (mg/dL)</Label>
                        <Input type="number" step="0.1" placeholder="1.0" value={stats.scr} onChange={e => setStats({...stats, scr: e.target.value})} className="bg-white border-slate-200 focus:border-teal-500 focus:ring-teal-500" />
                    </div>
                </div>

                <div className="flex gap-2 mt-2">
                    <Button 
                        onClick={calculate} 
                        disabled={loading} 
                        className={`flex-1 h-12 font-bold rounded-lg shadow-sm transition-all active:scale-95 ${
                            result ? 'bg-slate-200 text-slate-700 hover:bg-slate-300' : 'bg-teal-600 hover:bg-teal-700 text-white'
                        }`}
                    >
                        {loading ? "Processing..." : result ? "Recheck" : "Generate Clinical Assessment"}
                    </Button>
                    
                    {result && (
                        <Button 
                            onClick={() => setResult(null)} 
                            variant="outline" 
                            className="h-12 px-6 border-slate-200 text-slate-500 hover:text-rose-600 hover:border-rose-200 hover:bg-rose-50 font-bold rounded-lg transition-all"
                        >
                            Reset
                        </Button>
                    )}
                </div>
            </div>

            {/* Result Side - Matches form height */}
            <div className="h-[650px] lg:h-[660px] flex flex-col">
                {result ? (
                    <div className="h-full animate-in fade-in slide-in-from-right-4 duration-500 flex flex-col bg-slate-900 rounded-2xl border border-slate-800 shadow-2xl overflow-hidden relative">
                        {/* Summary Header */}
                        <div className="p-8 pb-6 border-b border-white/5 shrink-0">
                            <span className="text-teal-400 text-[10px] font-bold uppercase tracking-[0.2em] mb-4 block">Calculated Clearance</span>
                            <div className="flex items-baseline gap-2">
                                <span className="text-7xl font-black text-white tabular-nums tracking-tighter">{result.crcl}</span>
                                <span className="text-teal-500/50 font-bold text-lg uppercase italic">mL/min</span>
                            </div>
                            
                            <div className="grid grid-cols-2 gap-3 mt-6">
                                <div className="bg-white/5 p-3 rounded-xl border border-white/5 text-left">
                                    <div className="text-slate-400 text-[9px] uppercase font-bold tracking-wider mb-1">Dosing Weight</div>
                                    <div className="text-white text-xs font-bold">{result.weight_used}</div>
                                </div>
                                <div className="bg-white/5 p-3 rounded-xl border border-white/5 text-left">
                                    <div className="text-slate-400 text-[9px] uppercase font-bold tracking-wider mb-1">Protocol</div>
                                    <div className="text-white text-xs font-bold">Cockcroft-Gault</div>
                                </div>
                            </div>
                        </div>

                        {/* Scrollable recommendation part */}
                        <div className="flex-1 overflow-y-auto p-8 pt-6 space-y-6">
                            {result.recommendation ? (
                                <div className="w-full text-left bg-teal-500/10 border border-teal-500/20 rounded-xl p-6">
                                    <div className="flex items-center gap-2 mb-4 pb-2 border-b border-teal-500/10">
                                        <ShieldCheck className="w-4 h-4 text-teal-400" />
                                        <span className="text-[10px] font-bold text-teal-400 uppercase tracking-widest">Therapeutic Recommendation</span>
                                    </div>
                                    <MarkdownReport content={result.recommendation} invert />
                                </div>
                            ) : (
                                <div className="flex flex-col items-center justify-center h-full opacity-30 italic">
                                    <p className="text-slate-400 text-sm italic text-center px-8">No medication specified. AI clinical dosing adjustment skipped.</p>
                                </div>
                            )}
                            
                            {/* Removed footer button - moved to form side */}
                        </div>
                    </div>
                ) : (
                    <div className="h-full border-2 border-dashed border-slate-200 rounded-2xl flex flex-col items-center justify-center p-12 text-center bg-slate-50/30">
                        <div className="w-16 h-16 bg-white rounded-full flex items-center justify-center mb-6 shadow-sm border border-slate-100">
                            <Calculator className="w-8 h-8 text-teal-600" />
                        </div>
                        <h4 className="text-slate-900 font-bold mb-2 uppercase tracking-widest text-xs">Awaiting Parameters</h4>
                        <p className="text-slate-500 text-sm max-w-[240px]">Enter patient metrics to generate a validated clinical renal profile.</p>
                    </div>
                )}
            </div>
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
        <div className="space-y-6">
             <div className="bg-slate-50/50 p-4 rounded-xl border border-slate-100 shadow-inner group transition-all focus-within:border-teal-200">
                <div className="flex gap-2">
                    <div className="relative flex-1">
                        <Activity className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 w-4 h-4 group-focus-within:text-teal-600 transition-colors" />
                        <Input 
                            placeholder="e.g. Warfarin, Aspirin, Lisinopril..." 
                            value={navText}
                            onChange={e => setNavText(e.target.value)}
                            className="pl-10 border-transparent bg-transparent focus:border-transparent focus:ring-0 shadow-none h-11 text-slate-700"
                        />
                    </div>
                    <Button onClick={analyze} disabled={loading} className="bg-teal-600 hover:bg-teal-700 text-white px-6 h-11 shrink-0 rounded-lg font-semibold transition-all active:scale-95 shadow-sm">
                        {loading ? "Analyzing..." : "Check Interactions"}
                    </Button>
                </div>
                <div className="mt-2 flex items-center gap-2 overflow-x-auto">
                    <span className="text-[10px] text-slate-400 font-bold uppercase tracking-tight whitespace-nowrap">Examples:</span>
                    {["Warfarin, Aspirin", "Lisinopril, Spironolactone"].map(regimen => (
                        <button 
                            key={regimen}
                            onClick={() => setNavText(regimen)}
                            className="text-[10px] px-2 py-0.5 rounded-md bg-white text-slate-500 hover:bg-teal-50 hover:text-teal-700 transition-colors border border-slate-200"
                        >
                            {regimen}
                        </button>
                    ))}
                </div>
            </div>
            
            {analysis && (
                <Card className="border-teal-100 shadow-sm bg-teal-50/20 overflow-hidden animate-in fade-in slide-in-from-bottom-4 duration-700">
                    <CardHeader className="bg-teal-50/50 py-3 border-b border-teal-100">
                        <div className="flex items-center gap-2">
                            <TestTube className="w-4 h-4 text-teal-600" />
                            <CardTitle className="text-sm font-bold text-teal-800 uppercase tracking-widest">Clinical Interaction Assessment</CardTitle>
                        </div>
                    </CardHeader>
                    <CardContent className="p-6">
                        <MarkdownReport content={analysis} />
                    </CardContent>
                </Card>
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
        <div className="space-y-6">
            <div className="bg-slate-50/50 p-4 rounded-xl border border-slate-100 shadow-inner group transition-all focus-within:border-teal-200">
                <div className="flex gap-2">
                    <div className="relative flex-1">
                        <Shuffle className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 w-4 h-4 group-focus-within:text-teal-600 transition-colors" />
                        <Input 
                            placeholder="e.g. Lipitor (Atorvastatin)..." 
                            value={query}
                            onChange={e => setQuery(e.target.value)}
                            className="pl-10 border-transparent bg-transparent focus:border-transparent focus:ring-0 shadow-none h-11 text-slate-700"
                        />
                    </div>
                    <Button onClick={search} disabled={loading} className="bg-teal-600 hover:bg-teal-700 text-white px-6 h-11 shrink-0 rounded-lg font-semibold transition-all active:scale-95 shadow-sm">
                        {loading ? "Searching..." : "Find Substitutions"}
                    </Button>
                </div>
                <div className="mt-2 flex items-center gap-2 overflow-x-auto">
                    <span className="text-[10px] text-slate-400 font-bold uppercase tracking-tight whitespace-nowrap">Shortages:</span>
                    {["Lipitor", "Ozempic", "Adderall", "Amoxicillin"].map(drug => (
                        <button 
                            key={drug}
                            onClick={() => setQuery(drug)}
                            className="text-[10px] px-2 py-0.5 rounded-md bg-white text-slate-500 hover:bg-teal-50 hover:text-teal-700 transition-colors border border-slate-200"
                        >
                            {drug}
                        </button>
                    ))}
                </div>
            </div>

             {results && (
                <div className="animate-in fade-in slide-in-from-top-4 duration-500 space-y-4">
                    <Card className="border-teal-100 shadow-sm bg-teal-50/20 overflow-hidden">
                        <CardHeader className="bg-teal-50/50 py-3 border-b border-teal-100">
                            <div className="flex items-center gap-2">
                                <Shuffle className="w-4 h-4 text-teal-600" />
                                <CardTitle className="text-sm font-bold text-teal-800 uppercase tracking-widest">Clinical Substitution Options</CardTitle>
                            </div>
                        </CardHeader>
                        <CardContent className="p-6">
                            <MarkdownReport content={results} />
                        </CardContent>
                    </Card>
                </div>
            )}
        </div>
    )
}

interface MedicationEntry {
    name: string;
    dosage: string;
    duration: string;
}

/**
 * DrugOperationsModule
 * Extracted from DrugOperationsPage and refactored for integration within SafetyHUD.
 */
export default function DrugOperationsModule() {
    const [meds, setMeds] = useState<MedicationEntry[]>([{ name: "", dosage: "", duration: "" }])
    const [drugData, setDrugData] = useState<string | null>(null)
    const [loading, setLoading] = useState(false)

    const addMed = () => setMeds([...meds, { name: "", dosage: "", duration: "" }])
    const removeMed = (index: number) => {
        if (meds.length > 1) {
            setMeds(meds.filter((_, i) => i !== index))
        }
    }

    const updateMed = (index: number, field: keyof MedicationEntry, value: string) => {
        const newMeds = [...meds]
        newMeds[index][field] = value
        setMeds(newMeds)
    }

    const handleSearch = async (e: React.FormEvent) => {
        e.preventDefault()
        const validMeds = meds.filter(m => m.name.trim() !== "")
        if (validMeds.length === 0) return

        setLoading(true)
        try {
            const res = await fetch(`http://localhost:8000/clinical/safety-profile`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ medications: validMeds })
            })
            if (res.ok) {
                const data = await res.json()
                setDrugData(data) 
            }
        } catch (err) {
            console.error("Search failed", err)
            toast.error("Failed to generate clinical assessment")
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="flex flex-col space-y-8 pb-12">
            {/* Search Area - More prominent clinical search */}
            <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
                <div className="flex items-center justify-between mb-6">
                    <div>
                        <h3 className="text-sm font-semibold text-slate-900 uppercase tracking-wider">Regimen Safety Assessment</h3>
                        <p className="text-xs text-slate-500 mt-1">Generate comprehensive counseling for a complete medication protocol.</p>
                    </div>
                </div>
                
                <form onSubmit={handleSearch} className="space-y-6">
                    <div className="space-y-4">
                        {meds.map((med, index) => (
                            <div key={index} className="grid grid-cols-12 gap-3 items-end group animate-in slide-in-from-left-2 duration-200">
                                <div className="col-span-12 lg:col-span-5 space-y-2">
                                    {index === 0 && <Label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest ml-1">Drug Name</Label>}
                                    <div className="relative">
                                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 w-4 h-4 group-focus-within:text-teal-600 transition-colors" />
                                        <Input 
                                            placeholder="e.g. Warfarin..." 
                                            value={med.name}
                                            onChange={(e) => updateMed(index, 'name', e.target.value)}
                                            className="pl-10 h-11 border-slate-200 focus:border-teal-500 focus:ring-teal-500 bg-slate-50/50"
                                        />
                                    </div>
                                </div>
                                <div className="col-span-5 lg:col-span-3 space-y-2">
                                    {index === 0 && <Label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest ml-1">Dosage</Label>}
                                    <Input 
                                        placeholder="e.g. 5mg" 
                                        value={med.dosage}
                                        onChange={(e) => updateMed(index, 'dosage', e.target.value)}
                                        className="h-11 border-slate-200 focus:border-teal-500 bg-slate-50/50"
                                    />
                                </div>
                                <div className="col-span-5 lg:col-span-3 space-y-2">
                                    {index === 0 && <Label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest ml-1">Frequency</Label>}
                                    <Input 
                                        placeholder="e.g. Daily" 
                                        value={med.duration}
                                        onChange={(e) => updateMed(index, 'duration', e.target.value)}
                                        className="h-11 border-slate-200 focus:border-teal-500 bg-slate-50/50"
                                    />
                                </div>
                                <div className="col-span-2 lg:col-span-1 pb-1">
                                    <Button 
                                        type="button" 
                                        variant="ghost" 
                                        size="icon"
                                        onClick={() => removeMed(index)}
                                        className="text-slate-300 hover:text-rose-500 hover:bg-rose-50 rounded-lg transition-all"
                                        disabled={meds.length === 1}
                                    >
                                        <Trash2 className="w-4 h-4" />
                                    </Button>
                                </div>
                            </div>
                        ))}
                    </div>

                    <div className="flex items-center gap-3 pt-2">
                        <Button 
                            type="button" 
                            variant="outline" 
                            onClick={addMed}
                            className="h-12 px-6 border-dashed border-slate-200 text-slate-500 hover:text-teal-600 hover:border-teal-200 hover:bg-teal-50 font-bold rounded-lg transition-all"
                        >
                            <Plus className="w-4 h-4 mr-2" />
                            Add Medication
                        </Button>
                        
                        <div className="flex-1" />
                        
                        <div className="flex gap-2">
                            <Button 
                                type="submit" 
                                size="lg" 
                                disabled={loading} 
                                className={`h-12 px-8 font-semibold rounded-lg shadow-sm transition-all active:scale-95 ${
                                    drugData ? 'bg-slate-100 text-slate-600 hover:bg-slate-200' : 'bg-teal-600 hover:bg-teal-700 text-white'
                                }`}
                            >
                                {loading ? (
                                    <div className="flex items-center gap-2">
                                        <span className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                                        Analyzing Regimen...
                                    </div>
                                ) : drugData ? "Update Assessment" : "Generate Clinical Assessment"}
                            </Button>
                            
                            {drugData && (
                                <Button 
                                    type="button"
                                    onClick={() => {
                                        setDrugData(null);
                                        setMeds([{ name: "", dosage: "", duration: "" }]);
                                    }} 
                                    variant="outline" 
                                    className="h-12 px-6 border-slate-200 text-slate-500 hover:text-rose-600 hover:border-rose-200 hover:bg-rose-50 font-bold rounded-lg transition-all shadow-sm"
                                >
                                    Clear
                                </Button>
                            )}
                        </div>
                    </div>
                </form>

                {/* Suggestions / Recent */}
                {!drugData && (
                    <div className="mt-4 flex items-center gap-2 overflow-x-auto pb-1">
                        <span className="text-xs text-slate-400 font-medium whitespace-nowrap">Common:</span>
                        {["Warfarin", "Lisinopril", "Atorvastatin", "Metformin"].map(drug => (
                            <button 
                                key={drug}
                                onClick={() => {
                                    const emptyIndex = meds.findIndex(m => m.name === "");
                                    if (emptyIndex !== -1) {
                                        updateMed(emptyIndex, 'name', drug);
                                    } else {
                                        setMeds([...meds, { name: drug, dosage: "", duration: "" }]);
                                    }
                                }}
                                className="text-xs px-2.5 py-1 rounded-full bg-slate-100 text-slate-600 hover:bg-teal-50 hover:text-teal-700 transition-colors whitespace-nowrap border border-slate-200"
                            >
                                {drug}
                            </button>
                        ))}
                    </div>
                )}
            </div>

            {/* Dynamic Content area */}
            {drugData && (
                <div className="animate-in fade-in slide-in-from-top-4 duration-500 pb-8">
                    <div className="flex items-center gap-3 mb-6">
                        <div className="h-10 w-10 rounded-lg bg-teal-100 flex items-center justify-center text-teal-700">
                            <ShieldCheck className="w-6 h-6" />
                        </div>
                        <div>
                            <h2 className="text-2xl font-bold text-slate-900 capitalize">
                                {meds.filter(m => m.name).map(m => m.name).join(", ")}
                            </h2>
                            <p className="text-sm text-slate-500 uppercase tracking-widest font-medium">Comprehensive Regimen Safety Report</p>
                        </div>
                    </div>
                    
                    <Card className="border-teal-100 shadow-lg bg-white overflow-hidden">
                        <CardHeader className="bg-teal-50/50 py-4 border-b border-teal-100">
                            <div className="flex items-center justify-between">
                                <CardTitle className="text-sm font-bold text-teal-900 uppercase tracking-widest">At-A-Glance Pharmacy Profile</CardTitle>
                                <div className="flex items-center gap-2">
                                    <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                                    <span className="text-[10px] font-bold text-teal-700 uppercase tracking-tighter">AI-Generated Expert Consensus</span>
                                </div>
                            </div>
                        </CardHeader>
                        <CardContent className="p-8">
                            <MarkdownReport content={drugData} />
                        </CardContent>
                    </Card>
                </div>
            )}

            {/* Hub Modules Tab Section - Styled for clinical look */}
            <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
                <Tabs defaultValue="sandbox" className="w-full">
                    <TabsList className="grid w-full grid-cols-3 bg-slate-50 border-b border-slate-100 p-1">
                        <TabsTrigger value="sandbox" className="h-12 data-[state=active]:bg-white data-[state=active]:text-teal-600 data-[state=active]:shadow-none data-[state=active]:border-b-2 data-[state=active]:border-teal-500 rounded-none transition-all">
                            <TestTube className="w-4 h-4 mr-2" />
                            Interaction Sandbox
                        </TabsTrigger>
                        <TabsTrigger value="calculator" className="h-12 data-[state=active]:bg-white data-[state=active]:text-teal-600 data-[state=active]:shadow-none data-[state=active]:border-b-2 data-[state=active]:border-teal-500 rounded-none transition-all">
                            <Calculator className="w-4 h-4 mr-2" />
                            Clinical Calculators
                        </TabsTrigger>
                        <TabsTrigger value="substitution" className="h-12 data-[state=active]:bg-white data-[state=active]:text-teal-600 data-[state=active]:shadow-none data-[state=active]:border-b-2 data-[state=active]:border-teal-500 rounded-none transition-all">
                            <Shuffle className="w-4 h-4 mr-2" />
                            Substitutions
                        </TabsTrigger>
                    </TabsList>

                    <div className="p-6">
                        <TabsContent value="sandbox" className="mt-0 outline-none">
                            <div className="space-y-4">
                                <div className="flex flex-col">
                                    <h3 className="text-lg font-bold text-slate-900 leading-none">Multidrug Interaction Sandbox</h3>
                                    <p className="text-sm text-slate-500 mt-1">Analyze CYP450 metabolic pathways interactions without a patient profile.</p>
                                </div>
                                <InteractionSandbox />
                            </div>
                        </TabsContent>

                        <TabsContent value="calculator" className="mt-0 outline-none">
                             <div className="space-y-4">
                                <div className="flex flex-col">
                                    <h3 className="text-lg font-bold text-slate-900 leading-none">Renal & Hepatic Dosing</h3>
                                    <p className="text-sm text-slate-500 mt-1">Cockcroft-Gault Creatinine Clearance Calculator.</p>
                                </div>
                                <DoseCalculator />
                            </div>
                        </TabsContent>

                        <TabsContent value="substitution" className="mt-0 outline-none">
                            <div className="space-y-4">
                                <div className="flex flex-col">
                                    <h3 className="text-lg font-bold text-slate-900 leading-none">Therapeutic Equivalents</h3>
                                    <p className="text-sm text-slate-500 mt-1">Clinical substitution options for shortages or formulary management.</p>
                                </div>
                                <SubstitutionTable />
                            </div>
                        </TabsContent>
                    </div>
                </Tabs>
            </div>
        </div>
    )
}
