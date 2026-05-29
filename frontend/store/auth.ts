"use client"

import { create } from "zustand"
import type { User, UserRole } from "@/types"
import { getToken, setToken, getUser, setUser, clearAuth } from "@/lib/auth"

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  login: (user: User, token: string) => void
  logout: () => void
  hydrate: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: null,
  isAuthenticated: false,

  login: (user, token) => {
    setToken(token)
    setUser(user)
    // Also set cookie so middleware can read it
    document.cookie = `nh_token=${token}; path=/; max-age=1800; SameSite=Lax`
    set({ user, token, isAuthenticated: true })
  },

  logout: () => {
    clearAuth()
    document.cookie = "nh_token=; path=/; max-age=0"
    set({ user: null, token: null, isAuthenticated: false })
    window.location.href = "/login"
  },

  hydrate: () => {
    const token = getToken()
    const user = getUser()
    if (token && user) {
      set({ user, token, isAuthenticated: true })
    }
  },
}))
