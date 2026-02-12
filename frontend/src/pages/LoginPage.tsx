import { SignIn } from "@clerk/clerk-react";
import { Link } from "react-router-dom";

export default function LoginPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-slate-50">
      <div className="w-full max-w-md space-y-8 px-4">
        <div className="mt-8 flex justify-center">
            <SignIn />
        </div>
        <div className="text-center">
            <Link to="/" className="text-sm font-bold text-slate-400 hover:text-teal-600 transition-colors uppercase tracking-widest">
                ← Back to Global Home
            </Link>
        </div>
      </div>
    </div>
  );
}
