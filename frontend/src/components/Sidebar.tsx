import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { History, FileText, Settings, Database, PlusCircle, LogOut, Trash2 } from "lucide-react"
import { useSessionContext } from "@/context/SessionContext"
import { toast } from "sonner"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"

interface SidebarProps extends React.HTMLAttributes<HTMLDivElement> {}

import { useNavigate } from "react-router-dom"

export function Sidebar({ className }: SidebarProps) {
  const { sessionId, sessionsHistory, createNewSession, switchSession, loading, deleteSession, activeModule, setActiveModule } = useSessionContext()
  const navigate = useNavigate()

  const handleNewSession = async () => {
      console.log("🖱️ Sidebar: handleNewSession clicked")
      setActiveModule('safety-check')
      await createNewSession()
  }

  const handleSwitchSession = (id: string) => {
      setActiveModule('safety-check')
      switchSession(id)
  }

  return (
    <div className={cn("pb-12 h-full border-r bg-white", className)}>
      <div className="space-y-4 py-4">
        
        <div className="px-3 py-2">
          <div className="mb-2 px-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold tracking-tight text-slate-900">
              Sessions
            </h2>
            <Button 
                variant="ghost" 
                size="icon" 
                className="h-8 w-8 text-teal-600 hover:text-teal-700 hover:bg-teal-50"
                onClick={handleNewSession}
            >
                <PlusCircle className="h-5 w-5" />
            </Button>
          </div>
          <div className="space-y-1">
            {loading && sessionsHistory.length === 0 && (
                <div className="px-4 text-xs text-slate-400">Loading...</div>
            )}
            {!loading && sessionsHistory.length === 0 && (
                <div className="px-4 text-xs text-slate-400">No sessions found.</div>
            )}
            {sessionsHistory.map((session) => (
              <div key={session.id} className="group relative flex items-center">
                  <Button 
                    variant="ghost" 
                    className={cn(
                        "w-full justify-start font-normal pr-8", 
                        sessionId === session.id && "bg-slate-100 text-slate-900 font-medium"
                    )}
                    onClick={() => handleSwitchSession(session.id)}
                  >
                    <History className="mr-2 h-4 w-4 text-slate-400" />
                    <div className="flex flex-col items-start truncate text-ellipsis w-full">
                        <span className="truncate w-full text-left">{session.title || "Untitled Session"}</span>
                        <span className="text-[10px] text-slate-400">
                            {new Date(session.updated_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                        </span>
                    </div>
                  </Button>
                  
                  <AlertDialog>
                    <AlertDialogTrigger asChild>
                        <Button
                            variant="ghost"
                            size="icon"
                            className="absolute right-1 top-1/2 -translate-y-1/2 h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity text-slate-400 hover:text-rose-500 hover:bg-rose-50"
                            onClick={(e) => e.stopPropagation()} 
                        >
                            <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                    </AlertDialogTrigger>
                    <AlertDialogContent>
                        <AlertDialogHeader>
                            <AlertDialogTitle>Delete Session?</AlertDialogTitle>
                            <AlertDialogDescription>
                                This will permanently delete the session "{session.title}" and all its history. This action cannot be undone.
                            </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                            <AlertDialogCancel onClick={(e) => e.stopPropagation()}>Cancel</AlertDialogCancel>
                            <AlertDialogAction 
                                onClick={(e) => {
                                    e.stopPropagation()
                                    deleteSession(session.id)
                                    toast.success("Session deleted")
                                }}
                                className="bg-rose-600 hover:bg-rose-700 focus:ring-rose-600"
                            >
                                Delete
                            </AlertDialogAction>
                        </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
              </div>
            ))}
          </div>
        </div>
        
        <div className="px-3 py-2">
          <h2 className="mb-2 px-4 text-lg font-semibold tracking-tight text-slate-900">
            Library
          </h2>
          <div className="space-y-1">
            <Button variant="ghost" className="w-full justify-start">
              <FileText className="mr-2 h-4 w-4" />
              Saved Reports
            </Button>
            <Button 
                variant="ghost" 
                className={cn(
                    "w-full justify-start",
                    activeModule === 'drug-operations' && "bg-slate-100 text-slate-900 font-medium"
                )}
                onClick={() => {
                    setActiveModule('drug-operations')
                    navigate("/") // Ensure we are on the main page which houses the modules
                }}
            >
              <Database className="mr-2 h-4 w-4" />
              Drug Operations
            </Button>
            <Button variant="ghost" className="w-full justify-start">
              <Settings className="mr-2 h-4 w-4" />
              Settings
            </Button>
          </div>
        </div>

        {/* Bottom Area */}
        <div className="absolute bottom-4 left-0 w-full px-3">
             <Button variant="ghost" className="w-full justify-start text-rose-500 hover:text-rose-600 hover:bg-rose-50">
                <LogOut className="mr-2 h-4 w-4" />
                Sign Out
            </Button>
        </div>
      </div>
    </div>
  )
}
