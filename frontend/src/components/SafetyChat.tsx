import { useState, useRef, useEffect } from 'react'
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Send, User as UserIcon, Bot, Paperclip, X, Mic } from "lucide-react"
import { cn } from "@/lib/utils"
import { type Verdict } from './SafetyAnalysis'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: React.ReactNode
  timestamp: Date
}

interface SafetyChatProps {
  verdict: Verdict | null
  isProcessing: boolean
  onProcess: (text: string, file: File | null) => void
}

export function SafetyChat({ verdict, isProcessing, onProcess }: SafetyChatProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [attachedFile, setAttachedFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [dragActive, setDragActive] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Effect to add verdict as a message when it arrives
  useEffect(() => {
    if (verdict) {
      const verdictMessage: Message = {
        id: `verdict-${Date.now()}`,
        role: 'assistant',
        timestamp: new Date(),
        content: (
          <div className="space-y-4 min-w-[300px] md:min-w-[400px]">
             <div className={cn(
                "flex items-center gap-4 rounded-xl p-4 text-white shadow-sm",
                verdict.status === "green" ? "bg-emerald-500" :
                verdict.status === "yellow" ? "bg-amber-500" : "bg-rose-500"
              )}>
                <div className="flex-1">
                  <h3 className="font-bold text-lg">
                    {verdict.status === "green" ? "SAFE TO DISPENSE" :
                     verdict.status === "yellow" ? "CAUTION REQUIRED" : "DO NOT DISPENSE"}
                  </h3>
                  <p className="text-white/90 text-sm">
                    {verdict.status === "green" ? "No interactions found." :
                     "Please review the flags below before proceeding."}
                  </p>
                </div>
             </div>

             <div className="space-y-3">
                {verdict.flags.map((flag, i) => (
                  <div key={i} className={cn(
                    "rounded-lg border p-3 text-sm bg-white",
                    flag.severity === "warning" ? "border-amber-200 bg-amber-50 text-amber-900" :
                    flag.severity === "critical" ? "border-rose-200 bg-rose-50 text-rose-900" :
                    "border-slate-200 text-slate-700"
                  )}>
                    <div className="flex items-start justify-between gap-2">
                        <div>
                            <span className="font-semibold block mb-1">{flag.message}</span>
                            <span className="text-xs uppercase tracking-wider opacity-70">Category: {flag.category}</span>
                        </div>
                        <span className="text-[10px] text-slate-400 font-mono">{flag.source.toUpperCase()}</span>
                    </div>
                  </div>
                ))}
             </div>
          </div>
        )
      }
      setMessages(prev => [...prev, verdictMessage])
    }
  }, [verdict])

  const handleFileSelect = (file: File) => {
    if (file && file.type.startsWith('image/')) {
        setAttachedFile(file)
        const url = URL.createObjectURL(file)
        setPreviewUrl(url)
    }
  }

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true)
    } else if (e.type === "dragleave") {
      setDragActive(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0])
    }
  }

  const handleSend = () => {
    if (!input.trim() && !attachedFile) return

    // Create User Message
    const userMsg: Message = {
        id: `user-${Date.now()}`,
        role: 'user',
        content: (
            <div className="flex flex-col gap-2">
                {previewUrl && (
                    <img src={previewUrl} alt="Attached prescription" className="max-h-48 rounded-lg border border-white/20" />
                )}
                <p>{input}</p>
            </div>
        ),
        timestamp: new Date()
    }
    setMessages(prev => [...prev, userMsg])
    
    // Trigger Processing
    onProcess(input, attachedFile)

    // Clear Input
    setInput("")
    setAttachedFile(null)
    setPreviewUrl(null)
  }

  useEffect(() => {
    if (scrollRef.current) {
        scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  return (
    <div 
        className={cn(
            "flex flex-col h-full bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden transition-colors",
            dragActive ? "border-teal-500 bg-teal-50/50" : ""
        )}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
    >
      {/* Header */}
      <div className="px-4 py-3 border-b bg-slate-50 flex items-center gap-2">
        <Bot className="h-4 w-4 text-teal-600" />
        <span className="font-semibold text-sm text-slate-700">Safety Assistant</span>
      </div>

      {/* Chat Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6" ref={scrollRef}>
        {messages.length === 0 && !isProcessing && (
            <div className="flex flex-col items-center justify-center h-full text-slate-400 gap-4">
                <div className="h-16 w-16 bg-slate-100 rounded-full flex items-center justify-center mb-2">
                    <Bot className="h-8 w-8 text-slate-300" />
                </div>
                <div className="text-center space-y-1">
                    <p className="font-medium text-slate-600">Reimagine Clinical Safety</p>
                    <p className="text-sm">Drop a prescription image or type a query to start.</p>
                </div>
            </div>
        )}
        
        {isProcessing && (
           <div className="flex items-start gap-3">
               <div className="h-8 w-8 rounded-full bg-teal-100 flex items-center justify-center shrink-0">
                  <Bot className="h-4 w-4 text-teal-600 animate-pulse" />
               </div>
               <div className="bg-slate-100 rounded-2xl rounded-tl-none px-4 py-3 text-sm text-slate-600">
                  Running clinical analysis...
               </div>
           </div>
        )}

        {messages.map((msg) => (
            <div key={msg.id} className={cn("flex gap-3", msg.role === 'user' ? "flex-row-reverse" : "flex-row")}>
                <div className={cn(
                    "h-8 w-8 rounded-full flex items-center justify-center shrink-0",
                    msg.role === 'user' ? "bg-slate-900 text-white" : "bg-teal-100 text-teal-600"
                )}>
                    {msg.role === 'user' ? <UserIcon className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
                </div>
                <div className={cn(
                    "max-w-[85%] rounded-2xl px-4 py-3 text-sm shadow-sm",
                    msg.role === 'user' ? "bg-slate-900 text-white rounded-tr-none" : "bg-slate-50 text-slate-800 border border-slate-100 rounded-tl-none"
                )}>
                    {msg.content}
                </div>
            </div>
        ))}
      </div>

      {/* Input Area */}
      <div className="p-4 border-t bg-white">
        {/* Attachment Preview */}
        {attachedFile && (
            <div className="mb-2 flex items-center gap-2 bg-slate-50 p-2 rounded-lg border w-fit">
                {previewUrl && <img src={previewUrl} className="h-10 w-10 object-cover rounded" alt="Preview" />}
                <span className="text-xs text-slate-600 truncate max-w-[150px]">{attachedFile.name}</span>
                <button onClick={() => { setAttachedFile(null); setPreviewUrl(null); }} className="p-1 hover:bg-slate-200 rounded-full">
                    <X className="h-3 w-3 text-slate-500" />
                </button>
            </div>
        )}

        <div className="relative flex gap-2 items-end">
            <input 
                type="file" 
                ref={fileInputRef} 
                className="hidden" 
                accept="image/*"
                onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])} 
            />
            <Button 
                variant="ghost" 
                size="icon" 
                className="h-10 w-10 mb-1 text-slate-400 hover:text-teal-600"
                onClick={() => fileInputRef.current?.click()}
            >
                <Paperclip className="h-5 w-5" />
            </Button>

            <div className="relative flex-1">
                <Textarea
                    value={input}
                    onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setInput(e.target.value)}
                    placeholder="Describe prescription or drop image..."
                    className="min-h-[50px] pr-20 resize-none border-slate-200 focus-visible:ring-teal-500 py-3"
                    onKeyDown={(e: React.KeyboardEvent<HTMLTextAreaElement>) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                            e.preventDefault()
                            handleSend()
                        }
                    }}
                />
                
                <div className="absolute right-2 bottom-2 flex items-center gap-1">
                     <Button 
                        size="icon" 
                        variant="ghost"
                        className="h-8 w-8 rounded-full text-slate-400 hover:bg-slate-100 hover:text-teal-600"
                        title="Voice Input (Coming Soon)"
                     >
                        <Mic className="h-4 w-4" />
                     </Button>
                     <Button 
                        size="sm" 
                        className="h-8 w-8 p-0 rounded-full bg-teal-600 hover:bg-teal-700"
                        onClick={handleSend}
                        disabled={!input.trim() && !attachedFile}
                    >
                        <Send className="h-4 w-4" />
                    </Button>
                </div>
            </div>
        </div>
      </div>
    </div>
  )
}
