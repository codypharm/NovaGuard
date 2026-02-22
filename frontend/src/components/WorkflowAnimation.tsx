import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FileText, Image as ImageIcon, Zap, ShieldCheck, Database, FlaskConical, Activity, CheckCircle2, AlertTriangle, Pill } from 'lucide-react';

const steps = [
  {
    id: "input",
    title: "Multimodal Intake",
    description: "Accepts photographed labs, unstructured texts, or direct EHR integration.",
    icon: <FileText className="w-6 h-6 text-indigo-400" />,
    color: "from-indigo-500 to-blue-600",
    bg: "bg-indigo-50",
    border: "border-indigo-200"
  },
  {
    id: "classification",
    title: "Nova Extraction & Classification",
    description: "Amazon Nova instantly structures clinical entities and identifies patient intent.",
    icon: <Zap className="w-6 h-6 text-amber-400" />,
    color: "from-amber-400 to-orange-500",
    bg: "bg-amber-50",
    border: "border-amber-200"
  },
  {
    id: "audit",
    title: "Clinical Safety Matrix",
    description: "Cross-checks against FDA guidelines, PGx markers, Polypharmacy logic, and historical data.",
    icon: <ShieldCheck className="w-6 h-6 text-teal-400" />,
    color: "from-teal-400 to-emerald-500",
    bg: "bg-teal-50",
    border: "border-teal-200"
  },
  {
    id: "verdict",
    title: "Pharmacist Verdict",
    description: "Actionable decision support provided securely to the clinician.",
    icon: <CheckCircle2 className="w-6 h-6 text-sky-400" />,
    color: "from-sky-500 to-cyan-600",
    bg: "bg-sky-50",
    border: "border-sky-200"
  }
];

