import { Sidebar } from '@/components/Sidebar'

interface DashboardLayoutProps {
  children: React.ReactNode
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  return (
    <div className="min-h-screen bg-zinc-50 font-sans text-slate-900 flex">
      {/* Sidebar - Hidden on mobile, fixed on desktop */}
      <aside className="hidden w-64 flex-col md:flex fixed inset-y-0 z-50 bg-white border-r">
        <div className="h-16 flex items-center px-6 border-b bg-white">
             <div className="h-8 w-8 rounded bg-teal-600 mr-2"></div>
             <span className="font-bold text-lg">Nova Guard</span>
        </div>
        <Sidebar className="flex-1" />
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 md:ml-64 flex flex-col min-h-screen">
        {/* Modify Header to be cleaner or remove branding if in sidebar */}
        {/* For now, we keep a simplified header for actions */}
        
        <main className="flex-1 p-8">
            {children}
        </main>
      </div>
    </div>
  )
}
