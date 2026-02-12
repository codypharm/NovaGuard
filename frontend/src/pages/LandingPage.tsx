import { useNavigate } from "react-router-dom"
import { useUser } from "@clerk/clerk-react"
import { ShieldCheck, Activity, Database, Zap, ArrowRight, CheckCircle2, FlaskConical, Stethoscope } from 'lucide-react'
import { Button } from "@/components/ui/button"

export default function LandingPage() {
    const navigate = useNavigate()
    const { isSignedIn } = useUser()

    return (
        <div className="min-h-screen bg-[#FDFDFD] selection:bg-teal-100 selection:text-teal-900 overflow-x-hidden">
            {/* NAVIGATION BAR */}
            <nav className="fixed top-0 w-full z-50 bg-white/80 backdrop-blur-md border-b border-slate-100 h-20 px-6 lg:px-12 flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <div className="h-8 w-8 rounded-lg bg-teal-600 flex items-center justify-center text-white shadow-lg shadow-teal-500/20">
                        <ShieldCheck className="w-5 h-5" />
                    </div>
                    <span className="text-xl font-black tracking-tighter text-slate-900 uppercase italic">Nova Guard</span>
                </div>
                
                <div className="hidden md:flex items-center gap-10 text-sm font-bold text-slate-500 uppercase tracking-widest">
                    <a href="#" className="hover:text-teal-600 transition-colors">Safety Matrix</a>
                    <a href="#" className="hover:text-teal-600 transition-colors">OpenFDA API</a>
                    <a href="#" className="hover:text-teal-600 transition-colors">Protocols</a>
                </div>

                <div className="flex items-center gap-4">
                    {!isSignedIn && (
                        <Button 
                            variant="ghost"
                            onClick={() => navigate("/login")}
                            className="text-slate-600 font-bold hover:text-teal-600"
                        >
                            Sign In
                        </Button>
                    )}
                    <Button 
                        onClick={() => navigate("/workbench")}
                        className="bg-teal-600 hover:bg-teal-700 text-white rounded-full px-8 font-bold shadow-xl shadow-teal-500/10 h-12"
                    >
                        {isSignedIn ? "Go to Workbench" : "Launch Workbench"}
                    </Button>
                </div>
            </nav>

            {/* HERO SECTION */}
            <section className="relative pt-40 pb-32 px-6 lg:px-12">
                <div className="mx-auto max-w-7xl flex flex-col lg:flex-row items-center gap-16">
                    {/* Hero Text */}
                    <div className="w-full lg:w-1/2 relative z-10">
                        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-teal-50 border border-teal-100 text-teal-700 text-xs font-bold uppercase tracking-widest mb-8">
                            <span className="relative flex h-2 w-2">
                                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-teal-400 opacity-75"></span>
                                <span className="relative inline-flex rounded-full h-2 w-2 bg-teal-500"></span>
                            </span>
                            Live 2026 Clinical Intelligence
                        </div>
                        
                        <h1 className="text-5xl sm:text-7xl font-clinical font-black text-slate-900 leading-[1.1] mb-8">
                            Clinical Precision <br />
                            <span className="text-teal-600">Without Compromise.</span>
                        </h1>
                        <p className="text-xl text-slate-600 leading-relaxed mb-10 max-w-xl">
                            The Antigravity Clinical Workbench empowers pharmacists to eliminate dosing errors and automate regimen safety using Amazon Nova reasoning engine.
                        </p>
                        
                        <div className="flex flex-col sm:flex-row gap-4 mb-12">
                            <Button 
                                size="lg" 
                                onClick={() => navigate("/workbench")}
                                className="h-16 px-10 bg-slate-950 text-white hover:bg-teal-600 transition-all text-lg font-bold rounded-2xl group shadow-2xl shadow-slate-950/20"
                            >
                                Start Clinical Intake
                                <ArrowRight className="ml-2 w-5 h-5 group-hover:translate-x-1 transition-transform" />
                            </Button>
                            <Button 
                                variant="ghost" 
                                size="lg"
                                className="h-16 px-10 text-slate-500 font-bold rounded-2xl text-lg hover:bg-slate-50 underline decoration-slate-200 underline-offset-8"
                            >
                                Compare to Legacy Systems
                            </Button>
                        </div>

                        <div className="flex items-center gap-6 pt-8 border-t border-slate-100">
                           <div className="flex -space-x-3">
                                {[1,2,3,4].map(i => (
                                    <div key={i} className="h-10 w-10 rounded-full border-2 border-white bg-slate-200" />
                                ))}
                           </div>
                           <div className="text-sm font-bold text-slate-500 italic">
                               Trusted by 2,400+ Pharmacy Specialists
                           </div>
                        </div>
                    </div>

                    {/* Hero Visual Block */}
                    <div className="w-full lg:w-1/2 relative">
                        <div className="relative w-full aspect-square max-w-xl mx-auto">
                            {/* SVG Geometric Background Elements */}
                            <div className="absolute inset-0 bg-gradient-to-br from-teal-50 to-transparent rounded-[3rem] rotate-3 animate-drift" />
                            
                            {/* Floating "Med-Cards" mimicking reference */}
                            <div className="absolute top-10 right-0 w-48 p-4 bg-white rounded-2xl shadow-2xl border border-slate-50 animate-weightless" style={{ animationDelay: '-1s' }}>
                                <div className="h-8 w-8 rounded-lg bg-teal-50 border border-teal-100 flex items-center justify-center text-teal-600 mb-3">
                                    <FlaskConical className="w-4 h-4" />
                                </div>
                                <div className="h-2 w-12 bg-slate-100 rounded-full mb-2" />
                                <div className="h-2 w-24 bg-slate-50 rounded-full" />
                            </div>

                            <div className="absolute bottom-20 -left-10 w-56 p-6 bg-white rounded-3xl shadow-2xl border border-slate-50 animate-weightless" style={{ animationDelay: '2s' }}>
                                <div className="flex items-center gap-3 mb-4">
                                    <div className="h-10 w-10 rounded-full bg-slate-100" />
                                    <div className="flex flex-col gap-1.5">
                                        <div className="h-2 w-16 bg-slate-200 rounded-full" />
                                        <div className="h-1.5 w-10 bg-slate-100 rounded-full" />
                                    </div>
                                </div>
                                <div className="space-y-2">
                                    <div className="flex items-center gap-2">
                                        <CheckCircle2 className="w-3 h-3 text-teal-500" />
                                        <div className="h-1.5 w-24 bg-slate-50 rounded-full" />
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <CheckCircle2 className="w-3 h-3 text-teal-500" />
                                        <div className="h-1.5 w-20 bg-slate-50 rounded-full" />
                                    </div>
                                </div>
                            </div>

                            {/* Main Centered Clinical Visual */}
                            <div className="absolute inset-20 bg-white rounded-[2.5rem] shadow-2xl flex flex-col items-center justify-center border border-slate-50 p-8 overflow-hidden group">
                                <div className="h-20 w-20 rounded-2xl bg-teal-600 flex items-center justify-center text-white mb-6 group-hover:scale-110 transition-transform duration-500">
                                    <Stethoscope className="w-10 h-10" />
                                </div>
                                <div className="text-center">
                                    <div className="text-lg font-clinical font-bold text-slate-900 mb-1">Drug Ops Module</div>
                                    <div className="text-xs text-slate-400 font-bold uppercase tracking-widest underline decoration-teal-500 decoration-2 underline-offset-4 cursor-pointer">Explore Analysis</div>
                                </div>
                                
                                {/* Background Aura */}
                                <div className="absolute inset-0 bg-teal-500/5 rotate-45 scale-150 blur-3xl opacity-0 group-hover:opacity-100 transition-opacity" />
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* QUICK SOLUTIONS SECTION (White Grid) */}
            <section className="bg-slate-50/50 py-32 px-6 lg:px-12 border-y border-slate-100">
                <div className="mx-auto max-w-7xl">
                    <div className="text-center mb-20">
                        <h2 className="text-4xl sm:text-5xl font-clinical font-black text-slate-900 mb-6">
                            Precision Solution For <br />
                            <span className="text-teal-600">The Modern Pharmacist</span>
                        </h2>
                        <div className="h-1.5 w-24 bg-teal-600 mx-auto rounded-full" />
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-10">
                        <div className="med-card p-10 flex flex-col items-center text-center">
                            <div className="h-16 w-16 rounded-2xl bg-teal-50 text-teal-600 flex items-center justify-center mb-8 border border-teal-100">
                                <Database className="w-8 h-8" />
                            </div>
                            <h3 className="text-2xl font-clinical font-bold text-slate-900 mb-4">Interaction Sandbox</h3>
                            <p className="text-slate-500 leading-relaxed mb-8">
                                Analyze drug-drug patterns with surgical visibility. Simulated against actual OpenFDA safety protocols.
                            </p>
                            <Button variant="ghost" className="text-teal-600 font-bold uppercase tracking-widest text-xs hover:bg-transparent hover:underline underline-offset-4">
                                View Capabilities
                            </Button>
                        </div>

                        <div className="med-card p-10 flex flex-col items-center text-center">
                            <div className="h-16 w-16 rounded-2xl bg-teal-50 text-teal-600 flex items-center justify-center mb-8 border border-teal-100">
                                <Zap className="w-8 h-8" />
                            </div>
                            <h3 className="text-2xl font-clinical font-bold text-slate-900 mb-4">Renal Math Engine</h3>
                            <p className="text-slate-500 leading-relaxed mb-8">
                                Automate complex weight-adjusted dosing calculations (IBW/AdjBW) with zero mathematical variance.
                            </p>
                            <Button variant="ghost" className="text-teal-600 font-bold uppercase tracking-widest text-xs hover:bg-transparent hover:underline underline-offset-4">
                                Examine Methodology
                            </Button>
                        </div>

                        <div className="med-card p-10 flex flex-col items-center text-center">
                            <div className="h-16 w-16 rounded-2xl bg-teal-50 text-teal-600 flex items-center justify-center mb-8 border border-teal-100">
                                <Activity className="w-8 h-8" />
                            </div>
                            <h3 className="text-2xl font-clinical font-bold text-slate-900 mb-4">AI Counseling</h3>
                            <p className="text-slate-500 leading-relaxed mb-8">
                                Dynamic, context-aware patient guidance cards generated specifically for your current clinical session.
                            </p>
                            <Button variant="ghost" className="text-teal-600 font-bold uppercase tracking-widest text-xs hover:bg-transparent hover:underline underline-offset-4">
                                Preview Content
                            </Button>
                        </div>
                    </div>
                </div>
            </section>

            {/* FINAL CTA */}
            <section className="py-32 px-6 lg:px-12 text-center bg-white">
                <div className="mx-auto max-w-3xl">
                    <ShieldCheck className="w-16 h-16 text-teal-100 mx-auto mb-10" />
                    <h2 className="text-4xl sm:text-6xl font-clinical font-black text-slate-900 mb-8">
                        Deploy Your Failsafe. <br />
                        <span className="italic text-teal-600">Eliminate Error.</span>
                    </h2>
                    <p className="text-xl text-slate-500 mb-12">
                        Integrated with OpenFDA. Built on Amazon Nova. Optimized for precision accuracy in clinical decision support.
                    </p>
                    <Button 
                        size="lg" 
                        onClick={() => navigate("/workbench")}
                        className="h-20 px-16 bg-teal-600 text-white hover:bg-teal-700 transition-all text-xl font-bold rounded-full shadow-2xl shadow-teal-500/20"
                    >
                        Contact Clinical Support
                    </Button>
                </div>
            </section>

            {/* FOOTER */}
            <footer className="py-12 px-6 lg:px-12 border-t border-slate-100 flex flex-col sm:flex-row items-center justify-between gap-8 bg-white">
                <div className="flex items-center gap-2 opacity-50">
                    <div className="h-6 w-6 rounded bg-slate-900 flex items-center justify-center text-white text-[8px] font-black">NG</div>
                    <span className="text-xs font-black tracking-tighter text-slate-900 uppercase italic">Nova Guard clinical</span>
                </div>
                <div className="flex gap-10 text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]">
                    <a href="#" className="hover:text-teal-600">Privacy</a>
                    <a href="#" className="hover:text-teal-600">Transparency</a>
                    <a href="#" className="hover:text-teal-600">Status 2026</a>
                    <a href="#" className="hover:text-teal-600">Verify Identity</a>
                </div>
            </footer>
        </div>
    )
}
