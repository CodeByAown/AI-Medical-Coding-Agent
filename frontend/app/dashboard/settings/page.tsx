"use client"

import { useEffect, useState } from "react"
import { useTheme } from "next-themes"
import { motion } from "framer-motion"
import {
  User, Lock, Globe, Palette, Server, CheckCircle2,
  AlertCircle, Loader2, Eye, EyeOff, Moon, Sun,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { Badge } from "@/components/ui/badge"
import { useAuthStore } from "@/store/auth"
import { healthAPI } from "@/lib/api"
import type { HealthStatus } from "@/types"

export default function SettingsPage() {
  const { user } = useAuthStore()
  const { resolvedTheme, setTheme } = useTheme()
  const [mounted, setMounted] = useState(false)
  useEffect(() => setMounted(true), [])
  const [backendUrl, setBackendUrl] = useState("http://localhost:8000")
  const [healthStatus, setHealthStatus] = useState<HealthStatus | null>(null)
  const [checkingHealth, setCheckingHealth] = useState(false)
  const [showCurrentPw, setShowCurrentPw] = useState(false)
  const [currentPw, setCurrentPw] = useState("")
  const [newPw, setNewPw] = useState("")

  const checkHealth = async () => {
    setCheckingHealth(true)
    try {
      const status = await healthAPI.check()
      setHealthStatus(status)
    } catch {
      setHealthStatus({ status: "unhealthy" })
    } finally {
      setCheckingHealth(false)
    }
  }

  return (
    <div className="p-6 max-w-3xl space-y-5">
      <div>
        <h2 className="text-lg font-semibold text-slate-100">Settings</h2>
        <p className="text-sm text-slate-500 mt-0.5">Manage your account and preferences</p>
      </div>

      <Tabs defaultValue="account">
        <TabsList>
          <TabsTrigger value="account"><User className="h-3.5 w-3.5 mr-1.5" />Account</TabsTrigger>
          <TabsTrigger value="api"><Globe className="h-3.5 w-3.5 mr-1.5" />API</TabsTrigger>
          <TabsTrigger value="appearance"><Palette className="h-3.5 w-3.5 mr-1.5" />Appearance</TabsTrigger>
          <TabsTrigger value="system"><Server className="h-3.5 w-3.5 mr-1.5" />System</TabsTrigger>
        </TabsList>

        {/* Account */}
        <TabsContent value="account" className="space-y-5">
          <Card>
            <CardHeader><CardTitle className="text-sm">Profile</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center gap-4">
                <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-600 to-indigo-600 text-white text-lg font-bold">
                  {user?.email?.[0].toUpperCase() ?? "U"}
                </div>
                <div>
                  <p className="font-medium text-slate-200">{user?.email?.split("@")[0]}</p>
                  <p className="text-sm text-slate-500">{user?.email}</p>
                  <Badge variant="default" className="mt-1 text-[10px] capitalize">{user?.role}</Badge>
                </div>
              </div>
              <Separator />
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <Label className="text-xs">Display name</Label>
                  <Input defaultValue={user?.email?.split("@")[0]} className="h-8 text-sm" />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs">Email</Label>
                  <Input defaultValue={user?.email} className="h-8 text-sm" disabled />
                </div>
              </div>
              <Button size="sm" variant="outline">Save changes</Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle className="text-sm flex items-center gap-2"><Lock className="h-4 w-4" />Change Password</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-1.5">
                <Label className="text-xs">Current password</Label>
                <div className="relative">
                  <Input
                    type={showCurrentPw ? "text" : "password"}
                    value={currentPw}
                    onChange={(e) => setCurrentPw(e.target.value)}
                    className="h-8 text-sm pr-9"
                    placeholder="••••••••"
                  />
                  <button
                    type="button"
                    onClick={() => setShowCurrentPw(!showCurrentPw)}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 cursor-pointer"
                  >
                    {showCurrentPw ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                  </button>
                </div>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">New password</Label>
                <Input type="password" value={newPw} onChange={(e) => setNewPw(e.target.value)} className="h-8 text-sm" placeholder="Min. 8 characters" />
              </div>
              <Button size="sm" variant="outline" disabled={!currentPw || !newPw}>Update password</Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* API */}
        <TabsContent value="api" className="space-y-5">
          <Card>
            <CardHeader><CardTitle className="text-sm">Backend Configuration</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-1.5">
                <Label className="text-xs">Backend URL</Label>
                <div className="flex gap-2">
                  <Input value={backendUrl} onChange={(e) => setBackendUrl(e.target.value)} className="h-8 text-sm font-mono" />
                  <Button size="sm" variant="outline" onClick={checkHealth} disabled={checkingHealth}>
                    {checkingHealth ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "Test"}
                  </Button>
                </div>
              </div>

              {healthStatus && (
                <motion.div
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`flex items-start gap-3 rounded-xl border p-3 ${
                    healthStatus.status === "healthy"
                      ? "border-emerald-500/20 bg-emerald-500/8"
                      : "border-red-500/20 bg-red-500/8"
                  }`}
                >
                  {healthStatus.status === "healthy"
                    ? <CheckCircle2 className="h-4 w-4 text-emerald-400 mt-0.5 flex-shrink-0" />
                    : <AlertCircle className="h-4 w-4 text-red-400 mt-0.5 flex-shrink-0" />}
                  <div>
                    <p className={`text-sm font-medium ${healthStatus.status === "healthy" ? "text-emerald-300" : "text-red-300"}`}>
                      {healthStatus.status === "healthy" ? "Backend is healthy" : "Backend unreachable"}
                    </p>
                    {healthStatus.version && (
                      <p className="text-xs text-slate-500 mt-0.5">Version {healthStatus.version}</p>
                    )}
                  </div>
                </motion.div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle className="text-sm">API Settings</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              {[
                { label: "Enable request logging", defaultChecked: false },
                { label: "Auto-retry on failure", defaultChecked: true },
                { label: "Include audit metadata", defaultChecked: true },
              ].map(({ label, defaultChecked }) => (
                <div key={label} className="flex items-center justify-between">
                  <Label className="text-sm text-slate-300 cursor-pointer">{label}</Label>
                  <Switch defaultChecked={defaultChecked} />
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Appearance */}
        <TabsContent value="appearance" className="space-y-5">
          <Card>
            <CardHeader><CardTitle className="text-sm">Theme</CardTitle></CardHeader>
            <CardContent>
              {mounted ? (
                <div className="grid grid-cols-2 gap-3">
                  {(["dark", "light"] as const).map((t) => (
                    <button
                      key={t}
                      onClick={() => setTheme(t)}
                      className={`relative rounded-xl border p-4 text-left transition-all cursor-pointer ${
                        resolvedTheme === t
                          ? "border-blue-500 bg-blue-500/10"
                          : "border-[#1e2d4d] bg-[#080d1a] hover:border-[#263754]"
                      }`}
                    >
                      <div className={`inline-flex h-8 w-8 items-center justify-center rounded-lg mb-2 ${
                        t === "dark" ? "bg-slate-800" : "bg-slate-200"
                      }`}>
                        {t === "dark" ? <Moon className="h-4 w-4 text-slate-300" /> : <Sun className="h-4 w-4 text-slate-700" />}
                      </div>
                      <p className="text-sm font-medium text-slate-200 capitalize">{t} mode</p>
                      {resolvedTheme === t && (
                        <CheckCircle2 className="absolute top-3 right-3 h-4 w-4 text-blue-400" />
                      )}
                    </button>
                  ))}
                </div>
              ) : (
                <div className="h-24 animate-pulse rounded-xl bg-[#141e35]" />
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle className="text-sm">Display preferences</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              {[
                { label: "Show confidence percentages", defaultChecked: true },
                { label: "Expand evidence by default", defaultChecked: false },
                { label: "Dense table layout", defaultChecked: false },
                { label: "Show session IDs", defaultChecked: true },
              ].map(({ label, defaultChecked }) => (
                <div key={label} className="flex items-center justify-between">
                  <Label className="text-sm text-slate-300 cursor-pointer">{label}</Label>
                  <Switch defaultChecked={defaultChecked} />
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>

        {/* System */}
        <TabsContent value="system" className="space-y-5">
          <Card>
            <CardHeader><CardTitle className="text-sm">Component Status</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              {[
                { name: "AI Engine (GPT-4o)", status: "operational", detail: "openai/gpt-4o" },
                { name: "ICD-10 Knowledge Base", status: "operational", detail: "74,260 codes indexed" },
                { name: "CPT Knowledge Base", status: "operational", detail: "46 codes" },
                { name: "NLP Pipeline", status: "operational", detail: "en_core_web_sm" },
                { name: "PHI Encryption", status: "disabled", detail: "Set ENABLE_PHI_ENCRYPTION=true" },
                { name: "Redis Cache", status: "unavailable", detail: "Not connected" },
              ].map(({ name, status, detail }) => (
                <div key={name} className="flex items-center justify-between py-1">
                  <div>
                    <p className="text-sm text-slate-300">{name}</p>
                    <p className="text-[10px] text-slate-500 mt-0.5">{detail}</p>
                  </div>
                  <Badge
                    variant={status === "operational" ? "success" : status === "disabled" ? "warning" : "danger"}
                    className="text-[10px] capitalize"
                  >
                    {status}
                  </Badge>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle className="text-sm">Version Information</CardTitle></CardHeader>
            <CardContent className="space-y-2 text-sm">
              {[
                { label: "Platform", value: "Neural Hub v1.0.0" },
                { label: "Frontend", value: "Next.js 16 / React 19" },
                { label: "Backend", value: "FastAPI / Python 3.13" },
                { label: "Database", value: "SQLite (development)" },
                { label: "Auth", value: "JWT HS256 + RBAC" },
              ].map(({ label, value }) => (
                <div key={label} className="flex items-center justify-between">
                  <span className="text-slate-500 text-xs">{label}</span>
                  <span className="text-slate-300 text-xs font-mono">{value}</span>
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
