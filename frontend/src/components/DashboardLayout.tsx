import { Sidebar } from '@/components/Sidebar'
import { ShieldCheck } from 'lucide-react'
import { Link } from 'react-router-dom'

interface DashboardLayoutProps {
  children: React.ReactNode
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  return (
    <div className="min-h-screen bg-zinc-50 font-sans text-slate-900 flex">
      {/* Sidebar - Hidden on mobile, fixed on desktop */}
      <aside className="hidden w-64 flex-col md:flex fixed inset-y-0 z-50 bg-white border-r">
        <Link to="/" className="h-16 flex items-center px-6 border-b bg-white">
             <div className="h-8 w-8 rounded-lg bg-teal-600 flex items-center justify-center text-white shadow-lg shadow-teal-500/20 mr-2">
                <ShieldCheck className="w-5 h-5" />
             </div>
             <span className="text-xl font-black tracking-tighter text-slate-900 uppercase italic">Nova Guard</span>
        </Link>
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
