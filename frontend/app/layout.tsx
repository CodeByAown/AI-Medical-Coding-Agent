import type { Metadata } from "next"
import { Inter } from "next/font/google"
import "./globals.css"
import { ThemeProvider } from "next-themes"
import { ReactQueryProvider } from "@/lib/providers"

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
})

export const metadata: Metadata = {
  title: "Neural Hub | AI Medical Coding Platform",
  description: "Enterprise-grade AI-powered medical coding automation for ICD-10, CPT, and HCPCS",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    // suppressHydrationWarning on html is required by next-themes (it adds class attribute)
    <html lang="en" className={`${inter.variable} h-full`} suppressHydrationWarning>
      {/* suppressHydrationWarning on body prevents warnings from browser extensions mutating the DOM */}
      <body className="min-h-full antialiased" suppressHydrationWarning>
        <ThemeProvider
          attribute="class"
          defaultTheme="dark"
          enableSystem={false}
          storageKey="nh-theme"
        >
          <ReactQueryProvider>{children}</ReactQueryProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}
