import { useState, useRef, useEffect } from 'react'
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Send, User as UserIcon, Bot, Paperclip, X, Mic, Loader2, Square, Volume2, Download, CheckCircle2 } from "lucide-react"
import { cn } from "@/lib/utils"
import { type Verdict } from './SafetyAnalysis'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { getSessionHistory, transcribeAudio, playTTS, downloadReport } from '@/services/api'
import { useAudioRecorder } from "../hooks/useAudioRecorder"


interface Message {
  id: string
  role: 'user' | 'assistant'
  content: React.ReactNode
  rawText?: string
  timestamp: Date
}

interface SafetyChatProps {
  sessionId: string
  verdict: Verdict | null
  isProcessing: boolean
  processingStep?: string | null  // Live SSE node label
  onProcess: (text: string, file: File | null) => void
  assistantResponse: string | null
  onResponseShown: () => void
}

export function SafetyChat({ sessionId, verdict, isProcessing, processingStep, onProcess, assistantResponse, onResponseShown }: SafetyChatProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoadingHistory, setIsLoadingHistory] = useState(false)
  const [input, setInput] = useState("")
  const [attachedFile, setAttachedFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [dragActive, setDragActive] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Voice Input Hook
  const { isRecording, startRecording, stopRecording } = useAudioRecorder()
  const [isTranscribing, setIsTranscribing] = useState(false)
  
  const [isPlayingAudio, setIsPlayingAudio] = useState<string | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const [seenSteps, setSeenSteps] = useState<string[]>([])

  useEffect(() => {
     if (processingStep && !seenSteps.includes(processingStep)) {
        setSeenSteps(prev => [...prev, processingStep])
     }
  }, [processingStep])
  
  useEffect(() => {
     if (!isProcessing) {
        setSeenSteps([])
     }
  }, [isProcessing])

  const handlePlayTTS = async (text: string, msgId: string) => {
      if (isPlayingAudio === msgId) {
          audioRef.current?.pause()
          setIsPlayingAudio(null)
          return
      }
      
      setIsPlayingAudio(msgId)
      try {
          const url = await playTTS(text)
          if (audioRef.current) {
              audioRef.current.src = url
              audioRef.current.play()
              audioRef.current.onended = () => setIsPlayingAudio(null)
          } else {
              const audio = new Audio(url)
              audioRef.current = audio
              audio.play()
              audio.onended = () => setIsPlayingAudio(null)
          }
      } catch(e) {
          console.error(e)
          setIsPlayingAudio(null)
      }
  }

  const handleMicClick = async () => {
      if (isRecording) {
            const audioBlob = await stopRecording()
            if (audioBlob.size > 0) {
                setIsTranscribing(true)
                try {
                    const { text } = await transcribeAudio(audioBlob)
                    if (text) {
                        setInput(prev => prev + (prev ? " " : "") + text)
                    }
                } catch (err) {
                    console.error("Transcription failed", err)
                } finally {
                    setIsTranscribing(false)
                }
            }
      } else {
          startRecording()
      }
  }

  // Load History on Session Change
  useEffect(() => {
      if (!sessionId) return
      
      const loadHistory = async () => {
          setIsLoadingHistory(true)
          setMessages([]) // Clear immediately to prevent ghosting
          try {
              const history = await getSessionHistory(sessionId)
              const formattedMessages: Message[] = history.map(msg => ({
                  id: msg.id,
                  role: msg.role,
                  timestamp: msg.timestamp ? new Date(msg.timestamp) : new Date(),
                  content: msg.content
              }))
              setMessages(formattedMessages)
          } catch (err) {
              console.error("Failed to load history", err)
          } finally {
              setIsLoadingHistory(false)
          }
      }
      
      loadHistory()
  }, [sessionId])

  // Effect to add assistant response when it arrives
  useEffect(() => {
    if (assistantResponse) {
      const assistantMsg: Message = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        timestamp: new Date(),
        content: (
          <div className="prose prose-sm prose-slate max-w-none dark:prose-invert prose-headings:text-slate-900 prose-h2:text-slate-900 prose-h3:text-slate-900 prose-p:text-slate-800 prose-li:text-slate-800 prose-strong:text-slate-900 prose-strong:font-bold prose-th:text-slate-900 prose-td:text-slate-800">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{String(assistantResponse || '')}</ReactMarkdown>
          </div>
        )
      }
      setMessages(prev => [...prev, assistantMsg])
      onResponseShown() // Clear the prop so we don't re-add it
    }
  }, [assistantResponse, onResponseShown])

  // ... rest of component

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
                <div className="flex-1 text-white">
                  <h3 className="font-bold text-lg text-white">
                    {verdict.status === "green" ? "SAFE TO DISPENSE" :
                     verdict.status === "yellow" ? "CAUTION REQUIRED" : "DO NOT DISPENSE"}
                  </h3>
                  <p className="text-white/90 text-sm mb-4">
                    {verdict.status === "green" ? "Acceptable to dispense." :
                     verdict.status === "yellow" ? "Please review the flags below before proceeding." : "Do not dispense."}
                  </p>
                  <button 
                      onClick={() => downloadReport(sessionId)}
                      className="flex items-center gap-1.5 text-xs bg-white/20 hover:bg-white/30 text-white font-medium px-3 py-1.5 rounded-full backdrop-blur-sm transition-colors w-fit"
                  >
                      <Download className="h-3.5 w-3.5" />
                      Download PDF Report
                  </button>
                </div>
             </div>

             <div className="space-y-3">
                {(verdict.flags || []).map((flag, i) => (
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
        // Focus back to textarea
        setTimeout(() => textareaRef.current?.focus(), 0)
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
        {isLoadingHistory && (
             <div className="space-y-4 animate-pulse">
                <div className="flex flex-row gap-3">
                    <div className="h-8 w-8 rounded-full bg-slate-200 shrink-0"></div>
                    <div className="w-[60%] h-12 bg-slate-100 rounded-2xl rounded-tl-none"></div>
                </div>
                <div className="flex flex-row-reverse gap-3">
                    <div className="h-8 w-8 rounded-full bg-slate-200 shrink-0"></div>
                    <div className="w-[40%] h-8 bg-slate-100 rounded-2xl rounded-tr-none"></div>
                </div>
                <div className="flex flex-row gap-3">
                    <div className="h-8 w-8 rounded-full bg-slate-200 shrink-0"></div>
                    <div className="w-[75%] h-24 bg-slate-100 rounded-2xl rounded-tl-none"></div>
                </div>
             </div>
        )}

        {!isLoadingHistory && messages.length === 0 && !isProcessing && (
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
        
        {!isLoadingHistory && messages.map((msg) => (
            <div key={msg.id} className={cn("group flex gap-3 fade-in slide-in-from-bottom-2 duration-300", msg.role === 'user' ? "flex-row-reverse" : "flex-row")}>
                <div className={cn(
                    "h-8 w-8 rounded-full flex items-center justify-center shrink-0",
                    msg.role === 'user' ? "bg-slate-100 text-slate-600" : "bg-teal-100 text-teal-600"
                )}>
                    {msg.role === 'user' ? <UserIcon className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
                </div>
                <div className={cn(
                    "max-w-[85%] rounded-2xl px-4 py-3 text-sm shadow-sm",
                    msg.role === 'user' 
                        ? "bg-teal-50 text-teal-900 border border-teal-100 rounded-tr-none prose-p:text-teal-800 prose-headings:text-teal-900 prose-strong:text-teal-900 prose-li:text-teal-800 prose-ul:text-teal-800" 
                        : "bg-white text-slate-800 border border-slate-100 rounded-tl-none prose-p:text-slate-700 prose-headings:text-slate-900 prose-strong:text-slate-800 prose-li:text-slate-700 prose-ul:text-slate-700"
                )}>
                    <div className="prose prose-sm prose-slate max-w-none dark:prose-invert">
                        {typeof msg.content === 'string' ? (
                            <ReactMarkdown 
                                components={{
                                    img: ({node, ...props}) => (
                                        <img 
                                            {...props} 
                                            className="rounded-lg max-w-full h-auto my-2 border border-slate-200 shadow-sm" 
                                            alt={props.alt || "Image"}
                                        />
                                    )
                                }}
                            >
                                {msg.content}
                            </ReactMarkdown>
                        ) : (
                            msg.content
                        )}
                    </div>
                    {msg.role === 'assistant' && msg.rawText && (
                        <div className="flex justify-end mt-2 pt-2 border-t border-slate-100/50 opacity-0 group-hover:opacity-100 transition-opacity">
                            <button 
                                onClick={() => handlePlayTTS(msg.rawText!, msg.id)}
                                className={cn("flex items-center text-xs gap-1 px-2 py-1 rounded-md transition-colors", isPlayingAudio === msg.id ? "bg-teal-50 text-teal-600 font-medium" : "text-slate-400 hover:bg-slate-100 hover:text-slate-600")}
                                disabled={isPlayingAudio !== null && isPlayingAudio !== msg.id}
                            >
                                {isPlayingAudio === msg.id ? <Loader2 className="h-3 w-3 animate-spin"/> : <Volume2 className="h-3 w-3" />}
                                {isPlayingAudio === msg.id ? "Playing..." : "Read Aloud"}
                            </button>
                        </div>
                    )}
                </div>
            </div>
        ))}
        
        {isProcessing && (
           <div className="flex items-start gap-3 fade-in slide-in-from-bottom-2 duration-300">
               <div className="h-8 w-8 rounded-full bg-teal-100 flex items-center justify-center shrink-0 shadow-sm">
                  <Bot className="h-4 w-4 text-teal-600 animate-pulse" />
               </div>
               <div className="bg-white border border-slate-200 rounded-2xl rounded-tl-none p-4 text-sm text-slate-600 min-w-[280px] shadow-sm flex flex-col gap-3">
                  <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
                    <Loader2 className="h-4 w-4 animate-spin text-teal-600" />
                    <span className="font-semibold text-slate-800 tracking-tight">Processing Safety Check...</span>
                  </div>
                  
                  <div className="flex flex-col gap-2.5 relative pl-2 pt-1">
                     {/* Line connecting nodes */}
                     {seenSteps.length > 0 && <div className="absolute left-[11px] top-2 bottom-3 w-px bg-slate-200"></div>}
                     
                     {seenSteps.map((step, idx) => {
                         const isLast = idx === seenSteps.length - 1;
                         return (
                            <div key={idx} className="flex items-start gap-3 relative z-10">
                                <div className={cn("h-4 w-4 rounded-full border-2 flex items-center justify-center bg-white mt-0.5 shrink-0 transition-colors duration-500", isLast ? "border-teal-500 text-teal-500" : "border-slate-300")}>
                                    {!isLast && <CheckCircle2 className="h-3.5 w-3.5 fill-slate-200 text-white" />}
                                    {isLast && <div className="h-1.5 w-1.5 rounded-full bg-teal-500 animate-pulse"></div>}
                                </div>
                                <span className={cn("text-xs transition-all duration-300", isLast ? "text-teal-700 font-medium" : "text-slate-400 font-normal")}>
                                    {step}
                                </span>
                            </div>
                         )
                     })}
                  </div>
               </div>
           </div>
        )}
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
                    ref={textareaRef}
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
                        className={cn(
                            "h-8 w-8 rounded-full transition-all duration-200 relative",
                            isRecording 
                                ? "bg-red-500 text-white hover:bg-red-600 hover:text-white shadow-md ring-4 ring-red-100" 
                                : "text-slate-400 hover:bg-slate-100 hover:text-teal-600",
                            isTranscribing && "opacity-50 cursor-not-allowed"
                        )}
                        onClick={handleMicClick}
                        disabled={isTranscribing}
                        title={isRecording ? "Stop Recording" : "Voice Input"}
                     >
                        {isRecording && (
                            <span className="absolute -inset-1 rounded-full bg-red-400 opacity-20 animate-ping pointer-events-none"></span>
                        )}
                        {isTranscribing ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                        ) : isRecording ? (
                            <Square className="h-3 w-3 fill-current" />
                        ) : (
                            <Mic className="h-4 w-4" />
                        )}
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
