import { redirect } from "next/navigation";
import Link from "next/link";

import { createClient } from "@/lib/supabase/server";
import { InfoIcon } from "lucide-react";
import { FetchDataSteps } from "@/components/tutorial/fetch-data-steps";

export default async function ProtectedPage() {
  const supabase = await createClient();

  const { data, error } = await supabase.auth.getClaims();
  if (error || !data?.claims) {
    redirect("/auth/login");
  }

  return (
    <div className="flex-1 w-full flex flex-col gap-12">
      <div className="w-full">
        <div className="bg-accent text-sm p-3 px-5 rounded-md text-foreground flex gap-3 items-center">
          <InfoIcon size="16" strokeWidth={2} />
          This is a protected page that you can only see as an authenticated
          user
        </div>
      </div>
      <div className="flex flex-col gap-6 items-start">
        <div className="w-full">
          <h2 className="font-bold text-2xl mb-4">🎉 Welcome to your protected area!</h2>
          
          {/* WonderCam App Launch */}
          <div className="bg-gradient-to-r from-blue-500 to-purple-600 p-6 rounded-xl text-white mb-6">
            <h3 className="text-xl font-bold mb-2">📸 WonderCam</h3>
            <p className="mb-4 opacity-90">
              Your AI-powered camera companion. Take photos and have conversations about them with advanced AI.
            </p>
            <Link 
              href="/wondercam"
              className="inline-block bg-white text-blue-600 font-semibold px-6 py-3 rounded-lg hover:bg-gray-100 transition-colors"
            >
              Launch WonderCam 🚀
            </Link>
          </div>
        </div>
        
        <div>
          <h2 className="font-bold text-2xl mb-4">Your user details</h2>
          <pre className="text-xs font-mono p-3 rounded border max-h-32 overflow-auto">
            {JSON.stringify(data.claims, null, 2)}
          </pre>
        </div>
      </div>
      <div>
        <h2 className="font-bold text-2xl mb-4">Next steps</h2>
        <FetchDataSteps />
      </div>
    </div>
  );
}
