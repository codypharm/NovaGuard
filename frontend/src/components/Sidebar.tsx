import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { History, FileText, Settings, Database, PlusCircle, LogOut } from "lucide-react"

interface SidebarProps extends React.HTMLAttributes<HTMLDivElement> {}

export function Sidebar({ className }: SidebarProps) {
  // Mock session data
  const recentSessions = [
    { id: 1, label: "Patient #1024 - Lisinopril", time: "10m ago" },
    { id: 2, label: "Scan #982 - Amoxicillin", time: "1h ago" },
    { id: 3, label: "Patient #1023 - Metformin", time: "2h ago" },
  ]

  return (
    <div className={cn("pb-12 h-full border-r bg-white", className)}>
      <div className="space-y-4 py-4">
        <div className="px-3 py-2">
          <div className="mb-2 px-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold tracking-tight text-slate-900">
              Sessions
            </h2>
            <Button variant="ghost" size="icon" className="h-8 w-8 text-teal-600 hover:text-teal-700 hover:bg-teal-50">
                <PlusCircle className="h-5 w-5" />
            </Button>
          </div>
          <div className="space-y-1">
            {recentSessions.map((session) => (
              <Button key={session.id} variant="ghost" className="w-full justify-start font-normal">
                <History className="mr-2 h-4 w-4 text-slate-400" />
                <div className="flex flex-col items-start truncate text-ellipsis">
                    <span className="truncate w-full text-left">{session.label}</span>
                    <span className="text-[10px] text-slate-400">{session.time}</span>
                </div>
              </Button>
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
            <Button variant="ghost" className="w-full justify-start">
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
