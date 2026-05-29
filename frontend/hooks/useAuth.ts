"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { useAuthStore } from "@/store/auth"
import { authAPI } from "@/lib/api"
import { extractErrorMessage } from "@/lib/errors"
import type { User, UserRole } from "@/types"

export function useAuth() {
  const { user, token, isAuthenticated, login, logout, hydrate } = useAuthStore()
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()

  const signIn = async (email: string, password: string) => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await authAPI.login(email, password)
      const user: User = {
        user_id: response.user_id,
        email: response.email,
        role: response.role as UserRole,
      }
      login(user, response.access_token)
      router.push("/dashboard")
    } catch (err: unknown) {
      setError(extractErrorMessage(err, "Invalid credentials. Please try again."))
    } finally {
      setIsLoading(false)
    }
  }

  const signUp = async (email: string, password: string, fullName: string, role: string = "coder") => {
    setIsLoading(true)
    setError(null)
    try {
      await authAPI.register(email, password, fullName, role)
      // Auto-login after register
      await signIn(email, password)
    } catch (err: unknown) {
      setError(extractErrorMessage(err, "Registration failed. Please try again."))
      setIsLoading(false)
    }
  }

  return { user, token, isAuthenticated, isLoading, error, signIn, signUp, logout, hydrate, setError }
}
