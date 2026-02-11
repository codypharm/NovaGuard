import { SignIn } from "@clerk/clerk-react";

export default function LoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50">
      <div className="w-full max-w-md space-y-8 px-4">
        <div className="mt-8 flex justify-center">
            <SignIn />
        </div>
      </div>
    </div>
  );
}
