import { useState } from 'react'
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Upload, Mic, Search, CheckCircle } from "lucide-react"
import { cn } from "@/lib/utils"

interface PrescriptionInputProps {
  onProcess: (text: string, file: File | null) => void
  isProcessing: boolean
}

export function PrescriptionInput({ onProcess, isProcessing }: PrescriptionInputProps) {
  const [text, setText] = useState("")
  const [dragActive, setDragActive] = useState(false)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [file, setFile] = useState<File | null>(null)

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
      handleFile(e.dataTransfer.files[0])
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0])
    }
  }

  const handleFile = (file: File) => {
    if (file.type.startsWith("image/")) {
      setFile(file)
      const url = URL.createObjectURL(file)
      setPreviewUrl(url)
    } else {
        alert("Please upload an image file.")
    }
  }

  const handleSubmit = () => {
    onProcess(text, file)
  }

  return (
    <div className="space-y-6">
        <Card 
            className={cn(
                "border-dashed border-2 transition-all cursor-pointer relative overflow-hidden",
                dragActive ? "border-teal-500 bg-teal-50" : "border-slate-300 bg-white/50 hover:bg-white"
            )}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            onClick={() => document.getElementById('file-upload')?.click()}
        >
            <input 
                id="file-upload" 
                type="file" 
                className="hidden" 
                accept="image/*"
                onChange={handleFileChange}
            />
            
            <CardContent className="flex flex-col items-center justify-center py-12 text-center text-slate-500 min-h-[300px]">
                {previewUrl ? (
                    <div className="relative w-full h-full flex flex-col items-center">
                        <img src={previewUrl} alt="Preview" className="max-h-[250px] rounded-lg shadow-md object-contain" />
                        <div className="mt-4 flex items-center gap-2 text-teal-600">
                            <CheckCircle className="h-4 w-4" />
                            <span className="text-sm font-medium">Image Loaded</span>
                        </div>
                        <Button 
                            variant="ghost" 
                            size="sm" 
                            className="mt-2 text-rose-500 hover:text-rose-600 hover:bg-rose-50"
                            onClick={(e) => {
                                e.stopPropagation()
                                setPreviewUrl(null)
                                setFile(null)
                            }}
                        >
                            Remove
                        </Button>
                    </div>
                ) : (
                    <>
                        <div className={cn("mb-4 rounded-full p-4 transition-colors", dragActive ? "bg-teal-100" : "bg-slate-100")}>
                            <Upload className={cn("h-8 w-8", dragActive ? "text-teal-600" : "text-slate-400")} />
                        </div>
                        <h3 className="text-lg font-medium text-slate-900">
                            {dragActive ? "Drop it here!" : "Drop prescription image here"}
                        </h3>
                        <p className="text-sm mt-1">or click to browse</p>
                    </>
                )}
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
                value={text}
                onChange={(e) => setText(e.target.value)}
            />
            <div className="absolute bottom-3 right-3">
                <Button size="icon" variant="ghost" className="text-slate-400 hover:text-teal-600">
                    <Mic className="h-5 w-5" />
                </Button>
            </div>
        </div>

        <Button 
            className="w-full bg-teal-600 hover:bg-teal-700 h-12 text-lg"
            onClick={handleSubmit}
            disabled={isProcessing}
        >
            {isProcessing ? "Analyzing Protocol..." : "Run Safety Check"}
        </Button>
    </div>
  )
}