export function WorkflowAnimation() {
  const [activeStep, setActiveStep] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setActiveStep((prev) => (prev + 1) % steps.length);
    }, 4000); // 4 seconds per step
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="w-full max-w-5xl mx-auto py-24 relative">
      {/* Background Decorative Elements */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-teal-50/50 rounded-full blur-[100px] -z-10" />
      
      <div className="text-center mb-16 relative z-10">
        <h2 className="text-3xl md:text-5xl font-clinical font-black text-slate-900 mb-6">
          How Nova Guard Operates
        </h2>
        <p className="text-slate-500 text-lg max-w-2xl mx-auto">
          An autonomous flow spanning unstructured clinical inputs to highly-verified safety verdicts, orchestrated by advanced reasoning.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
        {/* Left Side: Step List */}
        <div className="flex flex-col space-y-4">
          {steps.map((step, index) => {
            const isActive = index === activeStep;
            return (
              <motion.div
                key={step.id}
                onClick={() => setActiveStep(index)}
                className={`relative p-6 rounded-2xl cursor-pointer transition-all duration-500 border-2 overflow-hidden overflow-hidden ${
                  isActive 
                    ? `bg-white border-transparent shadow-2xl shadow-slate-200/50 scale-105` 
                    : `bg-slate-50 border-slate-100 hover:bg-slate-100/50 hover:scale-100 opacity-60`
                }`}
                whileHover={{ scale: isActive ? 1.05 : 1.02 }}
              >
                {/* Active Indicator Glow */}
                {isActive && (
                  <motion.div 
                    layoutId="activeGlow"
                    className={`absolute inset-0 bg-gradient-to-r ${step.color} opacity-5`}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 0.05 }}
                    transition={{ duration: 0.5 }}
                  />
                )}
                
                {/* Active Left Border Indicator */}
                <div className={`absolute left-0 top-0 bottom-0 w-1.5 transition-colors duration-500 bg-gradient-to-b ${isActive ? step.color : 'from-transparent to-transparent'}`} />

                <div className="flex items-start gap-5 relative z-10">
                  <div className={`mt-1 h-12 w-12 rounded-xl flex items-center justify-center border transition-colors duration-500 ${isActive ? `${step.bg} ${step.border}` : 'bg-slate-100 border-slate-200'}`}>
                    {step.icon}
                  </div>
                  <div className="flex-1">
                    <h3 className={`text-xl font-bold mb-2 transition-colors duration-500 ${isActive ? 'text-slate-900' : 'text-slate-500'}`}>
                      {index + 1}. {step.title}
                    </h3>
                    <p className={`text-sm leading-relaxed transition-colors duration-500 ${isActive ? 'text-slate-600' : 'text-slate-400'}`}>
                      {step.description}
                    </p>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>

        {/* Right Side: Animated Visualization Stage */}
        <div className="relative h-[450px] bg-slate-900 rounded-[2.5rem] shadow-2xl overflow-hidden border border-slate-800 flex items-center justify-center p-8">
            {/* Grid background */}
            <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20 mix-blend-overlay"></div>
            <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px]"></div>

            <AnimatePresence mode="wait">
              {activeStep === 0 && (
                 <motion.div
                   key="stage-0"
                   initial={{ opacity: 0, scale: 0.9, y: 20 }}
                   animate={{ opacity: 1, scale: 1, y: 0 }}
                   exit={{ opacity: 0, scale: 0.9, y: -20 }}
                   transition={{ duration: 0.5, type: 'spring' }}
                   className="relative flex flex-col items-center gap-6"
                 >
                    <div className="flex gap-4">
                      <motion.div 
                        initial={{ y: -10 }} animate={{ y: 10 }} transition={{ repeat: Infinity, repeatType: 'reverse', duration: 2, ease: "easeInOut" }}
                        className="w-24 h-32 bg-slate-800 border border-slate-700 rounded-xl p-3 flex flex-col gap-2 shadow-2xl"
                      >
                         <div className="h-2 w-12 bg-indigo-500/50 rounded-full" />
                         <div className="h-2 w-full bg-slate-700 rounded-full" />
                         <div className="h-2 w-3/4 bg-slate-700 rounded-full" />
                         <ImageIcon className="w-8 h-8 text-indigo-400/50 m-auto" />
                      </motion.div>
                      <motion.div 
                         initial={{ y: 10 }} animate={{ y: -10 }} transition={{ repeat: Infinity, repeatType: 'reverse', duration: 2.5, ease: "easeInOut" }}
                         className="w-24 h-32 bg-slate-800 border border-slate-700 rounded-xl p-3 flex flex-col gap-2 shadow-2xl"
                      >
                         <div className="h-2 w-10 bg-indigo-500/50 rounded-full" />
                         <div className="h-2 w-full bg-slate-700 rounded-full" />
                         <div className="h-2 w-4/5 bg-slate-700 rounded-full" />
                         <FileText className="w-8 h-8 text-indigo-400/50 m-auto" />
                      </motion.div>
                    </div>
                    <div className="px-6 py-2 bg-indigo-500/20 border border-indigo-500/30 text-indigo-300 rounded-full text-sm font-semibold backdrop-blur-md">
                      Parsing Modalities...
                    </div>
                 </motion.div>
              )}

              {activeStep === 1 && (
                 <motion.div
                   key="stage-1"
                   initial={{ opacity: 0, scale: 0.9 }}
                   animate={{ opacity: 1, scale: 1 }}
                   exit={{ opacity: 0, scale: 0.9 }}
                   transition={{ duration: 0.5 }}
                   className="relative flex flex-col items-center w-full max-w-sm"
                 >
                    {/* Scanning Line Animation */}
                    <div className="relative w-full h-48 bg-slate-800/80 backdrop-blur-xl border border-amber-500/30 rounded-2xl p-6 overflow-hidden shadow-[0_0_50px_-12px_rgba(251,191,36,0.2)]">
                        <motion.div 
                            initial={{ top: 0 }}
                            animate={{ top: "100%" }}
                            transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                            className="absolute left-0 right-0 h-1 bg-amber-500/50 shadow-[0_0_20px_2px_rgba(251,191,36,0.8)] z-10"
                        />
                        <div className="flex flex-col gap-3 font-mono text-xs text-amber-500 opacity-80">
                           <div className="flex justify-between border-b border-slate-700 pb-1"><span>{">"} Intent Check:</span> <span className="text-emerald-400">CLINICAL_QUERY</span></div>
                           <div className="flex justify-between border-b border-slate-700 pb-1"><span>{">"} Drug Entity:</span> <span className="text-white">Lisinopril 10mg</span></div>
                           <div className="flex justify-between border-b border-slate-700 pb-1"><span>{">"} Patient Info:</span> <span className="text-white">ID-999 (Matched)</span></div>
                        </div>
                    </div>
                 </motion.div>
              )}

              {activeStep === 2 && (
                 <motion.div
                   key="stage-2"
                   initial={{ opacity: 0, rotateX: 90 }}
                   animate={{ opacity: 1, rotateX: 0 }}
                   exit={{ opacity: 0, rotateX: -90 }}
                   transition={{ duration: 0.6, type: 'spring' }}
                   className="relative flex flex-wrap gap-4 items-center justify-center"
                 >
                    <div className="w-28 h-28 rounded-2xl bg-teal-500/10 border border-teal-500/30 flex flex-col items-center justify-center p-2 relative shadow-[0_0_30px_-5px_rgba(20,184,166,0.3)]">
                        <Database className="w-8 h-8 text-teal-400 mb-2" />
                        <span className="text-[10px] font-bold text-teal-300 uppercase">Longitudinal</span>
                    </div>
                    
                    <div className="w-28 h-28 rounded-2xl bg-teal-500/10 border border-teal-500/30 flex flex-col items-center justify-center p-2 relative shadow-[0_0_30px_-5px_rgba(20,184,166,0.3)]">
                        <Activity className="w-8 h-8 text-teal-400 mb-2" />
                        <span className="text-[10px] font-bold text-teal-300 uppercase">PGx Markers</span>
                    </div>

                    <div className="w-28 h-28 rounded-2xl bg-teal-500/10 border border-teal-500/30 flex flex-col items-center justify-center p-2 relative shadow-[0_0_30px_-5px_rgba(20,184,166,0.3)]">
                        <Pill className="w-8 h-8 text-teal-400 mb-2" />
                        <span className="text-[10px] font-bold text-teal-300 uppercase">Polypharmacy</span>
                        <motion.div 
                          className="absolute -top-2 -right-2 h-5 w-5 rounded-full bg-amber-500 flex items-center justify-center text-[10px] font-bold text-white shadow-lg shadow-amber-500/50"
                          initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ delay: 1, type: 'spring' }}
                        >1</motion.div>
                    </div>
                 </motion.div>
              )}

              {activeStep === 3 && (
                 <motion.div
                   key="stage-3"
                   initial={{ opacity: 0, scale: 0.8 }}
                   animate={{ opacity: 1, scale: 1 }}
                   exit={{ opacity: 0, scale: 0.8 }}
                   transition={{ duration: 0.5, type: 'spring' }}
                   className="relative flex flex-col items-center text-center w-full max-w-sm"
                 >
                    <motion.div 
                      initial={{ scale: 0 }} 
                      animate={{ scale: 1 }} 
                      transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
                      className="w-24 h-24 rounded-full bg-emerald-500/20 border-2 border-emerald-500 flex items-center justify-center mb-6 shadow-[0_0_50px_-5px_rgba(16,185,129,0.5)]"
                    >
                        <ShieldCheck className="w-12 h-12 text-emerald-400" />
                    </motion.div>
                    <h4 className="text-xl font-bold text-white mb-2">Verdict: Caution Recommended</h4>
                    <p className="text-sm text-slate-400 border border-slate-700 bg-slate-800/50 p-3 rounded-lg backdrop-blur-sm">
                       Alternative therapy suggested due to moderate risk of CYP2D6 poor metabolism and pre-existing polypharmacy burden.
                    </p>
                 </motion.div>
              )}
            </AnimatePresence>

        </div>
      </div>
    </div>
  );
}
