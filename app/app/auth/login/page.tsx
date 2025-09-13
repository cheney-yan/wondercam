import type { Metadata } from "next";
import Image from "next/image";
import { ChevronDown } from "lucide-react";
import { LoginForm } from "@/components/login-form";
import { Button } from "@/components/ui/button";

export const metadata: Metadata = {
  title: "Login - WonderCam | AI Camera Assistant",
  description:
    "Sign in to WonderCam to capture photos, translate, and chat with an AI-powered camera assistant. 登录 WonderCam，拍照、翻译、与智能助手聊天。",
  openGraph: {
    title: "WonderCam Login 登录",
    description: "Sign in to access WonderCam. 登录以使用 WonderCam。",
    images: ["/app.png"],
  },
  twitter: {
    card: "summary_large_image",
    title: "WonderCam Login 登录",
    description: "Sign in to access WonderCam. 登录以使用 WonderCam。",
    images: ["/app.png"],
  },
};

export default function Page() {
  return (
    <main className="w-full">
      {/* Hero section with darkened background image */}
      <section className="relative min-h-[80svh] md:min-h-svh overflow-hidden md:rounded-3xl md:m-6">
        <Image
          src="/app.png"
          alt=""
          fill
          priority
          sizes="100vw"
          aria-hidden={true}
          className="object-cover"
        />
        {/* Dark overlay to reduce brightness */}
        <div className="absolute inset-0 bg-black/60" />
        <div className="absolute inset-0 bg-gradient-to-r from-black/70 via-black/50 to-transparent" />
        <div className="absolute inset-0 flex items-center">
          <div className="w-full max-w-5xl mx-auto px-6 py-12 grid gap-8 md:grid-cols-2 items-center">
            <div className="text-white">
              <h1 className="text-3xl md:text-5xl font-extrabold tracking-tight">
                WonderCam - AI Camera Helper
                <br />
                <span className="text-white/90">妙妙相机 - AI构建的奇妙图像</span>
              </h1>
              <p className="mt-4 text-white/90">
                Capture and chat with an intelligent assistant — all in one app.
              </p>
              <p className="text-white/80">
                拍照、智能助手聊天修改照片，尽在一个应用。
              </p>
              <Button asChild size="lg" className="mt-6 rounded-full shadow-lg">
                <a href="#login">Login Now（登录）</a>
              </Button>
            </div>
          </div>
        </div>

        {/* Scroll hint */}
        <div className="absolute bottom-6 left-0 right-0 flex justify-center text-white/80 text-sm">
          <span className="flex items-center gap-2">
            Scroll to login 下滑登录 <ChevronDown size={18} className="animate-bounce" />
          </span>
        </div>
      </section>

      {/* Centered login section */}
      <section
        id="login"
        className="flex min-h-svh w-full items-center justify-center p-6 md:p-10"
      >
        <div className="w-full max-w-sm">
          <LoginForm />
        </div>
      </section>
    </main>
  );
}
